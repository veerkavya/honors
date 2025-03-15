from inference import InferencePipeline
import cv2
import sqlite3
import time
import re
import numpy as np
import string
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, 
                            QPushButton, QVBoxLayout, QComboBox, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
import sys

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
    conn.commit()
    conn.close()
    return slot_no, slot_type, user_id


class RegistrationWindow(QWidget):
    """
    PyQt5 window that shows the current frame and asks the user to register.
    The detected_plate is auto-filled. User is asked for Name and User Type.
    """
    def __init__(self, detected_plate, parent=None):
        super().__init__(parent)
        self.detected_plate = detected_plate
        self.result = {}
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Registration Required')
        self.setMinimumSize(300, 200)
        
        layout = QVBoxLayout()
        
        # License plate display
        plate_label = QLabel('Detected License Plate:')
        self.plate_display = QLineEdit(self.detected_plate)
        self.plate_display.setReadOnly(True)
        
        # Name input
        name_label = QLabel('Name:')
        self.name_input = QLineEdit()
        
        # User type selection
        type_label = QLabel('User Type:')
        self.type_combo = QComboBox()
        self.type_combo.addItems(['Faculty', 'Guest'])
        
        # Submit button
        self.submit_btn = QPushButton('Register')
        self.submit_btn.clicked.connect(self.submit)
        
        # Add all widgets to layout
        layout.addWidget(plate_label)
        layout.addWidget(self.plate_display)
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(type_label)
        layout.addWidget(self.type_combo)
        layout.addWidget(self.submit_btn)
        
        self.setLayout(layout)
        
    def submit(self):
        if not self.name_input.text():
            QMessageBox.warning(self, "Input Error", "Please enter your name")
            return
            
        self.result['name'] = self.name_input.text()
        self.result['user_type'] = self.type_combo.currentText()
        self.result['vehicle_no'] = self.detected_plate
        self.close()


def registration_window(detected_plate):
    """
    Creates a PyQt5 window that asks the user to register.
    Returns (name, user_type, vehicle_no) once registration is complete.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    reg_window = RegistrationWindow(detected_plate)
    reg_window.show()
    app.exec_()
    
    return reg_window.result.get('name'), reg_window.result.get('user_type'), reg_window.result.get('vehicle_no')


def register_user(name, user_type, vehicle_no):
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


def show_parking_notification(slot_no, slot_type):
    """Display a notification about parking availability using PyQt5"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    msg = QMessageBox()
    msg.setWindowTitle("Parking Information")
    
    if slot_no is None:
        msg.setText("No parking slots available")
        msg.setIcon(QMessageBox.Warning)
    else:
        msg.setText(f"You can park at slot {slot_no} ({slot_type} area)")
        msg.setIcon(QMessageBox.Information)
    
    msg.exec_()


def custom_sink(result, video_frame):
    # Handle VideoFrame object from inference library
    visualization = result["line_counter_visualization"]
    cv2.imshow("Video Feed", visualization.numpy_image)
    cv2.waitKey(1)
    
    if result.get("google_gemini"):
        print(result["google_gemini"])
        detected_plate = result["google_gemini"][0].split('\n')[0]  # place the detected number plate
        if detected_plate:
            conn = sqlite3.connect('parking.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Users WHERE vehicle_no = ?", (detected_plate,))
            user = cursor.fetchone()
            conn.close()
            
            if user is None:
                print("User not registered. Launching registration window.")
                name, reg_type, vehicle_no = registration_window(detected_plate)
                if name and reg_type and vehicle_no:
                    register_user(name, reg_type, vehicle_no)
            
            slot_no, slot_type, user_id = assign_parking(detected_plate)
            show_parking_notification(slot_no, slot_type)


# Initialize pipeline
def main():
    pipeline = InferencePipeline.init_with_workflow(
        api_key="7RdO6RJ5gzrJPPIWh4Gm",
        workspace_name="darpan-neve-gigwd",
        workflow_id="custom-workflow-2-2",
        video_reference="./test.mp4",
        max_fps=10,
        on_prediction=custom_sink
    )
    pipeline.start()
    pipeline.join()

if __name__ == "__main__":
    main()