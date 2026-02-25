import os
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text


_engine = None


def _get_dsn() -> str:
    return os.environ.get("CLOUD_SQL_DSN") or os.environ.get("DATABASE_URL", "")


def get_engine():
    global _engine
    if _engine is None:
        dsn = _get_dsn()
        if not dsn:
            raise RuntimeError("CLOUD_SQL_DSN or DATABASE_URL is required for Cloud SQL.")
        _engine = create_engine(dsn, pool_pre_ping=True)
    return _engine


def _execute(sql: str, params: dict | None = None):
    engine = get_engine()
    with engine.begin() as conn:
        return conn.execute(text(sql), params or {})


def init_db():
    # Users
    _execute(
        """
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
        """
    )

    # Stores
    _execute(
        """
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
            daily_token_limit INTEGER DEFAULT 10000,
            tier TEXT DEFAULT 'basic',
            current_usage INTEGER DEFAULT 0,
            last_usage_date TEXT,
            membership TEXT,
            fee_rate REAL DEFAULT 0.033,
            wallet_balance INTEGER DEFAULT 0,
            kakao_biz_key TEXT,
            use_custom_kakao INTEGER DEFAULT 0,
            smart_callback_on INTEGER DEFAULT 0,
            smart_callback_text TEXT,
            created_at TEXT
        )
        """
    )

    # Orders
    _execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id BIGSERIAL PRIMARY KEY,
            store_id TEXT,
            type TEXT,
            item_name TEXT,
            amount INTEGER,
            fee_amount INTEGER DEFAULT 0,
            net_amount INTEGER DEFAULT 0,
            settlement_status TEXT DEFAULT 'pending',
            customer_phone TEXT,
            courier_id TEXT,
            rider_id TEXT,
            created_at TEXT
        )
        """
    )
    
    # Customers (CRM)
    _execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
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
        """
    )

    # Wallet Logs
    _execute(
        """
        CREATE TABLE IF NOT EXISTS wallet_logs (
            id BIGSERIAL PRIMARY KEY,
            store_id TEXT,
            change_type TEXT,
            amount INTEGER,
            balance_after INTEGER,
            memo TEXT,
            created_at TEXT
        )
        """
    )

    # Wallet Topups
    _execute(
        """
        CREATE TABLE IF NOT EXISTS wallet_topups (
            id BIGSERIAL PRIMARY KEY,
            store_id TEXT,
            amount INTEGER,
            depositor TEXT,
            status TEXT,
            processed_at TEXT,
            requested_at TEXT
        )
        """
    )

    # SMS Logs
    _execute(
        """
        CREATE TABLE IF NOT EXISTS sms_logs (
            id BIGSERIAL PRIMARY KEY,
            store_id TEXT,
            phone TEXT,
            category TEXT,
            message TEXT,
            status TEXT,
            response TEXT,
            created_at TEXT
        )
        """
    )

    # Virtual Number Mapping
    _execute(
        """
        CREATE TABLE IF NOT EXISTS virtual_numbers (
            virtual_number TEXT PRIMARY KEY,
            store_id TEXT,
            label TEXT,
            status TEXT,
            created_at TEXT
        )
        """
    )

    # Couriers / Riders
    _execute(
        """
        CREATE TABLE IF NOT EXISTS couriers (
            courier_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            company TEXT,
            vehicle_type TEXT,
            status TEXT,
            created_at TEXT
        )
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS riders (
            rider_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            area TEXT,
            status TEXT,
            created_at TEXT
        )
        """
    )

    # Billing Logs
    _execute(
        """
        CREATE TABLE IF NOT EXISTS ai_usage_logs (
            id BIGSERIAL PRIMARY KEY,
            store_id TEXT,
            tokens_input INTEGER,
            tokens_output INTEGER,
            cost INTEGER,
            timestamp TEXT
        )
        """
    )
    
    # Caching
    _execute(
        """
        CREATE TABLE IF NOT EXISTS cached_responses (
            id BIGSERIAL PRIMARY KEY,
            store_id TEXT,
            question TEXT,
            answer TEXT,
            hits INTEGER DEFAULT 0,
            last_used TEXT,
            created_at TEXT
        )
        """
    )
    
    # Point Logs
    _execute(
        """
        CREATE TABLE IF NOT EXISTS point_logs (
            id BIGSERIAL PRIMARY KEY,
            store_id TEXT,
            type TEXT, -- CHARGE, USAGE, REFUND
            amount INTEGER,
            balance_snapshot INTEGER,
            order_id TEXT,
            status TEXT, -- DONE, CANCELED
            created_at TEXT
        )
        """
    )


# init_db()  # <-- REMOVED: Do not run at import time to prevent crash on Cloud Run



