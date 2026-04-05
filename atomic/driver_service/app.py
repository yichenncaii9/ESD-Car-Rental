from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import date
import os

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
    print(f"[WARN] Firestore init failed (Phase 1 stub): {e}")
    db = None


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


# GET vs POST — method-based dispatch; no ordering conflict
@app.route("/api/drivers/<string:uid>", methods=["GET"])
def get_driver(uid):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500

    # drivers are keyed by license_number (not uid); must use .where() query, NOT .document(uid)
    docs = list(db.collection("drivers").where("uid", "==", uid).stream())
    if not docs:
        return jsonify({"status": "error", "message": "Driver not found"}), 404

    return jsonify({"status": "ok", "data": docs[0].to_dict()}), 200


@app.route("/api/drivers", methods=["POST"])
def create_driver():
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500

    body = request.get_json(silent=True) or {}
    uid = body.get("uid")
    license_number = body.get("license_number")
    license_expiry = body.get("license_expiry")

    if not all([uid, license_number, license_expiry]):
        return jsonify({"status": "error", "message": "Missing required fields: uid, license_number, license_expiry"}), 400

    doc_ref = db.collection("drivers").document(license_number)
    if doc_ref.get().exists:
        return jsonify({"status": "error", "message": "Driver with this license_number already exists"}), 409

    record = {
        "uid": uid,
        "name": body.get("name", ""),
        "email": body.get("email", ""),
        "license_number": license_number,
        "license_expiry": license_expiry,
        "phone": body.get("phone", ""),
    }
    doc_ref.set(record)
    return jsonify({"status": "created", "data": record}), 201


@app.route("/api/drivers/<string:uid>", methods=["PUT"])
def update_driver(uid):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500

    body = request.get_json(silent=True) or {}
    docs = list(db.collection("drivers").where("uid", "==", uid).stream())
    if not docs:
        return jsonify({"status": "error", "message": "Driver not found"}), 404

    updates = {}
    for field in ["name", "email", "license_number", "license_expiry", "phone"]:
        if field in body:
            updates[field] = body[field]

    if not updates:
        return jsonify({"status": "error", "message": "No fields to update"}), 400

    docs[0].reference.update(updates)
    updated = {**docs[0].to_dict(), **updates}
    return jsonify({"status": "ok", "data": updated}), 200


@app.route("/api/drivers/validate", methods=["POST"])
def validate_driver():
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500

    body = request.get_json(silent=True) or {}
    license_number = body.get("license_number")
    if not license_number:
        return jsonify({"status": "error", "message": "Missing required field: license_number"}), 400

    doc = db.collection("drivers").document(license_number).get()
    if not doc.exists:
        # validate returns 200 even for invalid — it is a validation query, not a resource lookup
        return jsonify({"valid": False, "reason": "driver not found"}), 200

    driver = doc.to_dict()
    expiry = date.fromisoformat(driver["license_expiry"])
    if expiry <= date.today():
        return jsonify({"valid": False, "reason": "license expired"}), 200

    return jsonify({"valid": True}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5003)), debug=True)
