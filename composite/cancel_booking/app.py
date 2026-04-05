import requests
import os
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

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

BOOKING_HOST = os.environ.get("BOOKING_SERVICE_HOST", "booking_service:5002")
VEHICLE_HOST = os.environ.get("VEHICLE_SERVICE_HOST", "vehicle_service:5001")
PRICING_HOST = os.environ.get("PRICING_SERVICE_HOST", "pricing_service:5005")
STRIPE_HOST = os.environ.get("STRIPE_WRAPPER_HOST", "stripe_wrapper:6202")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/cancel-booking", methods=["POST"])
def cancel_booking():
    body = request.get_json(silent=True) or {}
    booking_id = body.get("booking_id")
    if not booking_id:
        return jsonify({"status": "error", "message": "Missing required field: booking_id"}), 400

    # Step 1: Fetch booking
    r = requests.get(f"http://{BOOKING_HOST}/api/bookings/{booking_id}", timeout=5)
    if r.status_code == 404:
        return jsonify({"status": "error", "message": "Booking not found"}), 404
    if r.status_code != 200:
        return jsonify({"status": "error", "message": "Booking service error"}), 502
    booking = r.json().get("data", r.json())

    # Step 2: Validate booking is cancellable (COMP-03)
    booking_status = booking.get("status")
    if booking_status != "confirmed":
        return jsonify({
            "status": "error",
            "message": f"Booking cannot be cancelled (current status: {booking_status})"
        }), 400

    # Step 3: Compute hours before pickup for cancellation policy (COMP-04)
    pickup_datetime_str = booking.get("pickup_datetime", "")
    try:
        pickup_dt = datetime.fromisoformat(pickup_datetime_str)
        now = datetime.utcnow()
        hours_before_pickup = (pickup_dt - now).total_seconds() / 3600
    except (ValueError, TypeError):
        # Cannot parse pickup_datetime — default to 0% refund (safe conservative choice)
        hours_before_pickup = 0
        print(f"[cancel_booking] Could not parse pickup_datetime: {pickup_datetime_str!r}")

    # Reject cancellation if pickup time has already passed
    if hours_before_pickup <= 0:
        return jsonify({
            "status": "error",
            "message": "Cannot cancel a booking whose pickup time has already passed."
        }), 400

    # Step 4: Fetch cancellation policy tiers from pricing_service
    total_price = float(booking.get("total_price", 0))
    refund_percent = 0
    try:
        r = requests.get(f"http://{PRICING_HOST}/api/pricing/policy", timeout=5)
        if r.status_code == 200:
            tiers = r.json().get("tiers", [])
            # Tiers expected: [{"hours_before": 24, "refund_percent": 100}, ...]
            # Sort descending by hours_before so the highest threshold is checked first
            for tier in sorted(tiers, key=lambda t: t.get("hours_before", 0), reverse=True):
                if hours_before_pickup > tier.get("hours_before", 0):
                    refund_percent = tier.get("refund_percent", 0)
                    break
        else:
            print(f"[cancel_booking] Pricing policy unavailable ({r.status_code}) — using 0% refund")
    except Exception as e:
        print(f"[cancel_booking] Pricing service error: {e} — using 0% refund")

    refund_amount = round(total_price * refund_percent / 100, 2)

    # Step 5: Attempt Stripe refund (COMP-05, COMP-06)
    payment_intent_id = booking.get("stripe_payment_intent_id", "")
    refund_status = "pending_manual"
    if refund_amount > 0 and payment_intent_id:
        try:
            r = requests.post(f"http://{STRIPE_HOST}/api/stripe/refund",
                              json={"payment_intent_id": payment_intent_id, "amount": refund_amount},
                              timeout=10)
            if r.status_code == 200:
                refund_status = "processed"
            else:
                print(f"[cancel_booking] Stripe refund returned {r.status_code} — flagging pending_manual")
        except Exception as e:
            print(f"[cancel_booking] Stripe refund exception: {e} — flagging pending_manual")
    elif refund_amount == 0:
        # 0% refund — no Stripe call needed, mark as processed (nothing to refund)
        refund_status = "processed"

    # Step 6: Cancel booking in booking_service
    r = requests.put(f"http://{BOOKING_HOST}/api/bookings/{booking_id}/status",
                     json={"status": "cancelled"}, timeout=5)
    if r.status_code != 200:
        print(f"[cancel_booking] booking_service status update failed ({r.status_code})")

    # Step 7: Write refund_status to Firestore directly if pending_manual
    # (booking_service PUT /status only updates "status" field — cannot set refund_status)
    if refund_status == "pending_manual" and db is not None:
        try:
            db.collection("bookings").document(booking_id).update({"refund_status": "pending_manual"})
        except Exception as e:
            print(f"[cancel_booking] Firestore refund_status update failed: {e}")

    # Step 8: Release vehicle
    vehicle_id = booking.get("vehicle_id")
    if vehicle_id:
        try:
            requests.put(f"http://{VEHICLE_HOST}/api/vehicles/{vehicle_id}/status",
                         json={"status": "available"}, timeout=5)
        except Exception as e:
            print(f"[cancel_booking] Vehicle release failed: {e}")

    # Return COMP-07 response shape
    return jsonify({
        "booking_id": booking_id,
        "status": "cancelled",
        "refund_amount": refund_amount,
        "refund_status": refund_status,
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6002)), debug=True)
