# websocket_server/app.py — Phase 1 stub
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import os

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/notify", methods=["POST"])
def notify():
    # Phase 1 stub — real Socket.IO emit in Phase 5
    data = request.get_json() or {}
    print(f"[websocket_server] /notify received: {data}")
    return jsonify({"status": "ok", "message": "Phase 1 stub"}), 200


@socketio.on("connect")
def on_connect():
    print("[websocket_server] Client connected")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 6100)), debug=True)
