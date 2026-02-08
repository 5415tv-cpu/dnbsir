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

    # ... (rest of init_db)


    # ... (rest of init_db)
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


def log_sms(store_id, phone, category, message, status, response=""):
    """
    SMS 발송 이력 저장
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO sms_logs (store_id, phone, category, message, status, response, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (store_id, phone, category, message, status, str(response), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print(f"Log Error: {e}")
    finally:
        conn.close()

def get_sms_logs(store_id=None, limit=50):
    conn = get_connection()
    try:
        if store_id:
            query = "SELECT * FROM sms_logs WHERE store_id = ? ORDER BY id DESC LIMIT ?"
            return pd.read_sql_query(query, conn, params=(store_id, limit))
        else:
            query = "SELECT * FROM sms_logs ORDER BY id DESC LIMIT ?"
            return pd.read_sql_query(query, conn, params=(limit,))
    except:
        return pd.DataFrame()
    finally:
        conn.close()

# Initialize on module load
init_db()

# ... (Existing code) ...

# ==========================================
# Order & Analytics
# ==========================================

def save_order(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Get Fee Rate
        store_id = data.get('store_id')
        amount = int(data.get('amount', 0))
        
        # Default rate 3.3% if not found
        c.execute("SELECT fee_rate FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        rate = row['fee_rate'] if row and row['fee_rate'] is not None else 0.033
        
        fee = int(amount * rate)
        net = amount - fee
        
        c.execute('''
            INSERT INTO orders (store_id, type, item_name, amount, fee_amount, net_amount, settlement_status, customer_phone, payment_method, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            store_id,
            data.get('type'),
            data.get('item_name'),
            amount,
            fee,
            net,
            'pending',
            data.get('customer_phone'),
            data.get('payment_method', 'CARD'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Order Save Error: {e}")
        return False
    finally:
        conn.close()

def get_orders(store_id, days=30):
    conn = get_connection()
    try:
        # Simple date diff could be done in SQL or Python. SQL is faster.
        # SQLite 'now', '-30 days' syntax
        query = f"SELECT * FROM orders WHERE store_id = ? AND created_at >= date('now', '-{days} days')"
        df = pd.read_sql(query, conn, params=(store_id,))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_all_orders_admin(days=30):
    conn = get_connection()
    try:
        query = f"SELECT * FROM orders WHERE created_at >= date('now', '-{days} days')"
        df = pd.read_sql(query, conn)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_customer_stats(store_id, phone):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            SELECT COUNT(*) as count, SUM(amount) as total 
            FROM orders 
            WHERE store_id = ? AND customer_phone = ?
        ''', (store_id, phone))
        row = c.fetchone()
        if row:
            return {"visit_count": row['count'], "total_spend": row['total'] or 0}
        return {"visit_count": 0, "total_spend": 0}
    except Exception:
        return {"visit_count": 0, "total_spend": 0}
    finally:
        conn.close()


# ... (Existing code) ...

# ==========================================
# Settings (KV Store)
# ==========================================

def save_setting(store_id, key, value):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR REPLACE INTO store_settings (store_id, key, value)
            VALUES (?, ?, ?)
        ''', (store_id, key, str(value)))
        conn.commit()
        return True
    except Exception as e:
        print(f"Setting Save Error: {e}")
        return False
    finally:
        conn.close()

def get_all_settings(store_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT key, value FROM store_settings WHERE store_id = ?", (store_id,))
        rows = c.fetchall()
        return {row['key']: row['value'] for row in rows}
    except Exception:
        return {}
    finally:
        conn.close()


# ... (Existing User Mgmt / Store Mgmt code preserved) ...

# ==========================================
# Product Management
# ==========================================

def save_product(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO products (store_id, name, price, description, image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data.get('store_id'),
            data.get('name'),
            data.get('price'),
            data.get('description'),
            data.get('image_path'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Product Save Error: {e}")
        return False
    finally:
        conn.close()

def get_products(store_id):
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM products WHERE store_id = ? AND is_active = 1", conn, params=(store_id,))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

# ==========================================
# Reservation Management
# ==========================================

def save_reservation(data):
    # ... (Keep existing implementation) ...
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO reservations (store_id, customer_name, contact, res_date, res_time, head_count, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('store_id'),
            data.get('customer_name'),
            data.get('contact'),
            data.get('res_date'),
            data.get('res_time'),
            data.get('head_count', 1),
            data.get('status', 'confirmed'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Reservation Save Error: {e}")
        return False
    finally:
        conn.close()

def update_reservation_status(reservation_id, status):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE reservations SET status = ? WHERE id = ?", (status, reservation_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Reservation Update Error: {e}")
        return False
    finally:
        conn.close()

def get_reservations(store_id):
    # ... (Keep existing) ...
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM reservations WHERE store_id = ? ORDER BY res_date, res_time", conn, params=(store_id,))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


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

def update_store_auto_reply(store_id, msg, missed, end, refill_on=0, refill_amount=50000):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE stores 
            SET auto_reply_msg = ?, 
                auto_reply_missed = ?, 
                auto_reply_end = ?,
                auto_refill_on = ?,
                auto_refill_amount = ?
            WHERE store_id = ?
        ''', (msg, missed, end, refill_on, refill_amount, store_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Auto Reply Update Error: {e}")
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

def get_user(user_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    except Exception:
        return None
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Error: {e}")
        return False
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


def get_all_stores():
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM stores ORDER BY created_at DESC", conn)
    except Exception:
        return pd.DataFrame()
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


def get_wallet_logs(store_id=None, limit=200):
    conn = get_connection()
    try:
        if store_id:
            return pd.read_sql(
                "SELECT * FROM wallet_logs WHERE store_id = ? ORDER BY id DESC LIMIT ?",
                conn,
                params=(store_id, limit),
            )
        return pd.read_sql(
            "SELECT * FROM wallet_logs ORDER BY id DESC LIMIT ?",
            conn,
            params=(limit,),
        )
    except Exception:
        return pd.DataFrame()
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

# ==========================================
# Table & Room Management (Using store_settings)
# ==========================================
def get_store_tables(store_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM store_settings WHERE store_id = ? AND key = 'tables'", (store_id,))
        row = c.fetchone()
        if row:
            return json.loads(row['value'])
        return []
    except Exception:
        return []
    finally:
        conn.close()

def save_store_tables(store_id, tables_data):
    # tables_data should be a list of dicts
    # We reuse the existing save_setting logic which handles connection
    import json
    json_str = json.dumps(tables_data, ensure_ascii=False)

# ==========================================
# Ledger (Bookkeeping) Management
# ==========================================
def create_ledger_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ledger_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount INTEGER,
            memo TEXT,
            proof_path TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Auto-run migration
create_ledger_table()

def save_ledger_record(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO ledger_records (store_id, date, type, category, amount, memo, proof_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('store_id'),
            data.get('date'),
            data.get('type'),
            data.get('category'),
            data.get('amount'),
            data.get('memo'),
            data.get('proof_path'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ledger Save Error: {e}")
        return False
    finally:
        conn.close()

def get_ledger_records(store_id, month_str=None):
    # month_str: '2024-05'
    conn = get_connection()
    try:
        query = "SELECT * FROM ledger_records WHERE store_id = ?"
        params = [store_id]
        
        if month_str:
            query += " AND date LIKE ?"
            params.append(f"{month_str}%")
            
        query += " ORDER BY date DESC, id DESC"
        
        return pd.read_sql(query, conn, params=params)
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def delete_ledger_record(record_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM ledger_records WHERE id = ?", (record_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ==========================================
# Parcel Delivery Management
# ==========================================
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

create_delivery_table()

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


# ==========================================
# 💰 Wallet / Virtual Number Utilities
# ==========================================

def get_wallet_balance(store_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT wallet_balance FROM stores WHERE store_id = ?", (store_id,))
    row = c.fetchone()
    conn.close()
    if row and row["wallet_balance"] is not None:
        return int(row["wallet_balance"])
    return 0


def update_wallet_balance(store_id, new_balance):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE stores SET wallet_balance = ? WHERE store_id = ?", (int(new_balance), store_id))
        conn.commit()
        return True
    except Exception as exc:
        print(f"Wallet Update Error: {exc}")
        return False
    finally:
        conn.close()


def get_store_id_by_virtual_number(virtual_number):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT store_id FROM virtual_numbers WHERE virtual_number = ?", (virtual_number,))
    row = c.fetchone()
    conn.close()
    return row["store_id"] if row else None


def save_virtual_number(virtual_number, store_id, label="", status="active"):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT OR REPLACE INTO virtual_numbers (virtual_number, store_id, label, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                virtual_number,
                store_id,
                label,
                status,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return True
    except Exception as exc:
        print(f"Virtual Number Save Error: {exc}")
        return False
    finally:
        conn.close()


def get_all_virtual_numbers():
    conn = get_connection()
    try:
        return pd.read_sql(
            "SELECT * FROM virtual_numbers ORDER BY created_at DESC",
            conn,
        )
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


# ==========================================
# 🚚 Courier / Rider (Normalized Entities)
# ==========================================

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


# ==========================================
# 🚚 Courier / Rider (Normalized Entities)
# ==========================================

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

def get_order_by_id(order_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = c.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_order_tracking(order_id, tracking_number):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Try adding column if not present
        try:
            c.execute("ALTER TABLE orders ADD COLUMN tracking_code TEXT")
        except: pass
        
        c.execute("UPDATE orders SET tracking_code = ? WHERE id = ?", (str(tracking_number), order_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Tracking Update Error: {e}")
        return False
    finally:
        conn.close()

def update_order_payment_method(order_id, method):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE orders SET payment_method = ? WHERE id = ?", (method, order_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Payment Method Update Error: {e}")
        return False
    finally:
        conn.close()


def save_product(store_id, name, price, image_path):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO products (store_id, name, price, image_path, created_at, inventory)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (store_id, name, price, image_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 100)) # Default 100
        conn.commit()
        return True
    except Exception as e:
        print(f"Product Save Error: {e}")
        return False
    finally:
        conn.close()

def get_all_products():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM products")
        rows = c.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Product Fetch Error: {e}")
        return []
    finally:
        conn.close()

def init_expenses_db():
    conn = get_connection()
    c = conn.cursor()
    # Expenses Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            card_name TEXT,
            category TEXT,
            amount INTEGER,
            date TEXT,
            approval_no TEXT,
            created_at TEXT
        )
    ''')
    
    # Idempotency: Add approval_no column if not exists
    try:
        c.execute("ALTER TABLE expenses ADD COLUMN approval_no TEXT")
    except: pass
    
    # Idempotency: Unique Index
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_expenses_approval ON expenses(approval_no)")

    # MFA Token Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS card_auth_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            card_name TEXT,
            token TEXT,
            expires_at TEXT,
            proxy_ip TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_expenses_db()

def save_expense(store_id, card_name, category, amount, date, approval_no=None):
    # Check Lock
    if is_date_locked(store_id, date):
        print(f"Expense Save Blocked: Date {date} is locked.")
        return False

    conn = get_connection()
    c = conn.cursor()
    try:
        # Generate approval_no if missing (for mock data)
        if not approval_no:
            import hashlib
            raw = f"{store_id}{card_name}{category}{amount}{date}"
            approval_no = hashlib.md5(raw.encode()).hexdigest()[:10]

        c.execute('''
            INSERT INTO expenses (store_id, card_name, category, amount, date, approval_no, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (store_id, card_name, category, amount, date, approval_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Skipping Duplicate Expense: {approval_no}")
        return True # Treat as success (Idempotency)
    except Exception as e:
        print(f"Expense Save Error: {e}")
        return False
    finally:
        conn.close()

# Ledger Lock Functions
def init_lock_table():
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            CREATE TABLE IF NOT EXISTS ledger_locks (
                store_id TEXT,
                locked_until TEXT,
                created_at TEXT,
                PRIMARY KEY (store_id)
            )
        ''') 
        conn.commit()
    except Exception as e:
        print(f"Lock Table Init Error: {e}")
    finally:
        conn.close()

def get_ledger_lock_date(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        init_lock_table() # Ensure table exists
        c.execute("SELECT locked_until FROM ledger_locks WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        if row:
            return row[0]
        return None
    except Exception:
        return None
    finally:
        conn.close()

def lock_ledger(store_id, date):
    # Lock data up to this date (Inclusive)
    conn = get_connection()
    c = conn.cursor()
    try:
        init_lock_table()
        # Only update if new date is later than existing lock
        current_lock = get_ledger_lock_date(store_id)
        if current_lock and current_lock >= date:
            return True # Already locked
            
        c.execute("INSERT OR REPLACE INTO ledger_locks (store_id, locked_until, created_at) VALUES (?, ?, ?)", 
                  (store_id, date, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except Exception as e:
        print(f"Lock Error: {e}")
        return False
    finally:
        conn.close()

def is_date_locked(store_id, date):
    # date format: YYYY-MM-DD
    if not date: return False
    locked_until = get_ledger_lock_date(store_id)
    if not locked_until:
        return False
    return date <= locked_until

def save_order(store_id, product_id, product_name, price, quantity, buyer_name, buyer_phone, buyer_address):
    # Check Lock
    today = datetime.now().strftime("%Y-%m-%d")
    if is_date_locked(store_id, today):
        print(f"Order Save Blocked: Date {today} is locked.")
        return False
        
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO orders (store_id, product_id, product_name, price, quantity, buyer_name, buyer_phone, buyer_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (store_id, product_id, product_name, price, quantity, buyer_name, buyer_phone, buyer_address, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except Exception as e:
        print(f"Order Save Error: {e}")
        return False
    finally:
        conn.close()

def get_tax_stats(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        # 1. Total Revenue
        c.execute("SELECT SUM(price * quantity) as total_revenue FROM orders WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        total_revenue = row['total_revenue'] if row and row['total_revenue'] else 0
        
        # 2. Expense Rate (33.47% as per user request example)
        expense_rate = 0.3347
        recognized_expenses = int(total_revenue * expense_rate)
        
        # 3. Tax Base
        # Basic Deduction: 1,500,000
        basic_deduction = 1500000
        tax_base = total_revenue - recognized_expenses - basic_deduction
        if tax_base < 0: tax_base = 0
        
        # 4. Tax (6%)
        predicted_tax = int(tax_base * 0.06)
        
        return {
            "total_revenue": total_revenue,
            "recognized_expenses": recognized_expenses,
            "predicted_tax": predicted_tax
        }
    finally:
        conn.close()

def get_product_detail(product_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()

def save_expense(store_id, card_name, category, amount, date, approval_no=None):
    conn = get_connection()
    c = conn.cursor()
    try:
        # Generate approval_no if missing (for mock data)
        if not approval_no:
            import hashlib
            raw = f"{store_id}{card_name}{category}{amount}{date}"
            approval_no = hashlib.md5(raw.encode()).hexdigest()[:10]

        c.execute('''
            INSERT INTO expenses (store_id, card_name, category, amount, date, approval_no, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (store_id, card_name, category, amount, date, approval_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        print(f"Skipping Duplicate Expense: {approval_no}")
        return True # Treat as success (Idempotency)
    except Exception as e:
        print(f"Expense Save Error: {e}")
        return False
    finally:
        conn.close()

def get_monthly_expenses(store_id, month=None):
    # month format: "YYYY-MM"
    if not month:
        month = datetime.now().strftime("%Y-%m")
        
    conn = get_connection()
    try:
        query = "SELECT * FROM expenses WHERE store_id = ? AND date LIKE ?"
        df = pd.read_sql(query, conn, params=(store_id, f"{month}%"))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_integrated_ledger(store_id):
    conn = get_connection()
    try:
        # 1. Get Expenses (Purchase)
        expenses_query = """
            SELECT 
                date, 
                '매입' as type, 
                category, 
                card_name as client, 
                amount as total,
                '법인카드' as note
            FROM expenses 
            WHERE store_id = ?
        """
        
        # 2. Get Sales (Orders)
        orders_query = """
            SELECT 
                substr(created_at, 1, 10) as date, 
                '매출' as type, 
                '배송매출' as category, 
                buyer_name as client, 
                (price * quantity) as total,
                '카드결제' as note
            FROM orders 
            WHERE store_id = ?
        """
        
        df_expenses = pd.read_sql(expenses_query, conn, params=(store_id,))
        df_orders = pd.read_sql(orders_query, conn, params=(store_id,))
        
        # Merge
        df_all = pd.concat([df_expenses, df_orders], ignore_index=True)
        
        if df_all.empty:
            return []
            
        # Sort by Date
        df_all['date'] = pd.to_datetime(df_all['date'])
        df_all = df_all.sort_values(by='date')
        
        # Process Columns (Supply Value, VAT)
        results = []
        for idx, row in df_all.iterrows():
            total = int(row['total'])
            supply_value = int(total / 1.1)
            vat = total - supply_value
            
            results.append({
                "date": row['date'].strftime("%m-%d"),
                "type": row['type'],
                "category": row['category'],
                "client": row['client'],
                "supply_value": supply_value,
                "vat": vat,
                "total": total,
                "note": row['note']
            })
            
        return results

    except Exception as e:
        print(f"Ledger Error: {e}")
        return []
    finally:
        conn.close()

def get_today_stats(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("SELECT SUM(price * quantity) as revenue FROM orders WHERE store_id = ? AND created_at LIKE ?", (store_id, f"{today}%"))
        row = c.fetchone()
        revenue = row['revenue'] if row and row['revenue'] else 0
        
        margin = int(revenue * 0.1) # 10% Margin
        
        return {
            "revenue": revenue,
            "margin": margin
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        return {"revenue": 0, "margin": 0}
    finally:
        conn.close()
