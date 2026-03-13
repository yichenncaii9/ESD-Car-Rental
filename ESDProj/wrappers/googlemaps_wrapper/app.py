# wrappers/googlemaps_wrapper/app.py — Phase 1 stub
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/maps/geocode", methods=["POST"])
def geocode():
    # Phase 1 stub — real Google Maps call in Phase 4/5
    return jsonify({"status": "ok", "address": "Phase 1 stub", "lat": 1.3521, "lng": 103.8198}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6201)), debug=True)
