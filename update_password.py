import sqlite3
import datetime

def update_admin():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute("SELECT * FROM stores WHERE store_id = 'admin'")
    if cursor.fetchone():
        print("Updating existing admin password...")
        cursor.execute("UPDATE stores SET password = '123456' WHERE store_id = 'admin'")
    else:
        print("Creating new admin account...")
        # Use only valid columns from db_sqlite.py schema
        cursor.execute("""
            INSERT INTO stores (store_id, password, name, owner_name, phone, role, created_at)
            VALUES ('admin', '123456', '관리자', '관리자', '010-0000-0000', 'owner', ?)
        """, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    
    conn.commit()
    conn.close()
    print("✅ Admin password set to 123456")

if __name__ == "__main__":
    update_admin()
