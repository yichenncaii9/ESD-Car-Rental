# wrappers/openai_wrapper/app.py — GPT-4o vision severity classification (Phase 5)
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
import os
import json

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

SYSTEM_PROMPT = (
    "You are a vehicle incident assessor for a car rental service. "
    "Given an incident description, location, and optional photo, return a JSON object with exactly these keys:\n"
    "- \"severity\": one of \"low\", \"medium\", \"high\"\n"
    "- \"diagnosis\": short phrase naming the issue (e.g. \"scratched car rim\", \"flat tyre\", \"cracked windscreen\")\n"
    "- \"recommended_action\": one sentence the service team should take\n"
    "- \"safe_to_drive\": boolean, true only if the vehicle poses no safety risk\n\n"
    "low = minor cosmetic damage. medium = functional issue requiring service. high = safety hazard or major damage."
)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/openai/evaluate", methods=["POST"])
def evaluate():
    """
    Assess incident using OpenAI GPT-4o (with optional vision) and return enriched data.
    Mock fallback: if OpenAI fails, returns severity="medium" with placeholder values.

    Request body:
      { description: str, address: str, image_base64?: str, image_mime_type?: str }
      image_base64 is a base64-encoded image (no data-URI prefix needed;
      the wrapper adds the prefix automatically).
      image_mime_type defaults to "image/jpeg" if omitted (e.g. use "image/png" for PNG).

    Response:
      { status: "ok", severity: "low"|"medium"|"high", diagnosis: str, recommended_action: str, safe_to_drive: bool, provider: "openai"|"fallback" }
    """
    body = request.get_json(silent=True) or {}
    description = body.get("description", "")
    address = body.get("address", "Unknown location")
    image_base64 = body.get("image_base64")  # optional
    image_mime_type = body.get("image_mime_type", "image/jpeg")

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
                        "url": f"data:{image_mime_type};base64,{image_base64}",
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
            response_format={"type": "json_object"},
            max_tokens=150,
            temperature=0,
        )
        result = json.loads(response.choices[0].message.content)
        severity = result.get("severity", "medium").lower()
        if severity not in ("low", "medium", "high"):
            severity = "medium"
        return jsonify({
            "status": "ok",
            "severity": severity,
            "diagnosis": result.get("diagnosis", "unknown"),
            "recommended_action": result.get("recommended_action", "Inspect vehicle"),
            "safe_to_drive": bool(result.get("safe_to_drive", False)),
            "provider": "openai",
        }), 200

    except Exception as e:
        print(f"[openai_wrapper] OpenAI API failed, using mock fallback: {e}")
        return jsonify({
            "status": "ok",
            "severity": "medium",
            "diagnosis": "unknown",
            "recommended_action": "Inspect vehicle before next rental",
            "safe_to_drive": False,
            "provider": "fallback",
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6200)), debug=True)
