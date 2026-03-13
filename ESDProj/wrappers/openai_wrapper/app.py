# wrappers/openai_wrapper/app.py — Phase 1 stub
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/openai/evaluate", methods=["POST"])
def evaluate():
    # Phase 1 stub — real OpenAI call in Phase 4/5
    return jsonify({"status": "ok", "severity": "medium", "message": "Phase 1 stub"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6200)), debug=True)
