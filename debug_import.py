
import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

try:
    print("Attempting to import server.webhook_app...")
    import server.webhook_app
    print("Successfully imported server.webhook_app")
except Exception as e:
    print(f"Import Failed: {e}")
    import traceback
    traceback.print_exc()
