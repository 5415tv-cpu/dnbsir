import pandas as pd
from datetime import datetime
from .core import get_connection

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
    except Exception as e:
        print(f"Log Wallet Error: {e}")
        return False
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
    except Exception as e:
        print(f"Topup Error: {e}")
        return False
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
    except Exception:
        return []
    finally:
        conn.close()

def get_wallet_balance(store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT wallet_balance FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        if row and row["wallet_balance"] is not None:
            return int(row["wallet_balance"])
        return 0
    except Exception:
        return 0
    finally:
        conn.close()

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

def charge_wallet(store_id, amount, bonus, memo):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT wallet_balance FROM stores WHERE store_id = ?", (store_id,))
        row = c.fetchone()
        current = row['wallet_balance'] if row and row['wallet_balance'] else 0

        new_balance = current + amount + bonus

        c.execute("UPDATE stores SET wallet_balance = ? WHERE store_id = ?", (new_balance, store_id))
        c.execute('''
            INSERT INTO wallet_logs (store_id, change_type, amount, balance_after, memo, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (store_id, 'charge', amount + bonus, new_balance, memo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        return new_balance
    except Exception as e:
        print(f"Charge Wallet Error: {e}")
        return None
    finally:
        conn.close()
