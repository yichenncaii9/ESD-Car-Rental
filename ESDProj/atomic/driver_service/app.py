from flask import Flask, jsonify
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


@app.route("/api/drivers/<string:uid>", methods=["GET"])
def get_driver(uid):
    # Phase 1 stub — real logic in Phase 3
    return jsonify({"status": "ok", "data": {}, "message": "Phase 1 stub"}), 200


@app.route("/api/drivers/validate", methods=["POST"])
def validate_driver():
    # Phase 1 stub — real logic in Phase 3
    return jsonify({"status": "ok", "valid": True, "message": "Phase 1 stub"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5003)), debug=True)
