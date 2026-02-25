import sys
import os
import traceback

sys.path.append(os.path.abspath("."))

try:
    import db_manager
    print("DB Initialized.")
    
    store_id = "test_store"
    
    # 1. Get Initial Points
    wallet = db_manager.get_wallet_details(store_id)
    initial_points = wallet['current_points']
    print(f"Initial Points: {initial_points}")
    
    # 2. Refund 100P
    print("Refunding 100P...")
    success = db_manager.refund_points(store_id, 100, "Test Refund")
    
    if success:
        wallet = db_manager.get_wallet_details(store_id)
        new_points = wallet['current_points']
        print(f"New Points: {new_points}")
        
        if new_points == initial_points + 100:
            print("SUCCESS: Points correctly refunded.")
        else:
            print(f"FAIL: Expected {initial_points + 100}, got {new_points}")
    else:
        print("FAIL: Refund function returned False")
    
except Exception:
    traceback.print_exc()
