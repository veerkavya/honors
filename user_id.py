from flask import Flask, jsonify, request
import random
import time
import threading

app = Flask(__name__)

# Shared user ID data
user_id_data = {"incoming": None, "outgoing": None}

def auto_update_user_ids():
    """Periodically updates user IDs in the background."""
    while True:
        user_id_data["incoming"] = random.randint(1000, 9999)
        user_id_data["outgoing"] = random.randint(1000, 9999)
        print(f"Auto Updated IDs: {user_id_data}")
        time.sleep(10)  # Update every 10 seconds

# Route to GET the current user IDs
@app.route("/user_ids", methods=["GET"])
def get_user_ids():
    return jsonify(user_id_data)

# Route to manually UPDATE user IDs using a POST request
@app.route("/update_user_ids", methods=["POST"])
def update_user_ids():
    data = request.json  # Get JSON data from the request
    if "incoming" in data:
        user_id_data["incoming"] = data["incoming"]
    if "outgoing" in data:
        user_id_data["outgoing"] = data["outgoing"]
    return jsonify({"message": "User IDs updated", "data": user_id_data})

if __name__ == "__main__":
    # Start the background thread for auto-updating user IDs
    thread = threading.Thread(target=auto_update_user_ids, daemon=True)
    thread.start()

    # Start Flask server
    app.run(port=5001, debug=True)
