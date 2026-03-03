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

@router.get("/api/ping")
async def ping():
    return {"status": "ok", "message": "pong"}

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

@router.get("/status", response_class=HTMLResponse)
async def visual_health_check():
    return """
    <html>
        <head>
            <title>동네비서 시스템 상태</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: 'Noto Sans KR', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #f8fafc; margin: 0; }
                .card { background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center; border: 1px solid #e2e8f0; width: 80%; max-width: 400px; }
                .status-light { width: 40px; height: 40px; background: #22c55e; border-radius: 50%; display: inline-block; box-shadow: 0 0 20px #22c55e; animation: pulse 2s infinite; margin-bottom: 24px; }
                @keyframes pulse { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 20px rgba(34, 197, 94, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); } }
                h1 { color: #0f172a; margin: 0 0 12px 0; font-size: 1.5rem; }
                p { color: #64748b; margin: 0; font-size: 1rem; line-height: 1.5; }
                .refresh-btn { margin-top: 32px; padding: 14px 28px; border: none; background: #f1f5f9; color: #334155; border-radius: 12px; cursor: pointer; font-weight: bold; font-size: 1rem; width: 100%; transition: all 0.2s; }
                .refresh-btn:hover { background: #e2e8f0; }
            </style>
        </head>
        <body>
            <div class="card">
                <div class="status-light"></div>
                <h1>시스템 정상 가동 중</h1>
                <p>AI 동네비서 마이크로서비스가 완벽하게 돌아가고 있습니다.</p>
                <button class="refresh-btn" onclick="location.reload()">새로고침</button>
            </div>
        </body>
    </html>
    """
