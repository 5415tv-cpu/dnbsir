import db_sqlite as db
import datetime

STORE_ID = "test_billing_store"

def test_billing():
    print("[*] Starting Billing Logic Test...")
    
    # 1. Setup Test Store
    print(f"[-] Setting up store '{STORE_ID}'...")
    db.save_store({
        "store_id": STORE_ID,
        "name": "Billing Test Store",
        "points": 100,
        "daily_token_limit": 500,
        "current_usage": 0,
        "last_usage_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "password": "1234" # Required field usually
    })
    
    # [Fix] Manually update limit because save_store resets it
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("UPDATE stores SET daily_token_limit = 500 WHERE store_id = ?", (STORE_ID,))
    conn.commit()
    conn.close()
    
    # 2. Check Initial Status
    allowed, msg = db.check_ai_limit(STORE_ID)
    print(f"[-] Initial Check: Allowed={allowed}, Msg='{msg}'")
    if not allowed:
        print("[X] Failed: Store should be allowed.")
        return

    # 3. Simulate Usage (Cost: 10 + 100//100 = 11 points)
    input_tokens = 50
    output_tokens = 50
    print(f"[-] Simulating Usage: {input_tokens} in / {output_tokens} out")
    
    success, cost = db.log_ai_usage(STORE_ID, input_tokens, output_tokens)
    print(f"[-] Log Result: Success={success}, Cost={cost}")
    
    # 4. Verify Deduction
    store = db.get_store(STORE_ID)
    expected_points = 100 - cost
    expected_usage = input_tokens + output_tokens
    
    print(f"[-] Store Status: Points={store['points']} (Exp: {expected_points}), Usage={store['current_usage']} (Exp: {expected_usage})")
    
    if store['points'] != expected_points:
        print(f"[X] Failed: Points mismatch.")
    elif store['current_usage'] != expected_usage:
        print(f"[X] Failed: Usage mismatch.")
    else:
        print(f"[OK] Billing Logic Verified.")

    # 5. Test Limit Exceeded
    print("[-] Testing Daily Limit...")
    # Manually set usage to limit
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("UPDATE stores SET current_usage = 1000 WHERE store_id = ?", (STORE_ID,))
    conn.commit()
    conn.close()
    
    allowed, msg = db.check_ai_limit(STORE_ID)
    print(f"[-] Limit Check: Allowed={allowed}, Msg='{msg}'")
    if not allowed and "limit exceeded" in msg:
        print("[OK] Limit Enforcement Verified.")
    else:
        print(f"[X] Failed: Should be blocked by limit.")

if __name__ == "__main__":
    test_billing()
