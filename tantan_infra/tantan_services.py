import toml
import os
import sys

# 백엔드 선택: DATABASE_URL 또는 DB_BACKEND=postgres 환경변수가 명시된 경우에만 postgres 사용
# ※ os.name == 'posix' 체크는 제거 — Docker(Linux)에서도 sqlite를 쓰는 경우가 있음
if os.environ.get('DATABASE_URL') or os.environ.get('DB_BACKEND') == 'postgres':
    backend = 'postgres'
else:
    config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        backend = config.get('database', {}).get('backend', 'sqlite')
    except Exception as e:
        backend = 'sqlite'

if backend == 'sqlite':
    from tantan_services_sqlite import *
else:
    from tantan_services_pg import *
