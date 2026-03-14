# wrappers/twilio_wrapper/app.py — HTTP Flask wrapper for Twilio SMS (Phase 4)
# Called synchronously by composite/resolve_issue via POST /api/twilio/sms
# Mock failover: tries real Twilio API → falls back to mock if Twilio fails or creds missing
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import uuid

app = Flask(__name__)
CORS(app)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "+15005550006")  # Twilio test number


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/twilio/sms", methods=["POST"])
def send_sms():
    body = request.get_json(silent=True) or {}
    to = body.get("to")
    message = body.get("body", "")
    if not to:
        return jsonify({"status": "error", "message": "Missing required field: to"}), 400
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_FROM_NUMBER,
            to=to,
        )
        return jsonify({"status": "ok", "message_sid": msg.sid, "provider": "twilio"}), 200
    except Exception as e:
        print(f"[twilio_wrapper] Twilio API failed, using mock fallback: {e}")
        mock_sid = f"mock_{uuid.uuid4().hex}"
        return jsonify({"status": "ok", "message_sid": mock_sid, "provider": "fallback"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6203)), debug=True)
