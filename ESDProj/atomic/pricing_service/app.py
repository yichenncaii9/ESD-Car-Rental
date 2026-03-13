from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# No Firestore — pricing rates are hardcoded (OutSystems placeholder)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/pricing", methods=["GET"])
def get_pricing():
    # Phase 1 stub — returns hardcoded rates (OutSystems placeholder)
    return jsonify({
        "status": "ok",
        "rates": {
            "sedan": 12.50,
            "suv": 18.00,
            "van": 15.00
        }
    }), 200


@app.route("/api/pricing/calculate", methods=["GET"])
def calculate_pricing():
    # Phase 1 stub — real calculation logic in Phase 3
    return jsonify({"status": "ok", "total": 0, "message": "Phase 1 stub"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5005)), debug=True)
