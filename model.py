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

def setup_database():
    """
    Creates and initializes the SQLite database with the following tables:

    UserType:
      - type_id (PK)
      - type_name (Faculty/Guest)

    Users:
      - user_id (PK)
      - name
      - vehicle_no (unique license plate)
      - type_id (FK to UserType)

    Slots:
      - slot_id (PK)
      - slot_no
      - slot_type (faculty/guest)
      - status ("empty", "waiting", "occupied")
      - car_license_plate (to store assigned vehicle number)

    Occupied (ParkingHistory):
      - record_id (PK)
      - login_time
      - logout_time
      - date
      - slot_id (FK to Slots)
      - user_id (FK to Users)
    """
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()

    # Create UserType table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserType (
            type_id INTEGER PRIMARY KEY,
            type_name TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM UserType")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO UserType (type_id, type_name) VALUES (1, 'Faculty')")
        cursor.execute("INSERT INTO UserType (type_id, type_name) VALUES (2, 'Guest')")
        conn.commit()

    # Create Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            vehicle_no TEXT UNIQUE,
            type_id INTEGER,
            FOREIGN KEY(type_id) REFERENCES UserType(type_id)
        )
    """)

    # Create Slots table with car_license_plate column added
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Slots (
            slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_no INTEGER,
            slot_type TEXT,
            status TEXT DEFAULT 'empty',
            car_license_plate TEXT
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM Slots")
    if cursor.fetchone()[0] == 0:
        slot_no = 1
        # Assume 4 faculty slots and 6 guest slots
        for _ in range(4):
            cursor.execute("INSERT INTO Slots (slot_no, slot_type, status) VALUES (?, 'faculty', 'empty')", (slot_no,))
            slot_no += 1
        for _ in range(6):
            cursor.execute("INSERT INTO Slots (slot_no, slot_type, status) VALUES (?, 'guest', 'empty')", (slot_no,))
            slot_no += 1
        conn.commit()

    # Create Occupied (ParkingHistory) table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Occupied (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            login_time TEXT,
            logout_time TEXT,
            date TEXT,
            slot_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY(slot_id) REFERENCES Slots(slot_id),
            FOREIGN KEY(user_id) REFERENCES Users(user_id)
        )
    """)
    conn.commit()
    conn.close()

def main():
    setup_database()

if __name__ == "__main__":
    main()