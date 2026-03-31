import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import os

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json() or {}
    print(f"[websocket_server] /notify received: {data}")
    socketio.emit("report_update", {
        **data,
        "id": data.get("report_id")   # REQUIRED — ServiceDashboardView findIndex matches r.id === data.id
    })
    return jsonify({"status": "ok"}), 200


@socketio.on("connect")
def on_connect():
    print("[websocket_server] Client connected")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 6100)))
