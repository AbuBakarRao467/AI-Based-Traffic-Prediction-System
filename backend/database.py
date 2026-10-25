"""
database.py
SQLite database setup aur helper functions. Ye JSON file storage aur
hardcoded checkpoint list ki jagah leta hai — proper relational database
ke sath: Users, Checkpoints, Route Search History, Detection Logs.
"""

import sqlite3
import os
import hashlib
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "traffic_system.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Saari tables banata hai (agar na hon), aur default admin seed karta hai."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            traffic_image TEXT NOT NULL,
            damage_image TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS route_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_place TEXT,
            end_place TEXT,
            start_lat REAL,
            start_lon REAL,
            end_lat REAL,
            end_lon REAL,
            mode TEXT,
            distance_km REAL,
            duration_min REAL,
            searched_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS detection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detection_type TEXT NOT NULL,
            result_summary TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?)",
            ("admin", hashlib.sha256("admin123".encode()).hexdigest(), "Admin User", "admin", datetime.now().isoformat())
        )
        conn.commit()

    conn.close()


def seed_checkpoints_if_empty(checkpoints_list):
    """Purani hardcoded checkpoint list ko database mein ek dafa daal deta hai."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM checkpoints")
    if cur.fetchone()[0] == 0:
        for cp in checkpoints_list:
            cur.execute(
                "INSERT INTO checkpoints (id, name, lat, lon, traffic_image, damage_image) VALUES (?, ?, ?, ?, ?, ?)",
                (cp["id"], cp["name"], cp["lat"], cp["lon"], cp["traffic_image"], cp["damage_image"])
            )
        conn.commit()
    conn.close()


# ---------- Users ----------

def get_user(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username, password_hash, name, role="admin"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (username, password_hash, name, role, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, name, role FROM users")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------- Checkpoints ----------

def get_all_checkpoints():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM checkpoints")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------- Logging ----------

def log_route_search(start_place, end_place, start_coords, end_coords, mode, best_route):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO route_searches
        (start_place, end_place, start_lat, start_lon, end_lat, end_lon, mode, distance_km, duration_min, searched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        start_place, end_place, start_coords[0], start_coords[1], end_coords[0], end_coords[1],
        mode, best_route.get("distance_km"), best_route.get("duration_min"), datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def log_detection(detection_type, result_summary: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO detection_logs (detection_type, result_summary, created_at) VALUES (?, ?, ?)",
        (detection_type, json.dumps(result_summary), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()