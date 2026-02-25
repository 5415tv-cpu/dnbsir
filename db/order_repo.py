import pandas as pd
from datetime import datetime
from .core import get_connection

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
