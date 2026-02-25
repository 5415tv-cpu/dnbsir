import sqlite3

def inject_store():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Ensure stores table
    c.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            store_id TEXT PRIMARY KEY, 
            password TEXT, 
            name TEXT, 
            owner_name TEXT, 
            phone TEXT, 
            points INTEGER DEFAULT 0, 
            membership TEXT DEFAULT "free", 
            wallet_balance INTEGER DEFAULT 0, 
            is_signed BOOLEAN DEFAULT 0, 
            category TEXT DEFAULT "", 
            role TEXT DEFAULT "owner",
            auto_reply_msg TEXT DEFAULT "",
            auto_reply_missed INTEGER DEFAULT 0,
            auto_reply_end INTEGER DEFAULT 0,
            auto_refill_on INTEGER DEFAULT 0,
            auto_refill_amount INTEGER DEFAULT 0
        )
    ''')
    
    # Inject test_store
    try:
        c.execute('''
            INSERT OR REPLACE INTO stores (
                store_id, password, name, owner_name, phone, wallet_balance, is_signed, category, role
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('test_store', '1234', '강남 1호점', '김사장', '010-1234-5678', 50000, 1, 'food', 'owner'))
        conn.commit()
        print("✅ Store Data Injected.")
    except Exception as e:
        print(f"❌ Store Injection Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inject_store()
