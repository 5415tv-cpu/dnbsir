import os
import os

# 1. 스위치(환경 변수)를 가장 먼저 확인합니다.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_BACKEND = os.environ.get("DB_BACKEND", "").lower()

use_postgres = False
if DB_BACKEND == "sqlite":
    use_postgres = False
elif DATABASE_URL.startswith("postgres"):
    use_postgres = True
elif DB_BACKEND in ("postgresql", "postgres"):
    use_postgres = True

# 2. 확인된 결과에 따라 딱 하나의 DB만 임포트합니다 (Lazy Import)
# 2. 확인된 결과에 따라 딱 하나의 DB만 임포트합니다 (Lazy Import)
_sqlite = None
_postgres = None
get_db_session = None  # 👈 외부 부서(market.py 등)에 내어줄 공통 접속증 발급기

if use_postgres:
    print("[V] DB Backend: PostgreSQL (실전 모드)")
    import db_postgres as _postgres
    get_db_session = _postgres.get_db_session  # 👈 실전용 발급기 연결
else:
    print("[V] DB Backend: SQLite (로컬 모드)")
    import db_sqlite as _sqlite
    get_db_session = _sqlite.get_db_session  # 👈 로컬용 발급기 연결

# ... (이 아래는 기존 코드 유지) ...
# try:
#     import db as _sqlite
# except Exception:
#     _sqlite = None

# Detect database configuration from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_BACKEND = os.environ.get("DB_BACKEND", "").lower()

# Determine which database engine to use
use_postgres = False
detection_source = "None"

if DB_BACKEND == "sqlite":
    use_postgres = False
    detection_source = "DB_BACKEND (sqlite)"
elif DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
    use_postgres = True
    detection_source = "DATABASE_URL"
elif DB_BACKEND in ("postgresql", "postgres"):
    use_postgres = True
    detection_source = "DB_BACKEND"
else:
    # Default to PostgreSQL only if the module is available and DATABASE_URL is provided
    if _postgres is not None and DATABASE_URL:
        use_postgres = True
        detection_source = "Implicit (db_postgres module)"

# Bind active implementation and log status
if use_postgres and _postgres is not None:
    print(f"[V] DB Backend: PostgreSQL (Detection: {detection_source})", flush=True)
    db_impl = _postgres
else:
    print(f"[!] DB Backend: SQLite (Detection: {detection_source})", flush=True)
    db_impl = _sqlite

class _DBProxy:
    def __getattr__(self, name):
        if hasattr(db_impl, name):
            return getattr(db_impl, name)
        raise AttributeError(f"Active DB backend has no attribute: {name}")

db = _DBProxy()

# Expose async_engine for FastAPI oauth / standard routes
async_engine = getattr(db_impl, "async_engine", None)

