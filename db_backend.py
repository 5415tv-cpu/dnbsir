import os

import db as _sqlite


def _get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _use_cloudsql() -> bool:
    # Force Enable as per user request
    # Force Enable as per user request - Disabled for local test safety if needed, 
    # but strictly we should rely on DSN check below.
    # if True: # Always True -> Removed to allow fallback
    #      print("[V] DB Backend: Cloud SQL (Forced)")
    #      return True
    
    backend = _get_env("DB_BACKEND", "").lower()
    dsn = _get_env("CLOUD_SQL_DSN", "") or _get_env("DATABASE_URL", "")
    
    use_cloud = backend == "cloudsql" or bool(dsn)
    
    if use_cloud:
        print(f"[V] DB Backend: Cloud SQL (DSN Length: {len(dsn)})")
    else:
        print(f"[!] DB Backend: SQLite (Reason: DB_BACKEND='{backend}', DSN={'Set' if dsn else 'Missing'})")
        
    return use_cloud


class _DBProxy:
    def __init__(self):
        self._cloud = None
        if _use_cloudsql():
            try:
                import db_cloudsql as _cloudsql

                self._cloud = _cloudsql
            except Exception:
                self._cloud = None

    def __getattr__(self, name):
        if self._cloud and hasattr(self._cloud, name):
            return getattr(self._cloud, name)
        if hasattr(_sqlite, name):
            return getattr(_sqlite, name)
        raise AttributeError(f"DB backend has no attribute: {name}")


db = _DBProxy()
