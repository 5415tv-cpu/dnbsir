import pandas as pd
from datetime import datetime
from .core import get_connection

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
