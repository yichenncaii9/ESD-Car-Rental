import os, json, uuid, time
import pika
import requests

RABBITMQ_HOST       = os.environ.get("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT       = int(os.environ.get("RABBITMQ_PORT", 5672))
WEBSOCKET_URL       = os.environ.get("WEBSOCKET_SERVER_URL", "http://websocket_server:6100")
DRIVER_HOST         = os.environ.get("DRIVER_SERVICE_HOST", "driver_service:5003")
TWILIO_ACCOUNT_SID  = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER  = os.environ.get("TWILIO_FROM_NUMBER", "+15005550006")
TWILIO_SERVICE_TEAM = os.environ.get("TWILIO_SERVICE_TEAM_NUMBER")
EXCHANGE_NAME       = "report_topic"
QUEUE_NAME          = "twilio_queue"
ROUTING_KEY         = "report.new"


def send_sms(to, body):
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(body=body, from_=TWILIO_FROM_NUMBER, to=to)
        return msg.sid, "twilio"
    except Exception as e:
        print(f"[twilio_wrapper] Twilio failed, using mock: {e}")
        return f"mock_{uuid.uuid4().hex}", "fallback"


def connect_with_retry(max_attempts=5):
    for attempt in range(1, max_attempts + 1):
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    heartbeat=60
                )
            )
            print(f"[twilio_wrapper] Connected to RabbitMQ on attempt {attempt}")
            return connection
        except Exception as e:
            wait = 2 ** attempt
            print(f"[twilio_wrapper] RabbitMQ not ready (attempt {attempt}/{max_attempts}): {e}. Retrying in {wait}s")
            if attempt == max_attempts:
                raise
            time.sleep(wait)


def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        report_id  = data.get("report_id")
        vehicle_id = data.get("vehicle_id")
        severity   = data.get("severity")
        location   = data.get("location")
        user_uid   = data.get("user_uid")

        # Send SMS to service team
        if TWILIO_SERVICE_TEAM:
            msg = (
                f"[ESD Rental] New incident reported. "
                f"Report: {report_id} | Vehicle: {vehicle_id} | "
                f"Severity: {severity} | Location: {location}"
            )
            sid, provider = send_sms(TWILIO_SERVICE_TEAM, msg)
            print(f"[twilio_wrapper] Service team SMS sent: {sid} ({provider})")

        # Fetch driver phone and send driver SMS (non-fatal)
        try:
            r = requests.get(f"http://{DRIVER_HOST}/api/drivers/{user_uid}", timeout=5)
            if r.status_code == 200:
                driver_phone = r.json().get("phone_number")
                if driver_phone:
                    driver_msg = (
                        f"[ESD Rental] Your incident report {report_id} has been received. "
                        f"Our team is reviewing it."
                    )
                    sid2, provider2 = send_sms(driver_phone, driver_msg)
                    print(f"[twilio_wrapper] Driver SMS sent: {sid2} ({provider2})")
        except Exception as e:
            print(f"[twilio_wrapper] Driver phone fetch failed (non-fatal): {e}")

        # POST to websocket_server
        try:
            requests.post(
                f"{WEBSOCKET_URL}/notify",
                json={"report_id": report_id, "event": "sms_sent",
                      "severity": severity, "message": "SMS notifications sent"},
                timeout=5
            )
        except Exception as e:
            print(f"[twilio_wrapper] websocket notify failed: {e}")

    except Exception as e:
        print(f"[twilio_wrapper] callback error: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    connection = connect_with_retry()
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE_NAME, routing_key=ROUTING_KEY)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    print(f"[twilio_wrapper] Waiting for messages on {QUEUE_NAME}...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
