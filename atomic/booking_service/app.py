from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Local dev, Docker, and Kong use different Host headers in practice.
# Be explicit so Flask/Werkzeug accepts browser and proxy requests.
app.config["TRUSTED_HOSTS"] = [
    "localhost",
    "127.0.0.1",
    "booking_service",
    "booking-service",
    "kong",
]

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


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    body = request.get_json(silent=True) or {}
    required = ["user_uid", "vehicle_id", "vehicle_type", "pickup_datetime",
                "hours", "total_price", "stripe_payment_intent_id"]
    for field in required:
        if field not in body:
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
    body["status"] = "confirmed"
    update_time, doc_ref = db.collection("bookings").add(body)
    return jsonify({"status": "ok", "booking_id": doc_ref.id, "message": "Booking created"}), 201


# Note: more specific route registered before wildcard <booking_id> to avoid conflicts
@app.route("/api/bookings/user/<string:uid>/active", methods=["GET"])
def get_active_booking_by_user(uid):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    docs = list(db.collection("bookings").where("user_uid", "==", uid).where("status", "==", "confirmed").stream())
    if not docs:
        return jsonify({"status": "ok", "data": None, "message": "No active booking found"}), 200
    booking = {"id": docs[0].id, **docs[0].to_dict()}
    return jsonify({"status": "ok", "data": booking}), 200


@app.route("/api/bookings/user/<string:uid>", methods=["GET"])
def get_bookings_by_user(uid):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    docs = db.collection("bookings").where("user_uid", "==", uid).stream()
    results = [{"id": d.id, **d.to_dict()} for d in docs]
    return jsonify({"status": "ok", "data": results}), 200


@app.route("/api/bookings/<string:booking_id>", methods=["GET"])
def get_booking(booking_id):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    doc = db.collection("bookings").document(booking_id).get()
    if not doc.exists:
        return jsonify({"status": "error", "message": "Booking not found"}), 404
    return jsonify({"status": "ok", "data": {"id": doc.id, **doc.to_dict()}}), 200


@app.route("/api/bookings/<string:booking_id>/status", methods=["PUT"])
def update_booking_status(booking_id):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    if not new_status:
        return jsonify({"status": "error", "message": "Missing required field: status"}), 400
    doc_ref = db.collection("bookings").document(booking_id)
    if not doc_ref.get().exists:
        return jsonify({"status": "error", "message": "Booking not found"}), 404
    doc_ref.update({"status": new_status})
    return jsonify({"status": "ok", "message": "Status updated"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5002)), debug=True)
