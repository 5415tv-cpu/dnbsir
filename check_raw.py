import sqlite3
import pandas as pd

DB_FILE = "database.db"

def check_stores():
    try:
        conn = sqlite3.connect(DB_FILE)
        # Select specific columns to avoid clutter
        df = pd.read_sql("SELECT store_id, password, name, phone FROM stores", conn)
        print("Stores (ID, Password, Name, Phone):")
        print(df.to_string())
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_stores()