def save_user(user_data):
    user_data = user_data or {}
    _execute(
        """
        INSERT INTO users (id, password, name, phone, level, joined_at, total_payment, fee_amount, settle_date, settle_status, net_amount, plan_status)
        VALUES (:id, :password, :name, :phone, :level, :joined_at, :total_payment, :fee_amount, :settle_date, :settle_status, :net_amount, :plan_status)
        ON CONFLICT (id) DO UPDATE SET
            password = EXCLUDED.password,
            name = EXCLUDED.name,
            phone = EXCLUDED.phone,
            level = EXCLUDED.level,
            joined_at = EXCLUDED.joined_at,
            total_payment = EXCLUDED.total_payment,
            fee_amount = EXCLUDED.fee_amount,
            settle_date = EXCLUDED.settle_date,
            settle_status = EXCLUDED.settle_status,
            net_amount = EXCLUDED.net_amount,
            plan_status = EXCLUDED.plan_status
        """,
        {
            "id": user_data.get("id"),
            "password": user_data.get("password"),
            "name": user_data.get("name"),
            "phone": user_data.get("phone"),
            "level": user_data.get("level"),
            "joined_at": user_data.get("joined_at"),
            "total_payment": user_data.get("total_payment", 0),
            "fee_amount": user_data.get("fee_amount", 0),
            "settle_date": user_data.get("settle_date"),
            "settle_status": user_data.get("settle_status"),
            "net_amount": user_data.get("net_amount", 0),
            "plan_status": user_data.get("plan_status"),
        },
    )
    return True


def get_all_users():
    result = _execute("SELECT * FROM users ORDER BY joined_at DESC NULLS LAST")
    return pd.DataFrame(result.mappings().all())


def delete_user(user_id):
    _execute("DELETE FROM users WHERE id = :id", {"id": user_id})
    return True


