
from inference import InferencePipeline
import cv2
import urllib3
import torch
import sqlite3
import time
import re
import numpy as np
import string
from datetime import datetime
from ultralytics import YOLO
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

def assign_parking(vehicle_no):
    """
    Looks up the user by vehicle_no (license plate) and assigns a free slot (status 'empty')
    based on the user's type. For Faculty, it tries a faculty slot first; for Guest, only guest slots.
    The slot is marked as 'waiting' and a record is inserted into Occupied.

    Returns:
        (slot_no, slot_type, user_id) if a slot is available; otherwise (None, None, None).
    """
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, type_id FROM Users WHERE vehicle_no = ?", (vehicle_no,))
    user = cursor.fetchone()
    if user is None:
        conn.close()
        print("User not found for vehicle:", vehicle_no)
        return None, None, None
    user_id, type_id = user
    desired_type = 'faculty' if type_id == 1 else 'guest'

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
        # notification that place is not available
        return None, None, None
    #else:
        #notification that here u can park

    slot_id, slot_no, slot_type = slot
    cursor.execute("UPDATE Slots SET status = 'waiting', car_license_plate = ? WHERE slot_id = ?",
                   (vehicle_no, slot_id))
    now = datetime.now()
    login_time = now.strftime("%H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")
    #   NEEDS TO PASS THIS LOGIN TIME, SLOT_ID, USER_ID TO SLOT.PY AND THEN DO THE FOLLOWING OCCUPIED DB COMMAND.(have to think how to pass)
    # cursor.execute("INSERT INTO Occupied (login_time, logout_time, date, slot_id, user_id) VALUES (?, NULL, ?, ?, ?)",
    #                (login_time, date_str, slot_id, user_id))
    # conn.commit()
    # conn.close()
    return slot_no, slot_type, user_id


def registration_window(detected_plate):# NEEDS TO KEEP SOME THER PORTAL FOR THIS
    """
    Creates a Tkinter window that shows the current frame and asks the user to register.
    The detected_plate is auto-filled. User is asked for Name and User Type.
    Returns (name, user_type, vehicle_no) once registration is complete.
    """
    from PIL import Image, ImageTk
    # frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # pil_image = Image.fromarray(frame_rgb)

    reg_data = {}
    def submit():
        reg_data['name'] = name_var.get()
        reg_data['user_type'] = type_var.get()
        reg_data['vehicle_no'] = detected_plate
        root.destroy()

    root = tk.Tk()
    root.title("Registration Required")

    #imgtk = ImageTk.PhotoImage(image=pil_image)
    #img_label = tk.Label(root, image=imgtk)
    #img_label.pack()

    tk.Label(root, text="Detected License Plate:").pack()
    plate_entry = tk.Entry(root, width=20)
    plate_entry.insert(0, detected_plate)
    plate_entry.config(state="readonly")
    plate_entry.pack()

    tk.Label(root, text="Name:").pack()
    name_var = tk.StringVar()
    name_entry = tk.Entry(root, textvariable=name_var, width=20)
    name_entry.pack()

    tk.Label(root, text="User Type:").pack()
    type_var = tk.StringVar()
    type_dropdown = ttk.Combobox(root, textvariable=type_var, values=["Faculty", "Guest"], state="readonly", width=17)
    type_dropdown.current(0)
    type_dropdown.pack()

    submit_button = tk.Button(root, text="Register", command=submit)
    submit_button.pack()

    root.mainloop()
    return reg_data.get('name'), reg_data.get('user_type'), reg_data.get('vehicle_no')

def register_user(name, user_type, vehicle_no):# NEEDS TO KEEP SOME THER PORTAL FOR THIS
    """
    Inserts a new user into the Users table.
    """
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()
    type_id = 1 if user_type.lower() == "faculty" else 2
    cursor.execute("INSERT OR IGNORE INTO Users (name, vehicle_no, type_id) VALUES (?, ?, ?)",
                   (name, vehicle_no, type_id))
    conn.commit()
    conn.close()
    print(f"User registered: {name}, {vehicle_no}, {user_type}")



def custom_sink(result, video_frame):
    # Handle VideoFrame object from inference library
    visualization=result["line_counter_visualization"]
    if result.get("google_gemini"):
        print(result["google_gemini"])
    cv2.imshow("Video Feed", visualization.numpy_image)
    cv2.waitKey(1)
    detected_plate = result["google_gemini"][0].split('\n')[0] #place the detected number plate
    if detected_plate:
        conn = sqlite3.connect('parking.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE vehicle_no = ?", (detected_plate,))
        user = cursor.fetchone()
        conn.close()


        if user is None:
            print("User not registered. Launching registration window.")
            # cv2.imshow("Registration - Verify Placement", annotated_frame)
            # cv2.waitKey(500)
            name, reg_type, vehicle_no = registration_window(detected_plate)
            if name and reg_type and vehicle_no:
                register_user(name, reg_type, vehicle_no)#REGISTER KARNA HE HOGA
                #AFTER REGISTERING GET ITS USER_ID
        slot_no, slot_type, user_id = assign_parking(detected_plate)
        #NOTIFICATION TO THE USER THAT THIS SLOT IS EMPTY



# Initialize pipeline
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
