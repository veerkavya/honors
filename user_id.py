from flask import Flask, jsonify, request
import threading
from collections import deque
import random

app = Flask(__name__)

# Initialize user_data with deque for tracking last 10 values
user_data = {
    "incoming": deque(maxlen=10),
    "outgoing": deque([random.randint(1000, 9999) for _ in range(10)], maxlen=10),  # Random 10 outgoing users
    "login_time": deque(maxlen=10),
    "vehicle_no": deque(maxlen=10)
}

# Route to GET the current user data (entire queue)
@app.route("/user_data", methods=["GET"])
def get_user_data():
    return jsonify({
        "incoming": list(user_data["incoming"]),
        "outgoing": list(user_data["outgoing"]),
        "login_time": list(user_data["login_time"]),
        "vehicle_no": list(user_data["vehicle_no"])
    })

# Route to manually UPDATE (append) user IDs and login time
@app.route("/update_user_data", methods=["POST"])
def update_user_data():
    data = request.json  # Get JSON data from the request
    if "incoming" in data:
        user_data["incoming"].append(data["incoming"])
    if "outgoing" in data:
        user_data["outgoing"].append(data["outgoing"])
    if "login_time" in data:
        user_data["login_time"].append(data["login_time"])
    if "vehicle_no" in data:
        user_data["vehicle_no"].append(data["vehicle_no"])

    return jsonify({
        "message": "User data updated",
        "data": {
            "incoming": list(user_data["incoming"]),
            "outgoing": list(user_data["outgoing"]),
            "login_time": list(user_data["login_time"]),
            "vehicle_no": list(user_data["vehicle_no"])
        }
    })

# Route to DEQUEUE (remove the front element) from queues
@app.route("/dequeue_user_data", methods=["POST"])
def dequeue_user_data():
    data = request.json  # Get JSON data from the request
    removed_data = {}

    if "incoming" in data and user_data["incoming"]:
        removed_data["incoming"] = user_data["incoming"].popleft()
    if "outgoing" in data and user_data["outgoing"]:
        removed_data["outgoing"] = user_data["outgoing"].popleft()
    if "login_time" in data and user_data["login_time"]:
        removed_data["login_time"] = user_data["login_time"].popleft()
    if "vehicle_no" in data and user_data["vehicle_no"]:
        removed_data["vehicle_no"] = user_data["vehicle_no"].popleft()

    return jsonify({
        "message": "Dequeued user data",
        "removed_data": removed_data,
        "remaining_data": {
            "incoming": list(user_data["incoming"]),
            "outgoing": list(user_data["outgoing"]),
            "login_time": list(user_data["login_time"]),
            "vehicle_no": list(user_data["vehicle_no"])
        }
    })

if __name__ == "__main__":
    # Start Flask server
    app.run(port=5001, debug=True)
