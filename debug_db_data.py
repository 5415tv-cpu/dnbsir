
import sys
import os
import datetime

# Add current directory to path
sys.path.append(os.getcwd())

try:
    import db_sqlite as db
    print("[*] DB Module Imported Successfully")
except ImportError as e:
    print(f"[!] DB Import Failed: {e}")
    sys.exit(1)

def run_diagnostics():
    print("[-] Checking Database Connection...")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check Tables
    tables = ["users", "products", "orders", "courier_visits"]
    print(f"[-] Checking Table Counts:")
    store_id = "test_store"
    
    has_data = False
    
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            count = cursor.fetchone()[0]
            print(f"    - {t}: {count}")
            if count > 0: has_data = True
        except Exception as e:
            print(f"    [!] Error checking {t}: {e}")

    # Inject Data if Empty
    if not has_data:
        print("[!] DB appears empty. Injecting Mock Data for 'test_store'...")
        
        # 1. Create Store (User)
        try:
            db.save_user(store_id, "1234", "AI Store", "010-1234-5678")
            print("    [+] Created Mock User: test_store")
        except Exception as e:
            print(f"    [!] User Creation Error: {e}")

        # 2. Create Product
        try:
            db.save_product(store_id, "맛있는 김치 10kg", 35000, "static/sample_kimchi.jpg", "김치")
            print("    [+] Created Mock Product")
        except Exception as e:
            print(f"    [!] Product Creation Error: {e}")

        # 3. Create Order (Today)
        try:
            db.save_order(store_id, "맛있는 김치 10kg", 35000, "홍길동", "010-1111-2222", "서울시 강남구", "부재시 문앞", "sender_phone_mock")
            # Manually update date to today for accurate dashboard testing
            cursor.execute("UPDATE orders SET created_at = datetime('now') WHERE store_id = ?", (store_id,))
            conn.commit()
            print("    [+] Created Mock Order (Today)")
        except Exception as e:
            print(f"    [!] Order Creation Error: {e}")
            
        # 4. Create Re-visit (Yesterday and Today for CRM)
        try:
            # Past visit
            db.save_order(store_id, "맛있는 김치 10kg", 35000, "단골손님", "010-9999-8888", "서울시", "문앞", "010-9999-8888")
            cursor.execute("UPDATE orders SET created_at = datetime('now', '-1 day') WHERE sender_phone = '010-9999-8888'", ())
            # Today visit
            db.save_order(store_id, "알타리 무 5kg", 20000, "단골손님", "010-9999-8888", "서울시", "문앞", "010-9999-8888")
            conn.commit()
            print("    [+] Created Mock CRM Data (Re-visit)")
        except Exception as e:
             print(f"    [!] CRM Data Error: {e}")

    else:
        print("[*] DB has data. No injection needed.")

    conn.close()
    print("[*] Diagnostics Complete.")

if __name__ == "__main__":
    run_diagnostics()
