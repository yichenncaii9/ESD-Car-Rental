# wrappers/openai_wrapper/app.py — GPT-4o vision severity classification (Phase 5)
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
import os

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

SYSTEM_PROMPT = (
    "You are a vehicle incident severity classifier for a car rental service. "
    "Given an incident description, location, and optional photo, classify the severity "
    "as exactly one of: low, medium, or high. "
    "low = minor cosmetic damage or inconvenience. "
    "medium = functional issue requiring service. "
    "high = safety hazard or major damage. "
    "Respond with only the single word: low, medium, or high."
)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/openai/evaluate", methods=["POST"])
def evaluate():
    """
    Classify incident severity using OpenAI GPT-4o (with optional vision).
    Mock fallback: if OpenAI fails, returns severity="medium".

    Request body:
      { description: str, address: str, image_base64?: str }
      image_base64 is a base64-encoded JPEG/PNG (no data-URI prefix needed;
      the wrapper adds the prefix automatically).

    Response:
      { status: "ok", severity: "low"|"medium"|"high", provider: "openai"|"fallback" }
    """
    body = request.get_json(silent=True) or {}
    description = body.get("description", "")
    address = body.get("address", "Unknown location")
    image_base64 = body.get("image_base64")  # optional

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        text_content = f"Location: {address}\nIncident: {description}"

        if image_base64:
            # Vision message: array with text part + image_url part
            user_content = [
                {"type": "text", "text": text_content},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                        "detail": "low",   # low = 65 tokens, sufficient for damage assessment
                    },
                },
            ]
        else:
            # Text-only message: plain string (backwards-compatible)
            user_content = text_content

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=10,
            temperature=0,
        )
        severity = response.choices[0].message.content.strip().lower()
        if severity not in ("low", "medium", "high"):
            severity = "medium"
        return jsonify({"status": "ok", "severity": severity, "provider": "openai"}), 200

    except Exception as e:
        print(f"[openai_wrapper] OpenAI API failed, using mock fallback: {e}")
        return jsonify({"status": "ok", "severity": "medium", "provider": "fallback"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6200)), debug=True)
