
import os

new_code = """

# ==========================================
# Dashboard Data Fetchers (Appended)
# ==========================================

def get_orders(store_id, days=30):
    conn = get_connection()
    try:
        import datetime
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        query = "SELECT * FROM orders WHERE store_id = ? AND created_at >= ? ORDER BY created_at DESC"
        import pandas as pd
        df = pd.read_sql(query, conn, params=(store_id, start_date))
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Fetch Orders Error: {e}")
        return []
    finally:
        conn.close()

def get_products(store_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE store_id = ?", (store_id,))
        columns = [description[0] for description in c.description]
        rows = c.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Fetch Products Error: {e}")
        return []
    finally:
        conn.close()
"""

with open("db_sqlite.py", "a", encoding="utf-8") as f:
    f.write(new_code)

print("Successfully appended functions to db_sqlite.py")
