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

def get_product_detail(product_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM products WHERE id = ? OR product_id = ?", (product_id, product_id))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"Product Detail Error: {e}")
        return None
    finally:
        conn.close()

def decrease_product_inventory(product_id, quantity):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT inventory FROM products WHERE id = ?", (product_id,))
        row = c.fetchone()
        if not row:
            return False, "상품을 찾을 수 없습니다."

        current = row['inventory'] if row['inventory'] else 0
        if current < quantity:
            return False, "재고가 부족합니다."

        c.execute("UPDATE products SET inventory = inventory - ? WHERE id = ?", (quantity, product_id))
        conn.commit()
        return True, "OK"
    except Exception as e:
        print(f"Inventory Error: {e}")
        return False, str(e)
    finally:
        conn.close()
