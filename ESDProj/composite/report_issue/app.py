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


@app.route("/api/report-issue", methods=["POST"])
def report_issue():
    # Phase 1 stub — real orchestration logic implemented in Phase 4
    return jsonify({"status": "ok", "message": "Phase 1 stub — real logic in Phase 4"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6003)), debug=True)
