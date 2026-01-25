import sqlite3
import os
from datetime import datetime
import json
import pandas as pd

DB_FILE = "database.db"

def get_connection():
    """Create a thread-safe connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database tables."""
    conn = get_connection()
    c = conn.cursor()

    # 1. Users / User Management
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            phone TEXT,
            level TEXT,
            joined_at TEXT,
            total_payment INTEGER DEFAULT 0,
            fee_amount INTEGER DEFAULT 0,
            settle_date TEXT,
            settle_status TEXT,
            net_amount INTEGER DEFAULT 0,
            plan_status TEXT
        )
    ''')
    
    # 2. Stores
    c.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            store_id TEXT PRIMARY KEY,
            password TEXT,
            name TEXT,
            owner_name TEXT,
            phone TEXT,
            category TEXT,
            info TEXT,
            menu_text TEXT,
            printer_ip TEXT,
            table_count INTEGER DEFAULT 0,
            seats_per_table INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            membership TEXT,
            created_at TEXT
        )
    ''')

    # 3. Business Records (General, Delivery, Farmer)
    # Using a single flexible table or separate ones. Separate is cleaner for this legacy code.
    c.execute('''
        CREATE TABLE IF NOT EXISTS records_general (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            date_time TEXT,
            customer_name TEXT,
            contact TEXT,
            menu_info TEXT,
            head_count INTEGER,
            reservation_time TEXT,
            is_ai_served INTEGER,
            amount INTEGER,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS records_delivery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            date_time TEXT,
            sender_name TEXT,
            receiver_name TEXT,
            receiver_addr TEXT,
            item_type TEXT,
            tracking_code TEXT,
            fee INTEGER,
            status TEXT,
            created_at TEXT
        )
    ''')

    # 4. Wallet & Logs
    c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            change_type TEXT,
            amount INTEGER,
            balance_after INTEGER,
            memo TEXT,
            created_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS wallet_topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            amount INTEGER,
            depositor TEXT,
            status TEXT,
            processed_at TEXT,
            requested_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS message_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            receiver TEXT,
            cost INTEGER,
            status TEXT,
            channel TEXT,
            created_at TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Initialize on module load
init_db()

# ==========================================
# User Management
# ==========================================

def save_user(user_data):
    conn = get_connection()
    c = conn.cursor()
    try:
        # user_data expects keys: '아이디', '상호명', etc. mapping to DB columns
        c.execute('''
            INSERT OR REPLACE INTO users (id, name, level, phone, joined_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_data.get('아이디'),
            user_data.get('상호명'),
            user_data.get('유저 등급'),
            user_data.get('연락처'),
            user_data.get('가입일시')
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

def get_all_users():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM users", conn)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

# ==========================================
# Store Management
# ==========================================

def get_store(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def save_store(store_data):
    conn = get_connection()
    c = conn.cursor()
    try:
        # store_id is key
        store_id = store_data.get('store_id') or store_data.get('phone') # Fallback
        
        c.execute('''
            INSERT OR REPLACE INTO stores (
                store_id, password, name, owner_name, phone, category, 
                info, menu_text, printer_ip, table_count, seats_per_table, 
                points, membership
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            store_id,
            store_data.get('password'),
            store_data.get('name'),
            store_data.get('owner_name'),
            store_data.get('phone'),
            store_data.get('category'),
            store_data.get('info'),
            store_data.get('menu_text'),
            store_data.get('printer_ip'),
            store_data.get('table_count', 0),
            store_data.get('seats_per_table', 0),
            store_data.get('points', 0),
            store_data.get('membership')
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Store Save Error: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# Wallet Logic
# ==========================================

def log_wallet(store_id, change_type, amount, balance_after, memo):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (store_id, change_type, amount, balance_after, memo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def request_topup(store_id, amount, depositor):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO wallet_topups (store_id, amount, depositor, status, requested_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (store_id, amount, depositor, "pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    finally:
        conn.close()

def get_pending_topups():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM wallet_topups WHERE status = 'pending'")
        rows = c.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

# ==========================================
# Business Records
# ==========================================

def save_business_record(user_type, data):
    conn = get_connection()
    c = conn.cursor()
    try:
        if user_type == "일반사업자":
            c.execute('''
                INSERT INTO records_general (date_time, customer_name, contact, menu_info, head_count, amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('일시'), data.get('고객명'), data.get('연락처'), 
                data.get('메뉴/인원'), data.get('인원'), data.get('결제금액'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        elif user_type == "택배사업자":
             c.execute('''
                INSERT INTO records_delivery (date_time, sender_name, receiver_name, receiver_addr, item_type, fee, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('접수일시'), data.get('발송인명'), data.get('수령인명'),
                data.get('수령인 주소(AI추출)'), data.get('물품종류'), data.get('수수료'),
                data.get('상태', '접수완료'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        conn.commit()
        return True, "저장 성공"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

