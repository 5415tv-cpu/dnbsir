import sqlite3
import datetime

DB_FILE = "database.db"

def migrate_indexes():
    print(f"[*] Starting Index Migration on {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # List of tables that have store_id and need indexing
    target_tables = [
        "orders", 
        "products", 
        "customers", 
        "records_general", 
        "records_delivery", 
        "wallet_logs", 
        "message_logs", 
        "expenses",
        "wallet_topups",
        "reservations"
    ]
    
    success_count = 0
    
    for table in target_tables:
        index_name = f"idx_{table}_store_id"
        try:
            # Check if table exists first
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not c.fetchone():
                print(f"[!] Table '{table}' not found. Skipping.")
                continue
                
            print(f"[-] Creating index '{index_name}' on table '{table}'...")
            c.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}(store_id)")
            success_count += 1
            print(f"[OK] Index created (or already exists).")
            
        except Exception as e:
            print(f"[X] Failed to create index on {table}: {e}")
            
    conn.commit()
    conn.close()
    print(f"\n[=] Migration Complete. {success_count} indexes verified.")

if __name__ == "__main__":
    migrate_indexes()
