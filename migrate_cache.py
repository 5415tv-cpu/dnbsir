import sqlite3
import os

DB_PATH = "database.db"

def migrate_cache():
    print(f"[*] Starting Cache Migration for {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print(f"[!] Database file {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    try:
        # Create cached_responses table
        print("[-] Creating 'cached_responses' table...")
        c.execute('''
            CREATE TABLE IF NOT EXISTS cached_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_id TEXT,
                question TEXT,
                answer TEXT,
                hits INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT
            )
        ''')
        
        # Create Index for fast lookup
        print("[-] Creating Indexes...")
        c.execute("CREATE INDEX IF NOT EXISTS idx_cache_store_question ON cached_responses(store_id, question)")
        
        conn.commit()
        print("[OK] Migration Complete.")
        
    except Exception as e:
        print(f"[X] Migration Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_cache()
