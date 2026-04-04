from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import requests
import pika

app = Flask(__name__)
CORS(app)

# Firestore init — wrapped in try/except so container starts even without credentials
try:
    import firebase_admin
    from firebase_admin import credentials, firestore as fs
    cred = credentials.Certificate(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/secrets/firebase-service-account.json")
    )
    firebase_admin.initialize_app(cred)
    db = fs.client()
except Exception as e:
    print(f"[WARN] Firestore init failed: {e}")
    db = None

# Service host constants
BOOKING_HOST = os.environ.get("BOOKING_SERVICE_HOST", "booking_service:5002")
REPORT_HOST = os.environ.get("REPORT_SERVICE_HOST", "report_service:5004")
MAPS_HOST = os.environ.get("MAPS_WRAPPER_HOST", "googlemaps_wrapper:6201")
OPENAI_HOST = os.environ.get("OPENAI_WRAPPER_HOST", "openai_wrapper:6200")
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))


def publish_report_event(payload: dict):
    """Publish report event to RabbitMQ. Failure is logged but does NOT raise — Phase A response returned regardless."""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, heartbeat=30)
        )
        channel = connection.channel()
        channel.exchange_declare(exchange="report_topic", exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange="report_topic",
            routing_key="report.new",
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
        connection.close()
        print(f"[report_issue] Published to report_topic: report_id={payload.get('report_id')}")
    except Exception as e:
        print(f"[report_issue] RabbitMQ publish failed (Phase B): {e}")
        # Do NOT re-raise — report is already persisted; Phase A response still returned


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/report-issue", methods=["POST"])
def report_issue():
    body = request.get_json(silent=True) or {}
    booking_id = body.get("booking_id")
    vehicle_id = body.get("vehicle_id")
    user_uid = body.get("user_uid")
    lat = body.get("lat")
    lng = body.get("lng")
    description = body.get("description", "")

    if not all([booking_id, vehicle_id, user_uid, lat is not None, lng is not None]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # Phase A Step 1: Validate booking exists (COMP-08)
    r = requests.get(f"http://{BOOKING_HOST}/api/bookings/{booking_id}", timeout=5)
    if r.status_code == 404:
        return jsonify({"status": "error", "message": "Booking not found"}), 400
    if r.status_code != 200:
        print(f"[report_issue] booking_service check returned {r.status_code} — proceeding anyway")

    # Phase A Step 2: Reverse geocode location (COMP-08)
    r = requests.post(f"http://{MAPS_HOST}/api/maps/geocode",
                      json={"lat": lat, "lng": lng}, timeout=10)
    if r.status_code == 200:
        address = r.json().get("address", f"{lat},{lng}")
    else:
        address = f"{lat},{lng}"
        print(f"[report_issue] Maps geocode failed ({r.status_code}) — using coordinates")

    # Phase A Step 3: Classify severity via OpenAI (COMP-08)
    r = requests.post(f"http://{OPENAI_HOST}/api/openai/evaluate",
                      json={"description": description, "address": address}, timeout=15)
    if r.status_code == 200:
        openai_resp = r.json()
        severity = openai_resp.get("severity", "medium")
        ai_evaluation = openai_resp  # store full response { severity, provider }
    else:
        severity = "medium"
        ai_evaluation = None
        print(f"[report_issue] OpenAI evaluate failed ({r.status_code}) — defaulting severity=medium")

    # Phase A Step 4: Persist report to report_service (COMP-08)
    report_body = {
        "booking_id": booking_id,
        "vehicle_id": vehicle_id,
        "user_uid": user_uid,
        "location": address,
        "description": description,
    }
    r = requests.post(f"http://{REPORT_HOST}/api/reports", json=report_body, timeout=5)
    if r.status_code not in (200, 201):
        return jsonify({"status": "error", "message": f"Report service error: {r.json().get('message', 'unknown')}"}), 502
    report_id = r.json().get("report_id")

    # Phase A Step 5: Update severity on report (separate evaluation endpoint)
    # report_service POST /reports creates with severity=None; evaluation endpoint sets it
    try:
        requests.put(f"http://{REPORT_HOST}/api/reports/{report_id}/evaluation",
                     json={"severity": severity, "ai_evaluation": ai_evaluation}, timeout=5)
    except Exception as e:
        print(f"[report_issue] Severity update failed: {e} — severity stored in response only")

    # Phase B (inline): Publish to RabbitMQ (COMP-09)
    # Failure logged but does not block Phase A response
    publish_report_event({
        "report_id": report_id,
        "booking_id": booking_id,
        "vehicle_id": vehicle_id,
        "user_uid": user_uid,
        "severity": severity,
        "location": address,
        "description": description,
    })

    # Return COMP-10 response shape
    return jsonify({
        "report_id": report_id,
        "status": "submitted",
        "severity": severity,
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6003)), debug=True)
