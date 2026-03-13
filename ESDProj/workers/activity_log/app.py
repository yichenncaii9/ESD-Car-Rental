# workers/activity_log/app.py — Phase 1 stub
import os
import time

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
# Exchange name declared here so Phase 5 wiring is self-documenting.
# Real pika consumer subscribes to this exchange with key "report.new" in Phase 5.
EXCHANGE_NAME = "report_topic"

print(f"[activity_log] Phase 1 stub started. Will connect to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT} exchange={EXCHANGE_NAME} in Phase 5.")

# Keep container alive (real consumer loop in Phase 5)
while True:
    time.sleep(60)
