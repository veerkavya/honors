import cv2
import sqlite3
import time
import numpy as np
import requests  # For API calls
from datetime import datetime

# Correct Flask API URL (port 5001)
FLASK_API_URL = "http://localhost:5001/update_user_data"

def generate_random_name(vehicle_no):
    """Generates a random name based on the vehicle number."""
    return f"Guest_{vehicle_no}"

def assign_parking(vehicle_no):
    """
    Assigns a parking slot to the detected vehicle and updates the Flask API.
    """
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT user_id, type_id FROM Users WHERE vehicle_no = ?", (vehicle_no,))
    user = cursor.fetchone()

    if user is None:
        # Register new Guest user
        random_name = generate_random_name(vehicle_no)
        type_id = 2  # Guest
        cursor.execute("INSERT INTO Users (name, vehicle_no, type_id) VALUES (?, ?, ?)", (random_name, vehicle_no, type_id))
        conn.commit()
        cursor.execute("SELECT user_id FROM Users WHERE vehicle_no = ?", (vehicle_no,))
        user_id = cursor.fetchone()[0]
        print(f"New user added: {random_name} ({vehicle_no}) as Guest.")
    else:
        user_id, type_id = user

    # Determine parking slot preference
    desired_type = 'faculty' if type_id == 1 else 'guest'

    # Find an empty parking slot
    if desired_type == 'faculty':
        cursor.execute("SELECT slot_id, slot_no, slot_type FROM Slots WHERE slot_type = 'faculty' AND status = 'empty'")
        slot = cursor.fetchone()
        if slot is None:
            cursor.execute("SELECT slot_id, slot_no, slot_type FROM Slots WHERE slot_type = 'guest' AND status = 'empty'")
            slot = cursor.fetchone()
    else:
        cursor.execute("SELECT slot_id, slot_no, slot_type FROM Slots WHERE slot_type = 'guest' AND status = 'empty'")
        slot = cursor.fetchone()

    if slot is None:
        conn.close()
        print("No available parking slots.")  # Notify no slots available
        return None, None, None

    # Assign slot
    slot_id, slot_no, slot_type = slot
    cursor.execute("UPDATE Slots SET status = 'waiting', car_license_plate = ? WHERE slot_id = ?", (vehicle_no, slot_id))

    # Get current time
    now = datetime.now()
    login_time = now.strftime("%H:%M:%S")

    # Commit database changes
    conn.commit()
    conn.close()

    print(f"Assigned {vehicle_no} to Slot {slot_no} ({slot_type})")

    # **Update the Flask API with user_id and login_time**
    try:
        payload = {
            "incoming": user_id,  # Appending user_id
            "login_time": login_time,  # Appending login_time
            "vehicle_no": vehicle_no
        }
        response = requests.post(FLASK_API_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ Updated Flask API: {payload}")
        else:
            print(f"❌ Failed to update Flask API: {response.text}")
    except Exception as e:
        print(f"⚠️ Error updating Flask API: {e}")

    return slot_no, slot_type, user_id

def custom_sink(result, video_frame):
    """
    Processes the detected vehicle number and assigns a parking slot.
    """
    visualization = result["line_counter_visualization"]
    if result.get("google_gemini"):
        print(result["google_gemini"])
    cv2.imshow("Video Feed", visualization.numpy_image)
    cv2.waitKey(1)

    detected_plate = result["google_gemini"][0].split('\n')[0]  # Extract detected license plate
    if detected_plate:
        slot_no, slot_type, user_id = assign_parking(detected_plate)
        if slot_no:
            print(f"✅ Vehicle {detected_plate} assigned to Slot {slot_no} ({slot_type}).")
        else:
            print(f"❌ No slots available for {detected_plate}.")

# Initialize pipeline
from inference import InferencePipeline
pipeline = InferencePipeline.init_with_workflow(
    api_key="7RdO6RJ5gzrJPPIWh4Gm",
    workspace_name="darpan-neve-gigwd",
    workflow_id="custom-workflow-2",
    video_reference="./test.mp4",
    max_fps=10,
    on_prediction=custom_sink
)
pipeline.start()
pipeline.join()
