from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import hashlib

# Centralized Jinja2Templates instantiation
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Cache to avoid reading files repeatedly in production/dev
_asset_manifest = {}
_manifest_loaded = False

def get_static_url(path: str) -> str:
    global _asset_manifest, _manifest_loaded
    # Load manifest once
    if not _manifest_loaded:
        manifest_path = BASE_DIR / "static" / "dist" / "assets_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    _asset_manifest = json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to load assets manifest: {e}")
        _manifest_loaded = True
    
    # Check manifest first (production build)
    if path in _asset_manifest:
        return f"/static/dist/{_asset_manifest[path]}"
        
    # Development fallback: compute hash dynamically and append as query param
    local_file = BASE_DIR / "static" / path
    if local_file.exists():
        try:
            with open(local_file, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()[:8]
            return f"/static/{path}?h={h}"
        except Exception as e:
            print(f"[WARNING] Failed to hash file {path}: {e}")
            
    return f"/static/{path}"

# Register helper function globally
templates.env.globals['static_url'] = get_static_url
