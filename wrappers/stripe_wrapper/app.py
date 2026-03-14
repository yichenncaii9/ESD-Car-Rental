# wrappers/stripe_wrapper/app.py — Real Stripe SDK with mock failover (Phase 4)
# PSP failover architecture: Stripe primary → mock secondary
# Composites receive same response shape regardless of which path was taken
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import uuid

import stripe

app = Flask(__name__)
CORS(app)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/stripe/charge", methods=["POST"])
def charge():
    """
    Charge a payment method via Stripe PaymentIntent (test mode).
    Mock failover: if Stripe fails for any reason, returns a mock payment_intent_id.
    Request body: { amount: float (dollars), currency: str, payment_method: str }
    Response: { status: "ok", payment_intent_id: str, provider: "stripe"|"fallback" }
    """
    body = request.get_json(silent=True) or {}
    amount_dollars = float(body.get("amount", 0))
    amount_cents = int(round(amount_dollars * 100))
    currency = body.get("currency", "sgd")
    payment_method = body.get("payment_method", "pm_card_visa")

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            payment_method=payment_method,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
        return jsonify({
            "status": "ok",
            "payment_intent_id": intent.id,
            "provider": "stripe",
        }), 200
    except Exception as e:
        print(f"[stripe_wrapper] Stripe charge failed, using mock fallback: {e}")
        mock_id = f"mock_{uuid.uuid4().hex}"
        return jsonify({
            "status": "ok",
            "payment_intent_id": mock_id,
            "provider": "fallback",
        }), 200


@app.route("/api/stripe/refund", methods=["POST"])
def refund():
    """
    Refund a PaymentIntent via Stripe.
    Mock failover: if Stripe fails, returns mock refund_id.
    Request body: { payment_intent_id: str, amount: float (dollars) }
    Response: { status: "ok", refund_id: str, provider: "stripe"|"fallback" }
    """
    body = request.get_json(silent=True) or {}
    payment_intent_id = body.get("payment_intent_id", "")
    amount_dollars = float(body.get("amount", 0))
    amount_cents = int(round(amount_dollars * 100)) if amount_dollars > 0 else None

    # Mock intents cannot be refunded via real Stripe API — detect and short-circuit
    if payment_intent_id.startswith("mock_"):
        mock_refund_id = f"mock_re_{uuid.uuid4().hex}"
        print(f"[stripe_wrapper] Mock payment_intent_id detected — returning mock refund")
        return jsonify({
            "status": "ok",
            "refund_id": mock_refund_id,
            "provider": "fallback",
        }), 200

    try:
        refund_params = {"payment_intent": payment_intent_id}
        if amount_cents:
            refund_params["amount"] = amount_cents
        re = stripe.Refund.create(**refund_params)
        return jsonify({
            "status": "ok",
            "refund_id": re.id,
            "provider": "stripe",
        }), 200
    except Exception as e:
        print(f"[stripe_wrapper] Stripe refund failed, using mock fallback: {e}")
        mock_refund_id = f"mock_re_{uuid.uuid4().hex}"
        return jsonify({
            "status": "ok",
            "refund_id": mock_refund_id,
            "provider": "fallback",
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 6202)), debug=True)
