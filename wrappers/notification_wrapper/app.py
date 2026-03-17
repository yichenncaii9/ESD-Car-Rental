# wrappers/notification_wrapper/app.py — HTTP Flask wrapper for SMU Notification API
# Called synchronously by composite/resolve_issue via POST /api/notification/sms
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import uuid
import requests

app = Flask(__name__)
CORS(app)

SMU_SMS_URL = "https://smuedu-dev.outsystemsenterprise.com/SMULab_Notification/rest/Notification/SendSMS"


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/notification/sms", methods=["POST"])
def send_sms():
    body = request.get_json(silent=True) or {}
    to = body.get("to")
    message = body.get("body", "")
    if not to:
        return jsonify({"status": "error", "message": "Missing required field: to"}), 400
    try:
        r = requests.post(SMU_SMS_URL, json={"mobile": to, "message": message}, timeout=10)
        if r.status_code == 200:
            result = r.json()
            return jsonify({"status": "ok", "message_sid": result.get("status", "sent"), "provider": "smu"}), 200
        raise Exception(f"SMU API returned {r.status_code}")
    except Exception as e:
        print(f"[notification_wrapper] SMU SMS failed, using mock fallback: {e}")
        mock_sid = f"mock_{uuid.uuid4().hex}"
        return jsonify({"status": "ok", "message_sid": mock_sid, "provider": "fallback"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6203)), debug=True)
