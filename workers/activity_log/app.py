import os, json, time, datetime
import pika
import requests
import firebase_admin
from firebase_admin import credentials, firestore as fs

RABBITMQ_HOST  = os.environ.get("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT  = int(os.environ.get("RABBITMQ_PORT", 5672))
WEBSOCKET_URL  = os.environ.get("WEBSOCKET_SERVER_URL", "http://websocket_server:6100")
EXCHANGE_NAME  = "report_topic"
QUEUE_NAME     = "activity_queue"
ROUTING_KEY    = "report.new"

try:
    cred = credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/secrets/firebase-service-account.json"))
    firebase_admin.initialize_app(cred)
    db = fs.client()
except Exception as e:
    print(f"[activity_log] Firestore init failed: {e}")
    db = None


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
            print(f"[activity_log] Connected to RabbitMQ on attempt {attempt}")
            return connection
        except Exception as e:
            wait = 2 ** attempt
            print(f"[activity_log] RabbitMQ not ready (attempt {attempt}/{max_attempts}): {e}. Retrying in {wait}s")
            if attempt == max_attempts:
                raise
            time.sleep(wait)


def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        report_id = data.get("report_id")
        severity = data.get("severity")

        if db is not None:
            try:
                db.collection("activity_log").add({
                    "report_id": report_id,
                    "event":     "report.new",
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "severity":  severity,
                })
                print(f"[activity_log] Firestore write: report_id={report_id}")
            except Exception as e:
                print(f"[activity_log] Firestore write failed: {e}")

        try:
            requests.post(
                f"{WEBSOCKET_URL}/notify",
                json={"report_id": report_id, "event": "activity_logged",
                      "severity": severity, "message": "Activity logged"},
                timeout=5
            )
        except Exception as e:
            print(f"[activity_log] websocket notify failed: {e}")

    except Exception as e:
        print(f"[activity_log] callback error: {e}")
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
    print(f"[activity_log] Waiting for messages on {QUEUE_NAME}...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
