from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# No Firestore — pricing rates are hardcoded (OutSystems placeholder)

RATES = {"sedan": 12.50, "suv": 18.00, "van": 15.00}


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
    vehicle_type = request.args.get("vehicle_type", "").lower()
    hours_str = request.args.get("hours", "")

    if vehicle_type not in RATES:
        return jsonify({"status": "error", "message": "Invalid vehicle_type"}), 400

    try:
        hours = float(hours_str)
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid hours"}), 400

    total = round(RATES[vehicle_type] * hours, 2)
    return jsonify({
        "status": "ok",
        "vehicle_type": vehicle_type,
        "hours": hours,
        "total": total
    }), 200


@app.route("/api/pricing/policy", methods=["GET"])
def get_pricing_policy():
    return jsonify({
        "status": "ok",
        "tiers": [
            {"hours_before": 24, "refund_percent": 100},
            {"hours_before": 1,  "refund_percent": 50},
            {"hours_before": 0,  "refund_percent": 0}
        ]
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5005)), debug=True)
