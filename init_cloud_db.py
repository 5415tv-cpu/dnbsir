
import os
import db_cloudsql as db

# Use this to init missing tables in cloud sql without running full app
if __name__ == "__main__":
    if not os.environ.get("CLOUD_SQL_DSN"):
        print("[!] Please set CLOUD_SQL_DSN environment variable.")
    else:
        print("[*] Initializing Cloud SQL Tables...")
        try:
           db.init_db()
           print("[OK] Tables created.")
        except Exception as e:
           print(f"[!] Error: {e}")
