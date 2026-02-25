import pandas as pd
from datetime import datetime
from .core import get_connection

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
