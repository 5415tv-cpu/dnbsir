import pandas as pd
from .core import get_connection

def save_user(user_data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR REPLACE INTO users (id, name, level, phone, joined_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_data.get('아이디'),
            user_data.get('상호명'),
            user_data.get('유저 등급'),
            user_data.get('연락처'),
            user_data.get('가입일시')
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

def get_all_users():
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM users", conn)
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def get_user(user_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None
    except Exception:
        return None
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Delete Error: {e}")
        return False
    finally:
        conn.close()
