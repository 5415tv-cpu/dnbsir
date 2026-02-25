import sqlite3
import datetime

DB_PATH = "database.db"

def inject_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print(f"🔌 Connected to {DB_PATH}")

    # 1. Ensure Orders Table Exists (Minimal Schema for Safety)
    # in case it's a fresh DB
    c.execute("DROP TABLE IF EXISTS orders") # Force Fresh Schema
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id TEXT,
            item_name TEXT,
            amount INTEGER,
            customer_phone TEXT,
            created_at TEXT,
            settlement_status TEXT DEFAULT 'pending',
            fee_amount INTEGER DEFAULT 0,
            net_amount INTEGER DEFAULT 0,
            type TEXT DEFAULT 'FARM',
            payment_method TEXT DEFAULT 'CARD'
        )
    ''')

    # 2. Sample Data
    store_id = "test_store"
    # Dates: Recent enough to show up in "Last 30 Days"
    samples = [
        ("프리미엄 한우 세트", 150000, "010-1234-5678", "2026-02-14 10:00:00"),
        ("자연산 송이버섯", 200000, "010-9876-5432", "2026-02-14 11:30:00"),
        ("프리미엄 한우 세트", 150000, "010-5555-4444", "2026-02-15 09:15:00"),
        ("프리미엄 한우 세트", 150000, "010-1111-2222", "2026-02-16 12:45:00"),
        ("자연산 송이버섯", 400000, "010-7777-8888", "2026-02-16 14:20:00")
    ]

    print("🚀 Injecting 5 Sample Orders...")
    
    for item_name, amount, phone, date in samples:
        fee = int(amount * 0.033)
        net = amount - fee
        
        # Insert (Correct Schema)
        c.execute('''
            INSERT INTO orders (
                store_id, item_name, amount, customer_phone, created_at,
                fee_amount, net_amount, settlement_status, type, payment_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            store_id, item_name, amount, phone, date,
            fee, net, 'pending', 'FARM', 'CARD'
        ))

    conn.commit()
    print("✅ Injection Complete.")
    
    # Verification
    c.execute("SELECT COUNT(*), SUM(amount) FROM orders WHERE store_id=?", (store_id,))
    row = c.fetchone()
    print(f"📊 Verification: Count={row[0]}, Total Amount={row[1]}")
    
    conn.close()

if __name__ == "__main__":
    inject_data()
