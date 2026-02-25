from .core import get_connection
from datetime import datetime

def get_customer(customer_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM customers WHERE customer_id = ? AND store_id = ?", (customer_id, store_id))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Customer Get Error: {e}")
        return None
    finally:
        conn.close()

def get_customer_by_phone(phone):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM customers WHERE phone = ?", (phone,))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Customer Search Error: {e}")
        return None
    finally:
        conn.close()

def save_customer(customer_data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR REPLACE INTO customers (
                customer_id, store_id, name, phone, address, 
                preferences, notes, total_orders, last_visit, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT total_orders FROM customers WHERE customer_id=? AND store_id=?), 0), ?, ?)
        ''', (
            customer_data.get('customer_id'),
            customer_data.get('store_id'),
            customer_data.get('name'),
            customer_data.get('phone'),
            customer_data.get('address'),
            customer_data.get('preferences'),
            customer_data.get('notes'),
            customer_data.get('customer_id'),
            customer_data.get('store_id'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Customer Save Error: {e}")
        return False
    finally:
        conn.close()

def update_customer_field(customer_id, field, value, store_id):
    allowed_fields = ['name', 'phone', 'address', 'preferences', 'notes', 'last_visit']
    if field not in allowed_fields: return False
    
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(f"UPDATE customers SET {field} = ? WHERE customer_id = ? AND store_id = ?", (value, customer_id, store_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Customer Update Error: {e}")
        return False
    finally:
        conn.close()

def increment_customer_order(customer_id, store_id):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE customers 
            SET total_orders = total_orders + 1,
                last_visit = ?
            WHERE customer_id = ? AND store_id = ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), customer_id, store_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Customer Order Increment Error: {e}")
        return False
    finally:
        conn.close()
