import toml
import os
import sys

# Production check: force postgres backend if on Linux (POSIX) or if environment variable is set
if os.name == 'posix' or os.environ.get('DATABASE_URL') or os.environ.get('DB_BACKEND') == 'postgres':
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

