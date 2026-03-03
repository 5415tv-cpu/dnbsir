import pandas as pd
from .core import get_connection

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
        store_id = store_data.get('store_id') or store_data.get('phone')
        
        c.execute('''
            INSERT OR REPLACE INTO stores (
                store_id, password, name, owner_name, phone, category, 
                info, menu_text, printer_ip, table_count, seats_per_table, 
                points, membership
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            store_id, store_data.get('password'), store_data.get('name'), 
            store_data.get('owner_name'), store_data.get('phone'), 
            store_data.get('category'), store_data.get('info'), 
            store_data.get('menu_text'), store_data.get('printer_ip'), 
            store_data.get('table_count', 0), store_data.get('seats_per_table', 0), 
            store_data.get('points', 0), store_data.get('membership')
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Store Save Error: {e}")
        return False
    finally:
        conn.close()

def update_store_agreement(store_id, owner_name, marketing_agreed):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE stores
            SET is_signed = 1, owner_name = ?
            WHERE store_id = ?
        ''', (owner_name, store_id))
        conn.commit()
    except Exception as e:
        print(f"Agreement Update Error: {e}")
        return False
    finally:
        conn.close()
    
    # Also save marketing_agreed as a store setting
    save_setting(store_id, "marketing_agreed", "True" if marketing_agreed else "False")
    return True

def get_all_stores():
    conn = get_connection()
    try:
        return pd.read_sql("SELECT * FROM stores ORDER BY created_at DESC", conn)
    except Exception:
        return pd.DataFrame()
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

def get_store_tables(store_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM store_settings WHERE store_id = ? AND key = 'tables_data'", (store_id,))
        row = c.fetchone()
        if row and row['value']:
            import json
            return json.loads(row['value'])
        return []
    except Exception:
        return []
    finally:
        conn.close()

def save_store_tables(store_id, tables_data):
    import json
    return save_setting(store_id, 'tables_data', json.dumps(tables_data))
