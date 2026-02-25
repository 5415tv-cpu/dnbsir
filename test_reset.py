
import os
os.environ["DB_BACKEND"] = "sqlite"

import db_manager as db
import sys

try:
    print("Testing reset_store_onboarding (SQLite Mode)...")
    # Reset a dummy store ID
    db.reset_store_onboarding("test_store")
    print("Reset successful (no exception raised).")
except Exception as e:
    print(f"Error during reset: {e}")
    sys.exit(1)
