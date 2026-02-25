import sqlite3
import datetime

DB_FILE = "database.db"

def migrate_billing():
    print(f"[*] Starting Billing Migration on {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Add columns to stores table
    print("[-] Adding billing columns to 'stores' table...")
    try:
        c.execute("ALTER TABLE stores ADD COLUMN daily_token_limit INTEGER DEFAULT 10000")
        print("[OK] Added daily_token_limit")
    except Exception as e:
        print(f"[!] daily_token_limit might already exist: {e}")

    try:
        c.execute("ALTER TABLE stores ADD COLUMN tier TEXT DEFAULT 'basic'")
        print("[OK] Added tier")
    except Exception as e:
        print(f"[!] tier might already exist: {e}")
        
    try:
        c.execute("ALTER TABLE stores ADD COLUMN current_usage INTEGER DEFAULT 0")
        print("[OK] Added current_usage")
    except Exception as e:
        print(f"[!] current_usage might already exist: {e}")
        
    try:
        c.execute("ALTER TABLE stores ADD COLUMN last_usage_date TEXT")
        print("[OK] Added last_usage_date")
    except Exception as e:
        print(f"[!] last_usage_date might already exist: {e}")

    # 2. Create ai_usage_logs table
    print("[-] Creating 'ai_usage_logs' table...")
    try:
        c.execute('''
            CREATE TABLE IF NOT EXISTS ai_usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT,
                tokens_input INTEGER,
                tokens_output INTEGER,
                cost INTEGER,
                timestamp TEXT
            )
        ''')
        print("[OK] Created ai_usage_logs")
        
        # Add index for queries
        c.execute("CREATE INDEX IF NOT EXISTS idx_ai_logs_store_id ON ai_usage_logs(store_id)")
        print("[OK] Created index on ai_usage_logs(store_id)")
        
    except Exception as e:
        print(f"[X] Failed to create ai_usage_logs: {e}")

    conn.commit()
    conn.close()
    print("\n[=] Billing Migration Complete.")

if __name__ == "__main__":
    migrate_billing()
