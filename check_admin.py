import sqlite3
import os

DB_FILE = "database.db"

def check_admin():
    if not os.path.exists(DB_FILE):
        print("Database file not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("SELECT store_id, password FROM stores WHERE store_id = 'delivery_master'")
        row = c.fetchone()
        if row:
            print(f"Admin account exists. ID: {row[0]}, Password: {row[1]}")
        else:
            print("Admin account 'delivery_master' does not exist yet.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_admin()
