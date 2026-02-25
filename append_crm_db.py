
import os

new_code = """

# ==========================================
# CRM & Security Extensions (Appended)
# ==========================================

def get_today_revisit_list(store_id):
    conn = get_connection()
    try:
        query_today = "SELECT DISTINCT sender_phone, sender_name FROM orders WHERE store_id = ? AND date(created_at) = date('now')"
        c = conn.cursor()
        c.execute(query_today, (store_id,))
        today_rows = c.fetchall()
        
        revisit_list = []
        for row in today_rows:
            phone = row[0]
            name = row[1]
            if not phone: continue
            
            # Check Past Visits
            c.execute("SELECT COUNT(*) FROM orders WHERE store_id = ? AND sender_phone = ? AND date(created_at) < date('now')", (store_id, phone))
            past_count = c.fetchone()[0]
            
            if past_count > 0:
                revisit_list.append({
                    "name": name or "손님",
                    "phone": phone,
                    "visit_count": past_count + 1 # Includes today
                })
                
        return revisit_list
    except Exception as e:
        print(f"Revisit List Error: {e}")
        return []
    finally:
        conn.close()

def create_db_backup():
    try:
        import shutil
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_db_sqlite_{timestamp}.sqlite"
        shutil.copy("db_sqlite.sqlite", backup_path)
        return True, backup_path
    except Exception as e:
        return False, str(e)

def get_db_integrity_status():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("PRAGMA integrity_check;")
        result = c.fetchone()[0]
        return result == "ok"
    except:
        return False
    finally:
        conn.close()
"""

with open("db_sqlite.py", "a", encoding="utf-8") as f:
    f.write(new_code)

print("Successfully appended CRM functions to db_sqlite.py")
