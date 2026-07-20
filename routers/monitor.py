"""
콜백 블랙박스 모니터링 API
/api/admin/webhook-logs  — 로그 조회
/api/admin/webhook-stats — 통계 요약
/admin/webhook-monitor   — 대시보드 페이지
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import db_manager as db
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ── 서버간 인증 키 (탄탄제작소 Docker → 동네비서 API) ──────────────────
def _get_server_key() -> str:
    import config
    return config.get_secret("TANTAN_SERVER_KEY", "")

# ── 공통: 관리자 인증 확인 ────────────────────────────────────────────
def _require_admin(request: Request):
    # 1) 쿠키 세션 (관리자 브라우저)
    if request.cookies.get("admin_session"):
        return
    # 2) X-Server-Key 헤더 (탄탄제작소 서버간 호출)
    server_key = _get_server_key()
    if server_key and request.headers.get("X-Server-Key") == server_key:
        return
    raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


# ── 로그 목록 API ──────────────────────────────────────────────────────
@router.get("/api/admin/webhook-logs")
async def get_webhook_logs_api(
    request: Request,
    date: Optional[str] = None,       # 단일 날짜: 2026-06-17
    date_from: Optional[str] = None,  # 시작 날짜
    date_to: Optional[str] = None,    # 종료 날짜
    stage: Optional[str] = None,      # SMS_OK / SMS_FAIL / COOLDOWN 등
    phone: Optional[str] = None,      # 번호 검색
    limit: int = 200,
):
    _require_admin(request)
    # 단일 날짜면 from/to 동일하게 처리
    if date:
        date_from = date_from or date
        date_to   = date_to   or date
    try:
        logs = db.get_webhook_logs(
            date_from=date_from,
            date_to=date_to,
            stage=stage,
            customer_phone=phone,
            limit=min(limit, 500),
        )
        return {"success": True, "total": len(logs), "logs": logs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ── 통계 API ──────────────────────────────────────────────────────────
@router.get("/api/admin/webhook-stats")
async def get_webhook_stats_api(
    request: Request,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    _require_admin(request)
    if date:
        date_from = date_from or date
        date_to   = date_to   or date
    try:
        stats = db.get_webhook_stats(date_from=date_from, date_to=date_to)
        return {"success": True, **stats}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ── 대시보드 페이지 ──────────────────────────────────────────────────
@router.get("/admin/webhook-monitor", response_class=HTMLResponse)
async def webhook_monitor_page(request: Request):
    _require_admin(request)
    return templates.TemplateResponse(
        request, "webhook_monitor.html", {"request": request}
    )
