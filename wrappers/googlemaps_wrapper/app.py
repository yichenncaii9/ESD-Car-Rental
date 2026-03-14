# wrappers/googlemaps_wrapper/app.py — Real Google Maps reverse geocoding with mock fallback (Phase 4)
from flask import Flask, jsonify, request
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/maps/geocode", methods=["POST"])
def geocode():
    """
    Reverse geocode lat/lng to a human-readable address using Google Maps.
    Mock fallback: if Google Maps fails, returns coordinate string as address.
    Request body: { lat: float, lng: float }
    Response: { status: "ok", address: str, provider: "googlemaps"|"fallback" }
    """
    body = request.get_json(silent=True) or {}
    lat = body.get("lat")
    lng = body.get("lng")

    if lat is None or lng is None:
        return jsonify({"status": "error", "message": "Missing required fields: lat, lng"}), 400

    try:
        import googlemaps
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        results = gmaps.reverse_geocode((float(lat), float(lng)))
        if results:
            address = results[0]["formatted_address"]
        else:
            address = f"{lat},{lng}"
        return jsonify({
            "status": "ok",
            "address": address,
            "provider": "googlemaps",
        }), 200
    except Exception as e:
        print(f"[googlemaps_wrapper] Google Maps API failed, using mock fallback: {e}")
        fallback_address = f"{lat},{lng}"
        return jsonify({
            "status": "ok",
            "address": fallback_address,
            "provider": "fallback",
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6201)), debug=True)
