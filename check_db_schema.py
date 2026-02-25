import sqlite3
import pandas as pd

DB_FILE = "database.db"

def list_schema():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # List Tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables.")
        
        for table in tables:
            table_name = table[0]
            print(f"\n[Table: {table_name}]")
            
            # Get Columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]
            print(f"Columns: {col_names}")
            
            # Check for store_id
            if 'store_id' in col_names:
                print("✅ store_id present")
            else:
                print("❌ store_id MISSING")
                
            # List Indexes
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            if indexes:
                print("Indexes:")
                for idx in indexes:
                    print(f"  - {idx[1]}")
            else:
                print("Indexes: None")
                
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    # Redirect stdout to file
    with open("schema_dump.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        list_schema()
