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

# We will move init_db() here once all queries are consolidated

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

    # 2-1. Couriers (Parcel Drivers)
    c.execute('''
        CREATE TABLE IF NOT EXISTS couriers (
            courier_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            company TEXT,
            vehicle_type TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')

    # 2-2. Riders (Delivery Part-time)
    c.execute('''
        CREATE TABLE IF NOT EXISTS riders (
            rider_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            area TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')
    
    # 2-3. Courier Requests (Citizen -> Logistics)
    c.execute('''
        CREATE TABLE IF NOT EXISTS courier_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            citizen_id TEXT,
            sender_name TEXT,
            sender_phone TEXT,
            sender_addr TEXT,
            receiver_name TEXT,
            receiver_phone TEXT,
            receiver_addr TEXT,
            item_type TEXT,
            weight TEXT,
            status TEXT DEFAULT 'pending',
            payment_method TEXT,
            tracking_code TEXT,
            created_at TEXT,
            FOREIGN KEY(citizen_id) REFERENCES stores(store_id)
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


    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            name TEXT,
            price INTEGER,
            description TEXT,
            image_path TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            customer_name TEXT,
            contact TEXT,
            res_date TEXT,
            res_time TEXT,
            head_count INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')


    c.execute('''
        CREATE TABLE IF NOT EXISTS store_settings (
            store_id TEXT,
            key TEXT,
            value TEXT,
            PRIMARY KEY (store_id, key)
        )
    ''')
    

    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            type TEXT, -- MENU, RESERVE, PARCEL
            item_name TEXT,
            amount INTEGER,
            fee_amount INTEGER DEFAULT 0,
            net_amount INTEGER DEFAULT 0,
            settlement_status TEXT DEFAULT 'pending',
            customer_phone TEXT,
            created_at TEXT
        )
    ''') 
    
    # 5. Schema Migration (Safe Add)
    try:
        c.execute("ALTER TABLE stores ADD COLUMN fee_rate REAL DEFAULT 0.033")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN wallet_balance INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN fee_amount INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN net_amount INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN settlement_status TEXT DEFAULT 'pending'")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN courier_id TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN rider_id TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'CARD'")
    except: pass
    
    # Kakao Biz Customization
    try:
        c.execute("ALTER TABLE stores ADD COLUMN kakao_biz_key TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN use_custom_kakao INTEGER DEFAULT 0")
    except: pass

    # Smart Callback
    try:
        c.execute("ALTER TABLE stores ADD COLUMN smart_callback_on INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN smart_callback_text TEXT")
    except: pass
    
    # Auto Reply Settings
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_reply_msg TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_reply_missed INTEGER DEFAULT 1")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_reply_end INTEGER DEFAULT 0")
    except: pass
    
    # Auto Refill Settings
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_refill_on INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE stores ADD COLUMN auto_refill_amount INTEGER DEFAULT 50000")
    except: pass

    # Product Inventory
    try:
        c.execute("ALTER TABLE products ADD COLUMN inventory INTEGER DEFAULT 100")
    except: pass

    # Customers (CRM / Memory)
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT,
            store_id TEXT,
            name TEXT,
            phone TEXT,
            address TEXT,
            preferences TEXT,
            notes TEXT,
            total_orders INTEGER DEFAULT 0,
            last_visit TEXT,
            created_at TEXT,
            UNIQUE(customer_id, store_id)
        )
    ''')

    # Virtual Number Mapping (050)
    c.execute('''
        CREATE TABLE IF NOT EXISTS virtual_numbers (
            virtual_number TEXT PRIMARY KEY,
            store_id TEXT,
            label TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')
    
    # SMS Logs
    c.execute('''CREATE TABLE IF NOT EXISTS sms_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  store_id TEXT,
                  phone TEXT,
                  category TEXT,
                  message TEXT,
                  status TEXT,
                  response TEXT,
                  created_at TEXT)''')

    conn.commit()
    conn.close()
