import os
import toml

def load_secrets():
    """Load secrets from secrets.toml or environment variables."""
    secrets = {}
    
    # Try loading from secrets.toml
    try:
        if os.path.exists("secrets.toml"):
            secrets = toml.load("secrets.toml")
    except Exception:
        pass
        
    return secrets

def get_secret(key: str, default: str = "") -> str:
    """Get secret from environment variable or secrets.toml."""
    # Priority 1: Environment Variable
    value = os.environ.get(key)
    if value:
        return value
        
    # Priority 2: secrets.toml
    secrets = load_secrets()
    return secrets.get(key, default)
