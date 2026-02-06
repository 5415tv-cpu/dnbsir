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


init_db()


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
