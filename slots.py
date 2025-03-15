import cv2
import numpy as np
import pickle
import pandas as pd
import requests
from ultralytics import YOLO
import cvzone
import sqlite3
from datetime import datetime

# API Endpoint for user ID management
USER_ID_API = "http://localhost:5001"

# Load slot data
with open("slot_data.pkl", "rb") as f:
    data = pickle.load(f)
    polylines, area_numbers = data['polylines'], data['area_numbers']

# Load COCO class names
with open("coco.txt", "r") as my_file:
    class_list = my_file.read().strip().split("\n")

# Load YOLO model
model = YOLO('yolov8s.pt')

cap = cv2.VideoCapture('easy1.mp4')
frame_count = 0
i = 0  # Debug counter

def fetch_user_ids():
    """Fetches the current user IDs from the Flask API."""
    try:
        response = requests.get(f"{USER_ID_API}/user_ids")
        return response.json() if response.status_code == 200 else {"incoming": None, "outgoing": None}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user IDs: {e}")
        return {"incoming": None, "outgoing": None}

def reset_user_id(user_type):
    """Resets the incoming or outgoing user ID to None."""
    payload = {user_type: None}
    try:
        response = requests.post(f"{USER_ID_API}/update_user_ids", json=payload)
        if response.status_code == 200:
            print(f"{user_type} user ID reset successfully")
    except requests.exceptions.RequestException as e:
        print(f"Error resetting {user_type} user ID: {e}")

def detect_vehicles(frame):
    """Runs YOLO on the frame and returns list of centers of detected vehicles."""
    results = model.predict(frame)
    detections = results[0].boxes.data
    df = pd.DataFrame(detections).astype("float")
    centers = []

    for _, row in df.iterrows():
        x1, y1, x2, y2, _, cls_id = map(int, row[:6])
        class_name = class_list[cls_id]

        # Filter for cars
        if 'car' in class_name.lower():
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            centers.append((cx, cy))

    return centers

while True:
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()
    ret, frame = cap.read()

    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    frame_count += 1
    if frame_count % 3 != 0:
        continue  # Skip frames for performance

    frame = cv2.resize(frame, (1020, 500))
    vehicle_centers = detect_vehicles(frame)
    occupied_slots = set()
    nonoccupied_slots = set()

    user_ids = fetch_user_ids()
    user_id_incoming = user_ids.get("incoming")
    user_id_outgoing = user_ids.get("outgoing")
    now = datetime.now()
    login_time = now.strftime("%H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")
    for idx, polyline in enumerate(polylines):
        cv2.polylines(frame, [polyline], isClosed=True, color=(0, 255, 0), thickness=2)
        cvzone.putTextRect(frame, f'{area_numbers[idx]}', tuple(polyline[0]), 1, 1)
        f=0
        for (cx, cy) in vehicle_centers:


            if cv2.pointPolygonTest(np.array(polyline), (cx, cy), False) > 0:
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)
                occupied_slots.add(idx)

                if user_id_incoming:
                    cursor.execute("SELECT status FROM SLOTS WHERE slot_id = ?", (idx+1,))
                    slot_status = cursor.fetchone()

                    if slot_status and slot_status[0].lower() == "empty":
                        # Fetch the last login_time for this slot
                        cursor.execute("SELECT logout_time FROM Occupied WHERE slot_id = ? ORDER BY login_time DESC LIMIT 1", (idx+1,))
                        last_login_time = cursor.fetchone()

                        if last_login_time and last_login_time[0]:
                            # Convert last login time to datetime object
                            last_login_dt = datetime.strptime(last_login_time[0], "%H:%M:%S")

                            # Get the current system time
                            current_time_dt = datetime.strptime(login_time, "%H:%M:%S")

                            # Calculate the time difference in seconds
                            time_difference = (current_time_dt - last_login_dt).total_seconds()
                        else:
                            time_difference = float('inf')  # If no previous record, allow the entry

                        # Proceed only if at least 1 minute (60 seconds) has passed
                        if time_difference >= 30:
                            cvzone.putTextRect(frame, f'timing: {time_difference}', (50, 180), 2, 2)

                            cursor.execute("INSERT INTO Occupied (login_time, logout_time, date, slot_id, user_id) VALUES (?, NULL, ?, ?, ?)",
                                        (login_time, date_str, idx+1, user_id_incoming))
                            cursor.execute("UPDATE Slots SET status = 'occupied', car_license_plate = ? WHERE slot_id = ?",
                                        ('MH' + str(i), idx+1))
                            conn.commit()

                            reset_user_id("incoming")  # Reset incoming user ID

                f=1
                cv2.polylines(frame, [polyline], isClosed=True, color=(0, 0, 255), thickness=2)
                break  # Stop checking once a veqhicle is found in this slot
        if f==0:
            nonoccupied_slots.add(idx+1)

            cvzone.putTextRect(frame, f'outgoing: {idx+1}', (100, 200), 2, 2)

            if user_id_outgoing:

                cursor.execute("SELECT status, car_license_plate FROM SLOTS WHERE slot_id = ?", (idx+1,))
                slot_status = cursor.fetchone()

                if slot_status and slot_status[0].lower() == "occupied":
                    cursor.execute("UPDATE Slots SET status = 'empty', car_license_plate = ? WHERE slot_id = ?",
                                    (slot_status[1], idx+1))
                    cursor.execute("UPDATE Occupied SET logout_time = ? WHERE logout_time IS NULL AND slot_id = ?",
                        (login_time, idx+1))

                    conn.commit()

                    reset_user_id("outgoing")  # Reset outgoing user ID

    total_slots = len(polylines)
    car_count = len(occupied_slots)
    free_slots = total_slots - car_count
    i += 1  # Increment counter

    cvzone.putTextRect(frame, f'Car Count: {i}{car_count} {occupied_slots}', (50, 60), 2, 2)
    cvzone.putTextRect(frame, f'Free Slots: {free_slots}{nonoccupied_slots}', (50, 120), 2, 2)

    cv2.imshow('FRAME', frame)
    key = cv2.waitKey(1000) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()