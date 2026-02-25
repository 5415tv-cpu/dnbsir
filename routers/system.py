from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import db_manager as db

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent

@router.post("/api/debug_log")
async def debug_log(request: Request):
    data = await request.json()
    print(f"[Frontend Log] {data}")
    return {"status": "ok"}

@router.get("/api/health_full")
def health_full():
    pass 
    # To avoid API_URL issues if not imported here
    status = {"status": "ok", "db": "unknown", "base_dir": str(BASE_DIR), "env": {}}
    try:
        store = db.get_store("test_store")
        status["db"] = "connected" if store else "empty"
    except Exception as e:
        status["db"] = f"error: {e}"
    
    return status

@router.get("/api/version")
def debug_version():
    from db_backend import _use_cloudsql
    backend = "Cloud SQL" if _use_cloudsql() else "SQLite"
    return {"source": "modularized", "status": "patched_v4", "db_backend": backend}

@router.get("/api/admin/security/backup")
async def backup_db_endpoint():
    success, path = db.create_db_backup()
    if success:
        return {"success": True, "path": path}
    return {"success": False, "error": path}

@router.get("/api/admin/security/integrity")
async def check_integrity_endpoint():
    ok = db.get_db_integrity()
    return {"status": "OK" if ok else "CORRUPTED"}

@router.get("/health")
def health_check():
    return {"ok": True}
