import sys
import os
import traceback

# Add project root to sys.path
PROJECT_ROOT = r"C:\Users\A\Desktop\AI_Store"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Mock environment variables if necessary
os.environ["DB_BACKEND"] = "sqlite"

print(f"Running from: {os.getcwd()}")
print("Attempting to import server.webhook_app...")

try:
    from server.webhook_app import app
    print("✅ Import successful!")
except Exception as e:
    print(f"❌ Import failed: {e}")
    traceback.print_exc()
