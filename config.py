import os
import toml
from dotenv import load_dotenv

# dotenv 자동 로드 (.env 파일이 있으면 환경변수에 병합)
load_dotenv()

def load_secrets():
    """Load secrets from secrets.toml."""
    secrets = {}
    try:
        if os.path.exists("secrets.toml"):
            secrets = toml.load("secrets.toml")
    except Exception:
        pass
    return secrets

def get_secret(key: str, default: str = "") -> str:
    """Get secret from environment variable (including .env) or secrets.toml."""
    # Priority 1: Environment Variable (.env or system)
    value = os.environ.get(key)
    if value:
        return value
        
    # Priority 2: secrets.toml
    secrets = load_secrets()
    return secrets.get(key, default)

