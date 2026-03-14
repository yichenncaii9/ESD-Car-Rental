from flask import Flask, jsonify, request
from flask_cors import CORS
import datetime
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


@app.route("/api/reports", methods=["POST"])
def create_report():
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    body = request.get_json(silent=True) or {}
    required = ["booking_id", "vehicle_id", "user_uid", "location", "description"]
    for field in required:
        if field not in body:
            return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
    report_doc = {
        "booking_id":    body["booking_id"],
        "vehicle_id":    body["vehicle_id"],
        "user_uid":      body["user_uid"],
        "location":      body["location"],
        "description":   body["description"],
        "severity":      None,
        "status":        "pending",
        "created_at":    datetime.datetime.utcnow().isoformat(),
        "resolved_at":   None,
        "resolution":    None,
        "ai_evaluation": None,
    }
    update_time, doc_ref = db.collection("reports").add(report_doc)
    return jsonify({"status": "ok", "report_id": doc_ref.id, "message": "Report created"}), 201


@app.route("/api/reports/pending", methods=["GET"])
def get_pending_reports():
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    try:
        docs = db.collection("reports").where("status", "!=", "resolved").stream()
        results = [{"id": d.id, **d.to_dict()} for d in docs]
    except Exception:
        # Fallback: fetch all and filter in Python (if Firestore composite index not yet created)
        all_docs = db.collection("reports").stream()
        results = [{"id": d.id, **d.to_dict()} for d in all_docs
                   if d.to_dict().get("status") != "resolved"]
    return jsonify({"status": "ok", "data": results}), 200


@app.route("/api/reports/<string:report_id>", methods=["GET"])
def get_report(report_id):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    doc = db.collection("reports").document(report_id).get()
    if not doc.exists:
        return jsonify({"status": "error", "message": "Report not found"}), 404
    return jsonify({"status": "ok", "data": {"id": doc.id, **doc.to_dict()}}), 200


@app.route("/api/reports/<string:report_id>/evaluation", methods=["PUT"])
def update_report_evaluation(report_id):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    body = request.get_json(silent=True) or {}
    severity = body.get("severity")
    if not severity:
        return jsonify({"status": "error", "message": "Missing required field: severity"}), 400
    doc_ref = db.collection("reports").document(report_id)
    if not doc_ref.get().exists:
        return jsonify({"status": "error", "message": "Report not found"}), 404
    doc_ref.update({
        "severity":      severity,
        "ai_evaluation": body.get("ai_evaluation"),
    })
    return jsonify({"status": "ok", "message": "Evaluation updated"}), 200


@app.route("/api/reports/<string:report_id>/resolution", methods=["PUT"])
def update_report_resolution(report_id):
    if db is None:
        return jsonify({"status": "error", "message": "Firestore unavailable"}), 500
    body = request.get_json(silent=True) or {}
    resolution = body.get("resolution")
    if not resolution:
        return jsonify({"status": "error", "message": "Missing required field: resolution"}), 400
    doc_ref = db.collection("reports").document(report_id)
    if not doc_ref.get().exists:
        return jsonify({"status": "error", "message": "Report not found"}), 404
    doc_ref.update({
        "resolution":  resolution,
        "status":      "resolved",
        "resolved_at": datetime.datetime.utcnow().isoformat(),
    })
    return jsonify({"status": "ok", "message": "Resolution updated"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5004)), debug=True)
