# wrappers/openai_wrapper/app.py — Real OpenAI severity classification with mock fallback (Phase 4)
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/openai/evaluate", methods=["POST"])
def evaluate():
    """
    Classify incident severity using OpenAI GPT-3.5-turbo.
    Mock fallback: if OpenAI fails, returns severity="medium".
    Request body: { description: str, address: str }
    Response: { status: "ok", severity: "low"|"medium"|"high", provider: "openai"|"fallback" }
    """
    body = request.get_json(silent=True) or {}
    description = body.get("description", "")
    address = body.get("address", "Unknown location")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a vehicle incident severity classifier for a car rental service. "
                        "Given an incident description and location, classify the severity as exactly one of: low, medium, or high. "
                        "low = minor cosmetic damage or inconvenience. "
                        "medium = functional issue requiring service. "
                        "high = safety hazard or major damage. "
                        "Respond with only the single word: low, medium, or high."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Location: {address}\nIncident: {description}",
                },
            ],
            max_tokens=10,
            temperature=0,
        )
        severity = response.choices[0].message.content.strip().lower()
        # Validate response is one of the expected values
        if severity not in ("low", "medium", "high"):
            severity = "medium"
        return jsonify({
            "status": "ok",
            "severity": severity,
            "provider": "openai",
        }), 200
    except Exception as e:
        print(f"[openai_wrapper] OpenAI API failed, using mock fallback: {e}")
        return jsonify({
            "status": "ok",
            "severity": "medium",
            "provider": "fallback",
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6200)), debug=True)
