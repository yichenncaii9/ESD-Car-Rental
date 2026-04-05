from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests

app = Flask(__name__)
CORS(app)

# Firestore init — wrapped in try/except so container starts even without credentials
try:
    import firebase_admin
    from firebase_admin import credentials, firestore as fs
    cred = credentials.Certificate(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/secrets/firebase-service-account.json")
    )
    firebase_admin.initialize_app(cred)
    db = fs.client()
except Exception as e:
    print(f"[WARN] Firestore init failed (Phase 1 stub): {e}")
    db = None

DRIVER_HOST = os.environ.get("DRIVER_SERVICE_HOST", "driver_service:5003")
VEHICLE_HOST = os.environ.get("VEHICLE_SERVICE_HOST", "vehicle_service:5001")
PRICING_HOST = os.environ.get("PRICING_SERVICE_HOST", "pricing_service:5005")
BOOKING_HOST = os.environ.get("BOOKING_SERVICE_HOST", "booking_service:5002")
STRIPE_HOST = os.environ.get("STRIPE_WRAPPER_HOST", "stripe_wrapper:6202")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/book-car", methods=["POST"])
def book_car():
    body = request.get_json(silent=True) or {}
    user_uid = body.get("user_uid")
    vehicle_id = body.get("vehicle_id")   # plate number = Firestore doc ID
    vehicle_type = body.get("vehicle_type")
    pickup_datetime = body.get("pickup_datetime")
    hours = body.get("hours")
    payment_method = body.get("payment_method")   # tokenized by Stripe.js frontend

    if not all([user_uid, vehicle_id, vehicle_type, pickup_datetime, hours]):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # Guard: reject if user already has a confirmed booking
    try:
        r = requests.get(f"http://{BOOKING_HOST}/api/bookings/user/{user_uid}/active", timeout=5)
        if r.status_code == 200 and r.json().get("data"):
            return jsonify({"status": "error", "message": "You already have an active booking. Cancel it before making a new one."}), 409
    except Exception as e:
        print(f"[book_car] Could not check existing bookings: {e} — proceeding")

    # Step 1: Fetch driver record to get license_number
    r = requests.get(f"http://{DRIVER_HOST}/api/drivers/{user_uid}", timeout=5)
    if r.status_code != 200:
        return jsonify({"status": "error", "message": f"Driver not found: {r.json().get('message', 'unknown')}"}), 400
    driver = r.json().get("data", r.json())
    license_number = driver.get("license_number")
    if not license_number:
        return jsonify({"status": "error", "message": "Driver has no license_number on record"}), 400

    # Step 2: Validate driver license
    r = requests.post(f"http://{DRIVER_HOST}/api/drivers/validate",
                      json={"license_number": license_number}, timeout=5)
    if r.status_code != 200:
        return jsonify({"status": "error", "message": f"Driver validation error: {r.json().get('message', 'unknown')}"}), 400
    validation = r.json()
    if not validation.get("valid"):
        reason = validation.get("reason", "Invalid license")
        return jsonify({"status": "error", "message": f"Driver license invalid: {reason}"}), 400

    # Step 3: Check vehicle availability
    r = requests.get(f"http://{VEHICLE_HOST}/api/vehicles/{vehicle_id}", timeout=5)
    if r.status_code == 404:
        return jsonify({"status": "error", "message": "Vehicle not found"}), 404
    if r.status_code != 200:
        return jsonify({"status": "error", "message": "Vehicle service error"}), 502
    vehicle = r.json().get("data", r.json())
    if vehicle.get("status") != "available":
        return jsonify({"status": "error", "message": "Vehicle not available"}), 409

    # Step 4: Lock vehicle (set status="rented") before charging — prevents double-booking
    r = requests.put(f"http://{VEHICLE_HOST}/api/vehicles/{vehicle_id}/status",
                     json={"status": "rented"}, timeout=5)
    if r.status_code != 200:
        return jsonify({"status": "error", "message": "Failed to lock vehicle"}), 502

    # Step 5: Get pricing
    r = requests.get(f"http://{PRICING_HOST}/api/pricing/calculate",
                     params={"vehicle_type": vehicle_type, "hours": hours}, timeout=5)
    if r.status_code != 200:
        # Rollback vehicle lock
        requests.put(f"http://{VEHICLE_HOST}/api/vehicles/{vehicle_id}/status",
                     json={"status": "available"}, timeout=5)
        return jsonify({"status": "error", "message": "Pricing service error"}), 502
    total_price = r.json().get("total", 0)

    # Step 6: Charge Stripe
    charge_body = {"amount": total_price, "currency": "sgd"}
    if payment_method:
        charge_body["payment_method"] = payment_method
    r = requests.post(f"http://{STRIPE_HOST}/api/stripe/charge",
                      json=charge_body, timeout=10)
    if r.status_code != 200:
        # Rollback vehicle lock
        requests.put(f"http://{VEHICLE_HOST}/api/vehicles/{vehicle_id}/status",
                     json={"status": "available"}, timeout=5)
        return jsonify({"status": "error", "message": "Payment failed"}), 500
    stripe_resp = r.json()
    payment_intent_id = stripe_resp.get("payment_intent_id")

    # Step 7: Create booking
    booking_body = {
        "user_uid": user_uid,
        "vehicle_id": vehicle_id,
        "vehicle_type": vehicle_type,
        "pickup_datetime": pickup_datetime,
        "hours": hours,
        "total_price": total_price,
        "stripe_payment_intent_id": payment_intent_id,
    }
    r = requests.post(f"http://{BOOKING_HOST}/api/bookings", json=booking_body, timeout=5)
    if r.status_code not in (200, 201):
        # Best-effort rollback: refund Stripe + unlock vehicle
        print(f"[book_car] booking_service failed ({r.status_code}) — attempting rollback")
        try:
            requests.post(f"http://{STRIPE_HOST}/api/stripe/refund",
                          json={"payment_intent_id": payment_intent_id, "amount": total_price}, timeout=10)
        except Exception as e:
            print(f"[book_car] Stripe refund rollback failed: {e}")
        try:
            requests.put(f"http://{VEHICLE_HOST}/api/vehicles/{vehicle_id}/status",
                         json={"status": "available"}, timeout=5)
        except Exception as e:
            print(f"[book_car] Vehicle unlock rollback failed: {e}")
        return jsonify({"status": "error", "message": "Booking creation failed; payment refunded"}), 500

    booking_id = r.json().get("booking_id")
    return jsonify({
        "status": "confirmed",
        "booking_id": booking_id,
        "payment_intent_id": payment_intent_id,
    }), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6001)), debug=True)