def save_store(store_data):
    store_data = store_data or {}
    store_id = store_data.get("store_id") or store_data.get("phone")
    _execute(
        """
        INSERT INTO stores (
            store_id, password, name, owner_name, phone, category,
            info, menu_text, printer_ip, table_count, seats_per_table,
            points, membership, created_at
        ) VALUES (
            :store_id, :password, :name, :owner_name, :phone, :category,
            :info, :menu_text, :printer_ip, :table_count, :seats_per_table,
            :points, :membership, :created_at
        )
        ON CONFLICT (store_id) DO UPDATE SET
            password = EXCLUDED.password,
            name = EXCLUDED.name,
            owner_name = EXCLUDED.owner_name,
            phone = EXCLUDED.phone,
            category = EXCLUDED.category,
            info = EXCLUDED.info,
            menu_text = EXCLUDED.menu_text,
            printer_ip = EXCLUDED.printer_ip,
            table_count = EXCLUDED.table_count,
            seats_per_table = EXCLUDED.seats_per_table,
            points = EXCLUDED.points,
            membership = EXCLUDED.membership
        """,
        {
            "store_id": store_id,
            "password": store_data.get("password"),
            "name": store_data.get("name"),
            "owner_name": store_data.get("owner_name"),
            "phone": store_data.get("phone"),
            "category": store_data.get("category"),
            "info": store_data.get("info"),
            "menu_text": store_data.get("menu_text"),
            "printer_ip": store_data.get("printer_ip"),
            "table_count": store_data.get("table_count", 0),
            "seats_per_table": store_data.get("seats_per_table", 0),
            "points": store_data.get("points", 0),
            "membership": store_data.get("membership"),
            "created_at": store_data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True


def get_store(store_id):
    result = _execute("SELECT * FROM stores WHERE store_id = :id", {"id": store_id})
    row = result.mappings().first()
    return dict(row) if row else None


def get_all_stores():
    result = _execute("SELECT * FROM stores ORDER BY created_at DESC NULLS LAST")
    return pd.DataFrame(result.mappings().all())


def get_wallet_balance(store_id):
    result = _execute("SELECT wallet_balance FROM stores WHERE store_id = :id", {"id": store_id})
    row = result.mappings().first()
    if row and row.get("wallet_balance") is not None:
        return int(row["wallet_balance"])
    return 0


def update_wallet_balance(store_id, new_balance):
    _execute("UPDATE stores SET wallet_balance = :bal WHERE store_id = :id", {"bal": int(new_balance), "id": store_id})
    return True


def log_wallet(store_id, change_type, amount, balance_after, memo):
    _execute(
        """
        INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
        VALUES (:store_id, :change_type, :amount, :balance_after, :memo, :created_at)
        """,
        {
            "store_id": store_id,
            "change_type": change_type,
            "amount": amount,
            "balance_after": balance_after,
            "memo": memo,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True


def request_topup(store_id, amount, depositor):
    _execute(
        """
        INSERT INTO wallet_topups (store_id, amount, depositor, status, requested_at)
        VALUES (:store_id, :amount, :depositor, :status, :requested_at)
        """,
        {
            "store_id": store_id,
            "amount": amount,
            "depositor": depositor,
            "status": "pending",
            "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True


def get_pending_topups():
    result = _execute("SELECT * FROM wallet_topups WHERE status = 'pending' ORDER BY requested_at DESC")
    return [dict(row) for row in result.mappings().all()]

def get_wallet_topups(store_id):
    """
    Get all topup requests for a store (for Excel export)
    """
    result = _execute(
        "SELECT * FROM wallet_topups WHERE store_id = :id ORDER BY requested_at DESC",
        {"id": store_id}
    )
    return pd.DataFrame(result.mappings().all())


def get_wallet_logs(store_id=None, limit=200):
    if store_id:
        result = _execute(
            "SELECT * FROM wallet_logs WHERE store_id = :id ORDER BY id DESC LIMIT :lim",
            {"id": store_id, "lim": limit},
        )
    else:
        result = _execute("SELECT * FROM wallet_logs ORDER BY id DESC LIMIT :lim", {"lim": limit})
    return pd.DataFrame(result.mappings().all())


def save_virtual_number(virtual_number, store_id, label="", status="active"):
    _execute(
        """
        INSERT INTO virtual_numbers (virtual_number, store_id, label, status, created_at)
        VALUES (:virtual_number, :store_id, :label, :status, :created_at)
        ON CONFLICT (virtual_number) DO UPDATE SET
            store_id = EXCLUDED.store_id,
            label = EXCLUDED.label,
            status = EXCLUDED.status
        """,
        {
            "virtual_number": virtual_number,
            "store_id": store_id,
            "label": label,
            "status": status,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True


def get_store_id_by_virtual_number(virtual_number):
    result = _execute(
        "SELECT store_id FROM virtual_numbers WHERE virtual_number = :num",
        {"num": virtual_number},
    )
    row = result.mappings().first()
    return row["store_id"] if row else None


def get_all_virtual_numbers():
    result = _execute("SELECT * FROM virtual_numbers ORDER BY created_at DESC")
    return pd.DataFrame(result.mappings().all())


def log_sms(store_id, phone, category, message, status, response=""):
    _execute(
        """
        INSERT INTO sms_logs (store_id, phone, category, message, status, response, created_at)
        VALUES (:store_id, :phone, :category, :message, :status, :response, :created_at)
        """,
        {
            "store_id": store_id,
            "phone": phone,
            "category": category,
            "message": message,
            "status": status,
            "response": str(response),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True


def get_sms_logs(store_id=None, limit=50):
    if store_id:
        result = _execute(
            "SELECT * FROM sms_logs WHERE store_id = :id ORDER BY id DESC LIMIT :lim",
            {"id": store_id, "lim": limit},
        )
    else:
        result = _execute("SELECT * FROM sms_logs ORDER BY id DESC LIMIT :lim", {"lim": limit})
    return pd.DataFrame(result.mappings().all())


def save_order(data):
    data = data or {}
    _execute(
        """
        INSERT INTO orders (store_id, type, item_name, amount, fee_amount, net_amount, settlement_status, customer_phone, courier_id, rider_id, created_at)
        VALUES (:store_id, :type, :item_name, :amount, :fee_amount, :net_amount, :settlement_status, :customer_phone, :courier_id, :rider_id, :created_at)
        """,
        {
            "store_id": data.get("store_id"),
            "type": data.get("type"),
            "item_name": data.get("item_name"),
            "amount": data.get("amount", 0),
            "fee_amount": data.get("fee_amount", 0),
            "net_amount": data.get("net_amount", 0),
            "settlement_status": data.get("settlement_status", "pending"),
            "customer_phone": data.get("customer_phone"),
            "courier_id": data.get("courier_id"),
            "rider_id": data.get("rider_id"),
            "created_at": data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True


def get_orders(store_id, days=30):
    result = _execute(
        "SELECT * FROM orders WHERE store_id = :id ORDER BY created_at DESC",
        {"id": store_id},
    )
    return pd.DataFrame(result.mappings().all())


def get_all_orders_admin(days=30):
    result = _execute("SELECT * FROM orders ORDER BY created_at DESC")
    return pd.DataFrame(result.mappings().all())


def save_courier(data):
    data = data or {}
    _execute(
        """
        INSERT INTO couriers (courier_id, name, phone, company, vehicle_type, status, created_at)
        VALUES (:courier_id, :name, :phone, :company, :vehicle_type, :status, :created_at)
        ON CONFLICT (courier_id) DO UPDATE SET
            name = EXCLUDED.name,
            phone = EXCLUDED.phone,
            company = EXCLUDED.company,
            vehicle_type = EXCLUDED.vehicle_type,
            status = EXCLUDED.status
        """,
        {
            "courier_id": data.get("courier_id"),
            "name": data.get("name"),
            "phone": data.get("phone"),
            "company": data.get("company"),
            "vehicle_type": data.get("vehicle_type"),
            "status": data.get("status", "active"),
            "created_at": data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True


def get_courier(courier_id):
    result = _execute("SELECT * FROM couriers WHERE courier_id = :id", {"id": courier_id})
    row = result.mappings().first()
    return dict(row) if row else None


def get_all_couriers():
    result = _execute("SELECT * FROM couriers ORDER BY created_at DESC")
    return [dict(row) for row in result.mappings().all()]


def save_rider(data):
    data = data or {}
    _execute(
        """
        INSERT INTO riders (rider_id, name, phone, area, status, created_at)
        VALUES (:rider_id, :name, :phone, :area, :status, :created_at)
        ON CONFLICT (rider_id) DO UPDATE SET
            name = EXCLUDED.name,
            phone = EXCLUDED.phone,
            area = EXCLUDED.area,
            status = EXCLUDED.status
        """,
        {
            "rider_id": data.get("rider_id"),
            "name": data.get("name"),
            "phone": data.get("phone"),
            "area": data.get("area"),
            "status": data.get("status", "active"),
            "created_at": data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True


def get_rider(rider_id):
    result = _execute("SELECT * FROM riders WHERE rider_id = :id", {"id": rider_id})
    row = result.mappings().first()
    return dict(row) if row else None


def get_all_riders():
    result = _execute("SELECT * FROM riders ORDER BY created_at DESC")
    return [dict(row) for row in result.mappings().all()]
# 🚀 AI Cost Control (Billing)
# ==========================================

def check_ai_limit(store_id):
    """
    Check if the store can use AI services (Daily Limit & Points).
    Returns: (is_allowed, message)
    """
    # 1. Get Store Status
    result = _execute("SELECT daily_token_limit, current_usage, last_usage_date, points FROM stores WHERE store_id = :id", {"id": store_id})
    row = result.mappings().first()
    
    if not row:
        return False, "Store not found"
        
    limit = row['daily_token_limit'] or 10000
    usage = row['current_usage'] or 0
    last_date = row['last_usage_date']
    points = row['points'] or 0
    
    # 2. Daily Reset Check
    today = datetime.now().strftime("%Y-%m-%d")
    if last_date != today:
        # Reset usage for new day
        _execute("UPDATE stores SET current_usage = 0, last_usage_date = :today WHERE store_id = :id", 
                 {"today": today, "id": store_id})
        usage = 0
        
    # 3. Check Limit
    if usage >= limit:
        return False, f"Daily limit exceeded ({usage}/{limit})"
        
    # 4. Check Points (Pay-as-you-go)
    if points < 10:
            return False, "Insufficient points"
            
    return True, "OK"

def log_ai_usage(store_id, input_tokens, output_tokens):
    """
    Log AI usage and deduct points.
    """
    try:
        total_tokens = input_tokens + output_tokens
        cost = 10 + (total_tokens // 100)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Log Usage
        _execute("""
            INSERT INTO ai_usage_logs (store_id, tokens_input, tokens_output, cost, timestamp)
            VALUES (:store_id, :tokens_input, :tokens_output, :cost, :timestamp)
        """, {
            "store_id": store_id, 
            "tokens_input": input_tokens, 
            "tokens_output": output_tokens, 
            "cost": cost, 
            "timestamp": timestamp
        })
        
        # 2. Update Store (Deduct Points, Increment Usage)
        _execute("""
            UPDATE stores 
            SET points = points - :cost, 
                current_usage = current_usage + :total_tokens
            WHERE store_id = :store_id
        """, {"cost": cost, "total_tokens": total_tokens, "store_id": store_id})
        
        return True, cost
    except Exception as e:
        print(f"Logging Error: {e}")
        return False, 0

# ==========================================
# 🚀 AI Caching (Zero-Cost)
# ==========================================

def get_cached_response(store_id, user_message):
    """
    Check if a similar question exists in cache.
    """
    try:
        result = _execute("""
            SELECT answer, hits FROM cached_responses 
            WHERE store_id = :store_id AND question = :question
        """, {"store_id": store_id, "question": user_message})
        
        row = result.mappings().first()
        if row:
            # Update hits
            _execute("""
                UPDATE cached_responses 
                SET hits = hits + 1, last_used = :now 
                WHERE store_id = :store_id AND question = :question
            """, {
                "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "store_id": store_id, 
                "question": user_message
            })
            return row['answer']
            
        return None
    except Exception as e:
        print(f"Cache Get Error: {e}")
        return None

def save_cached_response(store_id, question, answer):
    """
    Save a Q&A pair to cache.
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # PostgreSQL specific UPSERT syntax might differ slightly (ON CONFLICT), assuming id is serial.
        # But here we don't have a unique constraint on (store_id, question) in the CREATE TABLE above?
        # Actually I added an Index but not a UNIQUE constraint.
        # Let's use INSERT for now, or assume migration adds unique constraint if we want UPSERT.
        # Simple INSERT for MVP.
        _execute("""
            INSERT INTO cached_responses (store_id, question, answer, hits, last_used, created_at)
            VALUES (:store_id, :question, :answer, 0, :timestamp, :timestamp)
        """, {
            "store_id": store_id, 
            "question": question, 
            "answer": answer,
            "timestamp": timestamp
        })
        return True
    except Exception as e:
        print(f"Cache Save Error: {e}")
        return False

# ==========================================
# Super Admin Stats
# ==========================================

def get_system_stats():
    """
    Get aggregated system statistics for Super Admin Dashboard.
    """
    stats = {
        "total_stores": 0,
        "active_stores": 0,
        "total_users": 0,
        "total_revenue": 0,
        "total_ai_tokens": 0,
        "recent_errors": []
    }
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Stores
            res_stores = conn.execute(text("SELECT COUNT(*), SUM(CASE WHEN points > 0 THEN 1 ELSE 0 END) FROM stores"))
            row_stores = res_stores.first()
            if row_stores:
                stats["total_stores"] = row_stores[0] or 0
                stats["active_stores"] = row_stores[1] or 0

            # Users
            res_users = conn.execute(text("SELECT COUNT(*) FROM users"))
            stats["total_users"] = res_users.scalar() or 0

            # Revenue (Sum of approved topups)
            try:
                # check if wallet_topups exists
                res_revenue = conn.execute(text("SELECT SUM(amount) FROM wallet_topups WHERE status='approved'"))
                stats["total_revenue"] = res_revenue.scalar() or 0
            except:
                stats["total_revenue"] = 0

            # AI Usage
            try:
                res_ai = conn.execute(text("SELECT SUM(tokens_input + tokens_output) FROM ai_usage_logs"))
                stats["total_ai_tokens"] = res_ai.scalar() or 0
            except:
                stats["total_ai_tokens"] = 0

            # Recent Errors
            try:
                # Using mappings() to get dict-like access
                res_logs = conn.execute(text("SELECT store_id, status, message, created_at FROM sms_logs WHERE status != '성공' ORDER BY created_at DESC LIMIT 5"))
                # row._mapping is available in SQLAlchemy 1.4+
                stats["recent_errors"] = [dict(row._mapping) for row in res_logs]
            except Exception as e:
                # print(f"Error fetching logs: {e}")
                stats["recent_errors"] = []

    except Exception as e:
        print(f"[!] Error getting system stats: {e}")
    
    return stats


# ==========================================
# 💰 Wallet & Usage Analytics
# ==========================================

def get_wallet_details(store_id):
    """
    Get wallet balance and recent logs for a store.
    """
    details = {
        "current_points": 0,
        "wallet_logs": [],
        "ai_usage_today": {"tokens": 0, "cost": 0},
        "sms_usage_today": {"count": 0, "cost": 0} # SMS cost estimation needed
    }
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # 1. Current Points
            res = conn.execute(text("SELECT points FROM stores WHERE store_id = :id"), {"id": store_id})
            points = res.scalar()
            details["current_points"] = points if points is not None else 0
            
            # 2. Recent Wallet Logs
            # Standardized to wallet_logs
            res_logs = conn.execute(text("""
                SELECT change_type as type, amount, created_at, memo 
                FROM wallet_logs 
                WHERE store_id = :id 
                ORDER BY id DESC LIMIT 20
            """), {"id": store_id})
            details["wallet_logs"] = [dict(row) for row in res_logs.mappings().all()]

    except Exception as e:
        print(f"[!] Error getting wallet details: {e}")
        
    # Get Usage Stats via separate function
    usage = get_daily_usage_stats(store_id)
    details["ai_usage_today"] = usage.get("ai")
    details["sms_usage_today"] = usage.get("sms")
    return details


def confirm_payment(store_id, amount, order_id, payment_key):
    """
    Atomic: Charge points and log transaction.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            with conn.begin(): # Start Transaction
                # 1. Update Points
                conn.execute(text("""
                    UPDATE stores 
                    SET points = COALESCE(points, 0) + :amount 
                    WHERE store_id = :id
                """), {"amount": amount, "id": store_id})
                
                # 2. Get New Balance for Snapshot
                res = conn.execute(text("SELECT points FROM stores WHERE store_id = :id"), {"id": store_id})
                new_balance = res.scalar()
                
                # 3. Insert Log
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Using wallet_logs
                conn.execute(text("""
                    INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
                    VALUES (:store_id, 'CHARGE', :amount, :balance, '포인트 충전', :now)
                """), {
                    "store_id": store_id,
                    "amount": amount,
                    "balance": new_balance,
                    "now": now
                })
        return True
    except Exception as e:
        print(f"[!] Payment Confirmation DB Error: {e}")
        return False
        
    return details

def get_daily_usage_stats(store_id):
    """
    Get daily usage statistics (AI & SMS) for today.
    """
    stats = {
        "ai": {"tokens": 0, "cost": 0},
        "sms": {"count": 0, "cost": 0}
    }
    try:
        engine = get_engine()
        today_start = datetime.now().strftime("%Y-%m-%d 00:00:00")
        
        with engine.connect() as conn:
            # AI Usage Today
            res_ai = conn.execute(text("""
                SELECT SUM(tokens_input + tokens_output), SUM(cost) 
                FROM ai_usage_logs 
                WHERE store_id = :id AND timestamp >= :today
            """), {"id": store_id, "today": today_start})
            row_ai = res_ai.first()
            if row_ai:
                stats["ai"]["tokens"] = row_ai[0] or 0
                stats["ai"]["cost"] = row_ai[1] or 0
                
            # SMS Usage Today
            # Assuming estimated cost: LMS=50, SMS=20. Let's avg 30 for now or count count * 30
            res_sms = conn.execute(text("""
                SELECT COUNT(*) 
                FROM sms_logs 
                WHERE store_id = :id AND created_at >= :today
            """), {"id": store_id, "today": today_start})
            count = res_sms.scalar() or 0
            stats["sms"]["count"] = count
            stats["sms"]["cost"] = count * 30 # Estimated cost per SMS
            
    except Exception as e:
        print(f"[!] Error getting daily usage: {e}")
        
    return stats


# ==========================================
# 🎯 CRM & Target Marketing
# ==========================================

def get_customer(customer_id, store_id):
    result = _execute(
        "SELECT * FROM customers WHERE customer_id = :cid AND store_id = :sid", 
        {"cid": customer_id, "sid": store_id}
    )
    row = result.mappings().first()
    return dict(row) if row else None

def get_customer_by_phone(phone):
    # This might be ambiguous if multiple stores have same customer, usually needs store_id
    # For now, return first match or handle appropriately
    result = _execute("SELECT * FROM customers WHERE phone = :phone LIMIT 1", {"phone": phone})
    row = result.mappings().first()
    return dict(row) if row else None

def save_customer(data):
    data = data or {}
    _execute(
        """
        INSERT INTO customers (customer_id, store_id, name, phone, address, preferences, notes, total_orders, last_visit, created_at)
        VALUES (:customer_id, :store_id, :name, :phone, :address, :preferences, :notes, :total_orders, :last_visit, :created_at)
        ON CONFLICT (customer_id, store_id) DO UPDATE SET
            name = COALESCE(EXCLUDED.name, customers.name),
            phone = COALESCE(EXCLUDED.phone, customers.phone),
            address = COALESCE(EXCLUDED.address, customers.address),
            preferences = COALESCE(EXCLUDED.preferences, customers.preferences),
            notes = COALESCE(EXCLUDED.notes, customers.notes),
            last_visit = COALESCE(EXCLUDED.last_visit, customers.last_visit)
        """,
        {
            "customer_id": data.get("customer_id"),
            "store_id": data.get("store_id"),
            "name": data.get("name"),
            "phone": data.get("phone"),
            "address": data.get("address"),
            "preferences": data.get("preferences"),
            "notes": data.get("notes"),
            "total_orders": data.get("total_orders", 0),
            "last_visit": data.get("last_visit") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    return True

def update_customer_field(customer_id, field, value, store_id):
    # Safe field validation could be added
    allowed_fields = ['name', 'phone', 'address', 'preferences', 'notes']
    if field not in allowed_fields:
        return False
        
    sql = f"UPDATE customers SET {field} = :value WHERE customer_id = :cid AND store_id = :sid"
    _execute(sql, {"value": value, "cid": customer_id, "sid": store_id})
    return True

def increment_customer_order(customer_id, store_id):
    _execute(
        """
        UPDATE customers 
        SET total_orders = total_orders + 1, last_visit = :now 
        WHERE customer_id = :cid AND store_id = :sid
        """,
        {"now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "cid": customer_id, "sid": store_id}
    )
    return True

def get_crm_customers(store_id, filter_type="all"):
    """
    Get customers list based on filter for Target Marketing.
    """
    sql = "SELECT * FROM customers WHERE store_id = :sid"
    params = {"sid": store_id}
    
    if filter_type == "recent":
        # Visit within last 30 days
        # Postgres date math: last_visit >= NOW() - INTERVAL '30 DAYS'
        # Assuming last_visit is stored as string 'YYYY-MM-DD HH:MM:SS'
        sql += " AND last_visit >= :date_limit"
        # Simple string comparison works for ISO dates
        from datetime import timedelta
        date_limit = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        params["date_limit"] = date_limit
        
    elif filter_type == "regular":
        # 3 or more orders
        sql += " AND total_orders >= 3"
        
    elif filter_type == "vip":
        # 10 or more orders
        sql += " AND total_orders >= 10"
        
    sql += " ORDER BY last_visit DESC LIMIT 100"
    
    result = _execute(sql, params)
    return [dict(row) for row in result.mappings().all()]

def deduct_points_for_sms(store_id, total_cost, customer_count):
    """
    Atomic Point Deduction for Batch SMS.
    Returns: (success, message, transaction_id)
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            with conn.begin(): # Transaction
                # 1. Check Balance
                res = conn.execute(text("SELECT points FROM stores WHERE store_id = :id FOR UPDATE"), {"id": store_id})
                current_points = res.scalar() or 0
                
                if current_points < total_cost:
                    return False, "잔액이 부족합니다.", None
                
                # 2. Deduct
                conn.execute(text("""
                    UPDATE stores 
                    SET points = points - :cost 
                    WHERE store_id = :id
                """), {"cost": total_cost, "id": store_id})
                
                # 3. Log
                new_balance = current_points - total_cost
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                memo = f"단체 문자 발송 ({customer_count}명)"
                
                conn.execute(text("""
                    INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
                    VALUES (:store_id, 'USE', :amount, :balance, :memo, :now)
                """), {
                    "store_id": store_id,
                    "amount": -total_cost,
                    "balance": new_balance,
                    "memo": memo,
                    "now": now
                })
                
        return True, "성공", "TX_" + datetime.now().strftime("%Y%m%d%H%M%S")
        
    except Exception as e:
        print(f"[!] Point Deduction Error: {e}")
        return False, f"시스템 오류: {e}", None

def refund_points(store_id, amount, reason):
    """
    Refund points (e.g., for failed SMS).
    """
    try:
        if amount <= 0: return True
        
        engine = get_engine()
        with engine.connect() as conn:
            with conn.begin():
                # 1. Refund
                conn.execute(text("""
                    UPDATE stores 
                    SET points = points + :amount 
                    WHERE store_id = :id
                """), {"amount": amount, "id": store_id})
                
                # 2. Log
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Manual subquery for balance_after because we rely on transactional consistency or just fetch it
                # Cloud SQL supports subqueries in VALUES but let's just do it cleanly or use the subquery syntax I used before but correct table
                conn.execute(text("""
                    INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
                    VALUES (:store_id, 'REFUND', :amount, (SELECT points FROM stores WHERE store_id = :store_id), :memo, :now)
                """), {
                    "store_id": store_id,
                    "amount": amount,
                    "memo": reason,
                    "now": now
                })
        return True
    except Exception as e:
        print(f"[!] Refund Error: {e}")
        return False

def deduct_fixed_cost(store_id, amount, reason):
    """
    Deduct fixed amount of points (Atomic).
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            with conn.begin():
                # 1. Check Balance
                res = conn.execute(text("SELECT points FROM stores WHERE store_id = :id FOR UPDATE"), {"id": store_id})
                current = res.scalar() or 0
                
                if current < amount:
                    return False
                
                # 2. Deduct
                conn.execute(text("UPDATE stores SET points = points - :amount WHERE store_id = :id"), 
                             {"amount": amount, "id": store_id})
                
                # 3. Log
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(text("""
                    INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
                    VALUES (:store_id, 'USE', :amount, (SELECT points FROM stores WHERE store_id = :store_id), :memo, :now)
                """), {
                    "store_id": store_id,
                    "amount": -amount,
                    "memo": reason,
                    "now": now
                })
        return True
    except Exception as e:
        print(f"[!] Deduct Error: {e}")
        return False

def create_db_backup():
    """
    Create a full system backup (JSON Dump of all tables).
    Returns path to backup file.
    """
    try:
        import pandas as pd
        import json
        import os
        from datetime import datetime

        engine = get_engine()
        # List of tables to backup
        tables = ["users", "stores", "couriers", "riders", "wallet_logs", "sms_logs", "ai_usage_logs", "customers"]
        
        backup_data = {}
        
        with engine.connect() as conn:
            # Get list of all tables from DB to be safe, or use hardcoded list
            # For MVP, hardcoded list is safer to avoid permission issues on schema queries
            for table in tables:
                try:
                    df = pd.read_sql(f"SELECT * FROM {table}", conn)
                    # Convert dates to string for JSON serialization
                    # simplistic approach: use records orientation
                    backup_data[table] = df.to_dict(orient="records")
                except Exception as e:
                    print(f"[Backup] Skipping table {table}: {e}")
                    
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_full_{timestamp}.json"
        
        # [Cloud Run Fix] Use /tmp for writable filesystem
        # Check if we are in Cloud Run (K_SERVICE env var exists) or just default to /tmp on Linux
        # For simplicity and safety in container, prioritize /tmp
        if os.environ.get("K_SERVICE") or os.name != 'nt':
             backup_dir = "/tmp"
        else:
             backup_dir = os.path.join(os.getcwd(), "backups")
             
        os.makedirs(backup_dir, exist_ok=True)
        
        filepath = os.path.join(backup_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=4, default=str)
            
        return filepath
    except Exception as e:
        print(f"[!] Backup Error: {e}")
        return None

def check_db_integrity():
    """
    Check Database Integrity & Connection.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Simple check: Select 1
            conn.execute(text("SELECT 1"))
            return "OK (Connected)"
    except Exception as e:
        return f"Error: {str(e)}"

def save_user(store_id, password, name, phone):
    """
    Save user to 'users' table (Legacy/Admin Management)
    """
    try:
        # PostgreSQL UPSERT
        sql = """
            INSERT INTO users (id, password, name, phone, joined_at)
            VALUES (:id, :password, :name, :phone, :joined_at)
            ON CONFLICT (id) DO UPDATE 
            SET password = :password, name = :name, phone = :phone
        """
        _execute(sql, {
            "id": store_id, 
            "password": password, 
            "name": name, 
            "phone": phone, 
            "joined_at": datetime.now().isoformat()
        })
        return True
    except Exception as e:
        print(f"[!] CloudSQL save_user Error: {e}")
        return False

def get_all_users():
    """
    Get all users (for Admin Dashboard)
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM users"))
            users = [dict(row._mapping) for row in result]
            return users
    except Exception as e:
        print(f"[!] CloudSQL get_all_users Error: {e}")
        return []

def update_store_role(store_id, role):
    """
    Update store role (RBAC) - Cloud SQL
    """
    try:
        # Attempt update
        sql = "UPDATE stores SET user_role = :role WHERE store_id = :id"
        result = _execute(sql, {"role": role, "id": store_id})
        
        # If no rows updated, check if column exists or store exists
        if result.rowcount == 0:
            # Check if store exists
            existing = _execute("SELECT store_id FROM stores WHERE store_id = :id", {"id": store_id}).first()
            if existing:
                # Store exists, so column might be missing. Attempt ADD COLUMN.
                try:
                    _execute("ALTER TABLE stores ADD COLUMN user_role TEXT")
                    _execute(sql, {"role": role, "id": store_id})
                    return True
                except Exception as e:
                    print(f"[!] Alter Table Failed (Column likely exists): {e}")
                    return False
            else:
                return False # Store doesn't exist

        return True
    except Exception as e:
        # Fallback for "column does not exist" error if not caught above
        if "column" in str(e).lower():
            try:
                _execute("ALTER TABLE stores ADD COLUMN user_role TEXT")
                _execute("UPDATE stores SET user_role = :role WHERE store_id = :id", {"role": role, "id": store_id})
                return True
            except Exception as e2:
                print(f"[!] CloudSQL update_store_role Migration Failed: {e2}")
        print(f"[!] CloudSQL update_store_role Error: {e}")
        return False


def reset_store_onboarding(store_id):
    """
    Reset onboarding flags for testing/debugging.
    """
    _execute(
        """
        UPDATE stores 
        SET is_signed = FALSE, 
            category = NULL, 
            user_role = NULL 
        WHERE store_id = :id
        """,
        {"id": store_id}
    )
    return True

def update_store_role(store_id, role):
    _execute(
        "UPDATE stores SET user_role = :role WHERE store_id = :id",
        {"role": role, "id": store_id}
    )
    return True

def ensure_schema():
    """
    Check and add missing columns for Cloud SQL (Migration).
    """
    print("[Schema] Checking columns...")
    # 1. user_role
    try:
        _execute("ALTER TABLE stores ADD COLUMN user_role TEXT")
        print("[Schema] Added user_role column.")
    except Exception as e:
        # Ignore if column exists
        pass

    # 2. is_signed
    try:
        _execute("ALTER TABLE stores ADD COLUMN is_signed BOOLEAN DEFAULT FALSE")
        print("[Schema] Added is_signed column.")
    except Exception as e:
        pass
        
    return True

