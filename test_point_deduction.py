
import os
import requests
import db_cloudsql as db

# Ensure Cloud SQL mock
os.environ["CLOUD_SQL_DSN"] = "sqlite:///cloud_simulation.db"
os.environ["DB_BACKEND"] = "cloudsql"

STORE_ID = "wallet_test_store"

def setup_test_store():
    print(f"[*] Setting up test store: {STORE_ID}")
    db.init_db() # Ensure tables
    db.save_store({
        "store_id": STORE_ID,
        "name": "Wallet Test Store",
        "points": 1000,
        "password": "123",
        "daily_token_limit": 10000
    })
    # Reset usage logs for clean test
    db._execute("DELETE FROM ai_usage_logs WHERE store_id = :id", {"id": STORE_ID})
    
    # Verify initial points
    store = db.get_store(STORE_ID)
    print(f"    -> Initial Points: {store['points']}")
    return store['points']

def test_deduction():
    # 1. Setup
    initial_points = setup_test_store()
    
    # 2. Simulate AI Usage (Directly calling log_ai_usage for unit test accuracy)
    #    (Integration test with requests would require running server)
    print("[-] Simulating AI Usage (Input: 50, Output: 50 tokens)...")
    input_tokens = 50
    output_tokens = 50
    
    success, cost = db.log_ai_usage(STORE_ID, input_tokens, output_tokens)
    
    if not success:
        print("[!] Failed to log usage.")
        return
        
    print(f"    -> Cost Calculated: {cost} P")
    
    # 3. Verify Deduction
    store = db.get_store(STORE_ID)
    final_points = store['points']
    print(f"    -> Final Points: {final_points}")
    
    expected_points = initial_points - cost
    
    if final_points == expected_points:
        print(f"[OK] Deduction Verified! ({initial_points} - {cost} = {final_points})")
    else:
        print(f"[FAIL] Point Mismatch! Expected {expected_points}, got {final_points}")

    # 4. Verify Wallet Stats (What user sees on dashboard)
    print("[-] Verifying Dashboard Stats...")
    stats = db.get_wallet_details(STORE_ID)
    print(f"    -> Dashboard Points: {stats['current_points']}")
    print(f"    -> AI Usage Today: {stats['ai_usage_today']}")
    
    if stats['current_points'] == final_points and stats['ai_usage_today']['cost'] > 0:
         print("[OK] Dashboard Data Sync Verified.")
    else:
         print("[!] Dashboard Data likely stale or incorrect.")

if __name__ == "__main__":
    test_deduction()
