# wrappers/googlemaps_wrapper/app.py — Real Google Maps reverse geocoding with mock fallback (Phase 4)
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import math

app = Flask(__name__)
CORS(app)

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

# Static Singapore landmark lookup — used when Google Maps API is unavailable
_SG_LANDMARKS = [
    ("Woodlands Checkpoint",        1.4469,  103.7691),
    ("Tuas Second Link",            1.3437,  103.6390),
    ("Changi Airport Terminal 1",   1.3592,  103.9894),
    ("Changi Airport Terminal 2",   1.3570,  103.9876),
    ("Changi Airport Terminal 3",   1.3549,  103.9873),
    ("Changi Airport Terminal 4",   1.3360,  103.9826),
    ("Orchard Road",                1.3048,  103.8318),
    ("Marina Bay Sands",            1.2834,  103.8607),
    ("Raffles Place MRT",           1.2830,  103.8513),
    ("Dhoby Ghaut MRT",             1.2993,  103.8455),
    ("Jurong East MRT",             1.3331,  103.7422),
    ("Tampines MRT",                1.3538,  103.9452),
    ("Bishan MRT",                  1.3510,  103.8480),
    ("Ang Mo Kio MRT",              1.3700,  103.8496),
    ("Yishun MRT",                  1.4294,  103.8354),
    ("Boon Lay MRT",                1.3387,  103.7059),
    ("Pasir Ris MRT",               1.3730,  103.9493),
    ("Buona Vista MRT",             1.3072,  103.7900),
    ("HarbourFront MRT",            1.2651,  103.8218),
    ("Paya Lebar MRT",              1.3178,  103.8930),
    ("Sengkang MRT",                1.3916,  103.8954),
    ("Punggol MRT",                 1.4053,  103.9022),
    ("Clementi MRT",                1.3152,  103.7651),
    ("Toa Payoh MRT",               1.3326,  103.8476),
    ("Novena MRT",                  1.3203,  103.8437),
    ("Bukit Timah",                 1.3420,  103.7768),
    ("Sembawang",                   1.4491,  103.8200),
    ("Tuas Industrial Estate",      1.2966,  103.6365),
    ("Pandan Reservoir",            1.3139,  103.7440),
    ("Kent Ridge",                  1.2936,  103.7840),
]


def _haversine_km(lat1, lng1, lat2, lng2):
    """Return great-circle distance in km between two lat/lng points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_sg_landmark(lat, lng, max_km=2.0):
    """Return '<Name>, Singapore' for the nearest landmark within max_km, else 'Singapore'."""
    best_name, best_dist = None, float("inf")
    for name, la, ln in _SG_LANDMARKS:
        d = _haversine_km(float(lat), float(lng), la, ln)
        if d < best_dist:
            best_dist, best_name = d, name
    if best_dist <= max_km:
        return f"{best_name}, Singapore"
    return "Singapore"


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/maps/geocode", methods=["POST"])
def geocode():
    """
    Reverse geocode lat/lng to a human-readable address using Google Maps.
    Mock fallback: if Google Maps fails, returns nearest Singapore landmark name as address.
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
        print(f"[googlemaps_wrapper] Google Maps API failed, using SG landmark fallback: {e}")
        fallback_address = _nearest_sg_landmark(lat, lng)
        return jsonify({
            "status": "ok",
            "address": fallback_address,
            "provider": "fallback",
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6201)), debug=True)
