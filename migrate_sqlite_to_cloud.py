
import sqlite3
import os
import db_cloudsql
from sqlalchemy import text

# Local SQLite DB
SQLITE_DB = "database.db"

def migrate_data():
    if not os.path.exists(SQLITE_DB):
        print(f"[!] Local database {SQLITE_DB} not found.")
        return

    print(f"[*] Reading from local SQLite: {SQLITE_DB}")
    conn_sqlite = sqlite3.connect(SQLITE_DB)
    conn_sqlite.row_factory = sqlite3.Row
    c = conn_sqlite.cursor()

    # Cloud SQL Engine
    # Ensure CLOUD_SQL_DSN is set in env
    try:
        engine = db_cloudsql.get_engine()
        print("[*] Connected to Cloud SQL.")
    except Exception as e:
        print(f"[!] Cloud SQL Connection Error: {e}")
        return

    tables_to_migrate = [
        "users", "stores", "products", "orders", 
        "wallet_logs", "wallet_topups", "sms_logs",
        "virtual_numbers", "couriers", "riders",
        "cached_responses", "ai_usage_logs" # New tables
    ]

    with engine.begin() as conn_cloud:
        for table in tables_to_migrate:
            print(f"[-] Migrating table: {table}...")
            try:
                # 1. Read from SQLite
                c.execute(f"SELECT * FROM {table}")
                rows = c.fetchall()
                if not rows:
                    print(f"    -> No data in valid table {table}. Skipping.")
                    continue
                
                print(f"    -> Found {len(rows)} rows.")

                # 2. Insert into Cloud SQL
                # utilizing SQLAlchemy's capabilities or db_cloudsql functions?
                # Dynamic insert is tricky with varying schemas. 
                # Let's try to map rows to dictionaries and use SQLAlchemy's insert.
                
                # Get column names from first row
                columns = rows[0].keys()
                
                # Prepare data list
                data = [dict(row) for row in rows]
                
                # Simple INSERT replacement. 
                # Note: This might fail on duplicate primary keys if run multiple times.
                # Ideally we want UPSERT but that's dialect specific. 
                # For migration, we assume Cloud DB is empty or we ignore duplicates.
                
                # Using SQLAlchemy Core
                from sqlalchemy import Table, MetaData
                metadata = MetaData()
                try:
                    # Reflect table from Cloud SQL
                    t = Table(table, metadata, autoload_with=engine)
                    
                    # Clean data: remove keys that might not exist in target if schema drifted?
                    # Or assume schema is synced via db_cloudsql.init_db()
                    
                    # Insert (skip duplicates if possible? OR DELETE ALL FIRST?)
                    # Safety: Let's NOT delete. Let's try insert and ignore errors? No that's slow.
                    # Let's use clean insert.
                    
                    conn_cloud.execute(t.insert(), data)
                    print(f"    -> [OK] Inserted.")
                except Exception as e:
                    print(f"    -> [!] Insert failed (Table might not exist or Duplicates): {e}")

            except sqlite3.OperationalError:
                print(f"    -> [!] Table {table} not found in SQLite.")

    conn_sqlite.close()
    print("[*] Migration Complete.")

if __name__ == "__main__":
    # Check if Cloud SQL DSN is set
    if not os.environ.get("CLOUD_SQL_DSN"):
        print("[!] Please set CLOUD_SQL_DSN environment variable.")
        print("    Example: $env:CLOUD_SQL_DSN='postgresql+pg8000://user:pass@/db?unix_sock=...'")
    else:
        migrate_data()
