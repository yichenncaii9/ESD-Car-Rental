from flask import Flask, jsonify, request
from flask_cors import CORS
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


@app.route("/api/vehicles", methods=["GET"])
def get_vehicles():
    if db is None:
        return jsonify({"status": "error", "message": "Database not available"}), 500
    docs = db.collection("vehicles").stream()
    results = [{"id": d.id, **d.to_dict()} for d in docs]
    return jsonify({"status": "ok", "data": results}), 200


@app.route("/api/vehicles/<string:vehicle_id>", methods=["GET"])
def get_vehicle(vehicle_id):
    if db is None:
        return jsonify({"status": "error", "message": "Database not available"}), 500
    doc = db.collection("vehicles").document(vehicle_id).get()
    if not doc.exists:
        return jsonify({"status": "error", "message": "Vehicle not found"}), 404
    return jsonify({"status": "ok", "data": doc.to_dict()}), 200


@app.route("/api/vehicles/<string:vehicle_id>/status", methods=["PUT"])
def update_vehicle_status(vehicle_id):
    if db is None:
        return jsonify({"status": "error", "message": "Database not available"}), 500
    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    if not new_status:
        return jsonify({"status": "error", "message": "Missing required field: status"}), 400
    doc_ref = db.collection("vehicles").document(vehicle_id)
    if not doc_ref.get().exists:
        return jsonify({"status": "error", "message": "Vehicle not found"}), 404
    doc_ref.update({"status": new_status})
    return jsonify({"status": "ok", "message": "Status updated"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True)
