import sqlite3
import pandas as pd
from datetime import datetime
from .core import get_connection

def create_delivery_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            sender_name TEXT,
            sender_phone TEXT,
            sender_addr TEXT,
            receiver_name TEXT,
            receiver_phone TEXT,
            receiver_addr TEXT,
            item_name TEXT,
            weight REAL,
            fare INTEGER,
            status TEXT,
            tracking_number TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_delivery(data):
    conn = get_connection()
    try:
        import random
        c = conn.cursor()
        tn = f"TRK{datetime.now().strftime('%Y%m%d')}{random.randint(1000,9999)}"
        c.execute('''
            INSERT INTO deliveries (store_id, sender_name, sender_phone, sender_addr, 
                                    receiver_name, receiver_phone, receiver_addr, 
                                    item_name, weight, fare, status, tracking_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('store_id'),
            data.get('sender_name'),
            data.get('sender_phone'),
            data.get('sender_addr'),
            data.get('receiver_name'),
            data.get('receiver_phone'),
            data.get('receiver_addr'),
            data.get('item_name'),
            data.get('weight', 1),
            data.get('fare', 3000),
            '접수완료',
            tn,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True, tn
    except Exception as e:
        print(f"Delivery Save Error: {e}")
        return False, str(e)
    finally:
        conn.close()

def get_store_deliveries(store_id):
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM deliveries WHERE store_id = ? ORDER BY id DESC", conn, params=(store_id,))
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def save_courier(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        courier_id = data.get("courier_id")
        c.execute(
            """
            INSERT OR REPLACE INTO couriers (courier_id, name, phone, company, vehicle_type, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                courier_id,
                data.get("name"),
                data.get("phone"),
                data.get("company"),
                data.get("vehicle_type"),
                data.get("status", "active"),
                data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ),
        )
        conn.commit()
        return True
    except Exception as exc:
        print(f"Courier Save Error: {exc}")
        return False
    finally:
        conn.close()

def get_courier(courier_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM couriers WHERE courier_id = ?", (courier_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_couriers():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM couriers ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_rider(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        rider_id = data.get("rider_id")
        c.execute(
            """
            INSERT OR REPLACE INTO riders (rider_id, name, phone, area, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                rider_id,
                data.get("name"),
                data.get("phone"),
                data.get("area"),
                data.get("status", "active"),
                data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ),
        )
        conn.commit()
        return True
    except Exception as exc:
        print(f"Rider Save Error: {exc}")
        return False
    finally:
        conn.close()

def get_rider(rider_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM riders WHERE rider_id = ?", (rider_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_riders():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM riders ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
