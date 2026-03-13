# wrappers/stripe_wrapper/app.py — Phase 1 stub
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/stripe/charge", methods=["POST"])
def charge():
    # Phase 1 stub — real Stripe charge in Phase 3/4
    return jsonify({"status": "ok", "payment_intent_id": "pi_stub_phase1", "message": "Phase 1 stub"}), 200


@app.route("/api/stripe/refund", methods=["POST"])
def refund():
    # Phase 1 stub — real Stripe refund in Phase 3/4
    return jsonify({"status": "ok", "refund_id": "re_stub_phase1", "message": "Phase 1 stub"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6202)), debug=True)
