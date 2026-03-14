from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests

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
REPORT_HOST = os.environ.get("REPORT_SERVICE_HOST", "report_service:5004")
TWILIO_HOST = os.environ.get("TWILIO_WRAPPER_HOST", "twilio_wrapper_http:6203")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/resolve-issue", methods=["POST"])
def resolve_issue():
    body = request.get_json(silent=True) or {}
    report_id = body.get("report_id")
    resolution = body.get("resolution")
    driver_phone = body.get("driver_phone")  # Optional; can come from body or be looked up

    if not report_id or not resolution:
        return jsonify({"status": "error", "message": "Missing required fields: report_id, resolution"}), 400

    # Step 1: Update report resolution via report_service (COMP-11)
    r = requests.put(f"http://{REPORT_HOST}/api/reports/{report_id}/resolution",
                     json={"resolution": resolution}, timeout=5)
    if r.status_code == 404:
        return jsonify({"status": "error", "message": "Report not found"}), 404
    if r.status_code != 200:
        return jsonify({"status": "error", "message": f"Report service error: {r.json().get('message', 'unknown')}"}), 502

    # Step 2: Send SMS to driver via twilio_wrapper HTTP endpoint (COMP-11)
    # driver_phone is optional — if not provided, SMS cannot be sent
    sms_status = "unsent"
    if driver_phone:
        sms_message = (
            f"Your vehicle incident report (ID: {report_id}) has been resolved. "
            f"Resolution: {resolution}. Thank you for using ESD Car Rental."
        )
        try:
            r = requests.post(f"http://{TWILIO_HOST}/api/twilio/sms",
                              json={"to": driver_phone, "body": sms_message}, timeout=10)
            if r.status_code == 200:
                sms_status = "sent"
            else:
                print(f"[resolve_issue] twilio_wrapper returned {r.status_code} — flagging sms_status=unsent")
        except Exception as e:
            print(f"[resolve_issue] twilio_wrapper exception: {e} — flagging sms_status=unsent")
    else:
        print(f"[resolve_issue] No driver_phone provided — SMS not sent for report {report_id}")

    # Step 3: Write sms_status to Firestore directly if unsent (COMP-11)
    # report_service PUT /resolution only updates the resolution field — cannot set sms_status
    if sms_status == "unsent" and db is not None:
        try:
            db.collection("reports").document(report_id).update({"sms_status": "unsent"})
        except Exception as e:
            print(f"[resolve_issue] Firestore sms_status update failed: {e}")

    # Return success regardless of SMS outcome — report is resolved either way
    return jsonify({
        "report_id": report_id,
        "status": "resolved",
        "sms_status": sms_status,
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6004)), debug=True)
