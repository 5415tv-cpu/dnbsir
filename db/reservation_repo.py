import pandas as pd
from datetime import datetime
from .core import get_connection

def save_reservation(data):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO reservations (store_id, customer_name, contact, res_date, res_time, head_count, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('store_id'),
            data.get('customer_name'),
            data.get('contact'),
            data.get('res_date'),
            data.get('res_time'),
            data.get('head_count', 1),
            data.get('status', 'confirmed'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Reservation Save Error: {e}")
        return False
    finally:
        conn.close()

def update_reservation_status(reservation_id, status):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE reservations SET status = ? WHERE id = ?", (status, reservation_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Reservation Update Error: {e}")
        return False
    finally:
        conn.close()

def get_reservations(store_id):
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM reservations WHERE store_id = ? ORDER BY res_date, res_time", conn, params=(store_id,))
        return df
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()

def save_business_record(user_type, data):
    conn = get_connection()
    c = conn.cursor()
    try:
        if user_type == "일반사업자":
            c.execute('''
                INSERT INTO records_general (date_time, customer_name, contact, menu_info, head_count, amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('일시'), data.get('고객명'), data.get('연락처'), 
                data.get('메뉴/인원'), data.get('인원'), data.get('결제금액'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        elif user_type == "택배사업자":
             c.execute('''
                INSERT INTO records_delivery (date_time, sender_name, receiver_name, receiver_addr, item_type, fee, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('접수일시'), data.get('발송인명'), data.get('수령인명'),
                data.get('수령인 주소(AI추출)'), data.get('물품종류'), data.get('수수료'),
                data.get('상태', '접수완료'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        conn.commit()
        return True, "저장 성공"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()
