from fastapi import FastAPI, HTTPException, Request, Form, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import typing

import sms_manager as sms
import db_manager as db

app = FastAPI()

# Mount Static Files
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- PWA Pages ---

# 1. PWA 홈 (Citizen Portal)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 2. 관리자 로그인 페이지
@app.get("/admin", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 3. 로그인 처리 API
@app.post("/api/login")
async def login(response: Response, store_id: str = Form(...), password: str = Form(...)):
    store = db.get_store(store_id)
    
    # 간단한 비밀번호 확인 (실제 운영 시에는 bcrypt 사용 권장)
    if store and str(store.get('password')) == password:
        # 세션 쿠키 설정 (간단히 구현)
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie(key="admin_session", value=store_id)
        return response
    else:
        # 로그인 실패 시 다시 로그인 페이지로 (에러 메시지 처리 필요)
        return RedirectResponse(url="/admin?error=invalid", status_code=303)

# 4. 관리자 대시보드
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    store_id = request.cookies.get("admin_session")
    if not store_id:
        return RedirectResponse(url="/admin")
    
    store = db.get_store(store_id)
    if not store:
        return RedirectResponse(url="/admin")
        
    return templates.TemplateResponse("dashboard.html", {"request": request, "store": store})

# 5. 로그아웃
@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/admin", status_code=303)
    response.delete_cookie("admin_session")
    return response

# 2. 기존에 잘 작동하던 /docs 기능은 그대로 유지됩니다.


class MissedCallWebhook(BaseModel):
    virtual_number: str
    caller_phone: str
    store_id: str | None = None
    store_name: str | None = None
    order_link: str | None = None


def _get_env(app_: FastAPI, key: str, default: str = "") -> str:
    return app_.extra.get(key, default)


def _extract_value(payload: dict, keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _normalize_nhn_payload(payload: dict) -> dict:
    virtual_number = _extract_value(
        payload,
        ["virtual_number", "virtualNumber", "called", "callee", "to", "dn", "called_number", "vn"],
    )
    caller_phone = _extract_value(
        payload,
        ["caller_phone", "caller", "from", "ani", "src", "callerNumber", "caller_number"],
    )
    store_id = _extract_value(payload, ["store_id", "storeId", "merchant_id"])
    store_name = _extract_value(payload, ["store_name", "storeName", "merchant_name"])
    order_link = _extract_value(payload, ["order_link", "orderLink", "link"])
    if not order_link and store_id:
        base_url = _get_env(app, "APP_BASE_URL", "https://dnbsir.com").rstrip("/")
        order_link = f"{base_url}/?id={store_id}"
    return {
        "virtual_number": virtual_number,
        "caller_phone": caller_phone,
        "store_id": store_id,
        "store_name": store_name,
        "order_link": order_link,
    }


def _check_token(request: Request) -> None:
    token = request.headers.get("X-Webhook-Token", "")
    expected = _get_env(request.app, "WEBHOOK_TOKEN", "")
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _send_test_notice(app_: FastAPI):
    if not _get_env(app_, "ENABLE_WEBHOOK_TEST_NOTIFY", "true").lower().startswith("t"):
        return
    admin_phone = _get_env(app_, "ADMIN_ALERT_PHONE", "010-2384-7447")
    sms.send_cloud_sms(admin_phone, "연결 성공", store_id="SYSTEM")


@app.post("/webhook/missed-call")
def handle_missed_call(payload: MissedCallWebhook, request: Request):
    _check_token(request)
    ok, msg = sms.process_missed_call_webhook(payload.model_dump())
    db.log_sms(
        payload.store_id or "UNKNOWN",
        payload.caller_phone,
        "WEBHOOK",
        "missed_call",
        "OK" if ok else "FAIL",
        msg,
    )
    if ok:
        _send_test_notice(request.app)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.post("/api/webhook/call-detect")
async def handle_call_detect(request: Request):
    _check_token(request)
    payload = await request.json()
    normalized = _normalize_nhn_payload(payload)
    ok, msg = sms.process_missed_call_webhook(normalized)
    db.log_sms(
        normalized.get("store_id") or "UNKNOWN",
        normalized.get("caller_phone", ""),
        "WEBHOOK",
        "call_detect",
        "OK" if ok else "FAIL",
        msg,
    )
    if ok:
        _send_test_notice(request.app)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@app.get("/health")
def health_check():
    return {"ok": True}


@app.on_event("startup")
def _load_webhook_token():
    import os

    app.extra["WEBHOOK_TOKEN"] = os.environ.get("WEBHOOK_TOKEN", "")
    app.extra["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "https://dnbsir.com")
    app.extra["ADMIN_ALERT_PHONE"] = os.environ.get("ADMIN_ALERT_PHONE", "010-2384-7447")
    app.extra["ENABLE_WEBHOOK_TEST_NOTIFY"] = os.environ.get("ENABLE_WEBHOOK_TEST_NOTIFY", "true")

from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 404:
        return HTMLResponse(
            f"""
            <html>
                <head><meta charset="utf-8"><title>404 페이지 없음</title></head>
                <body style="text-align: center; padding-top: 50px; font-family: sans-serif;">
                    <h1 style="color: #E53935;">⚠️ 404 찾을 수 없음</h1>
                    <p style="font-size: 18px;">요청하신 경로 <b>{request.url.path}</b> 를 찾을 수 없습니다.</p>
                    <div style="background: #f5f5f5; padding: 20px; display: inline-block; border-radius: 10px; text-align: left;">
                        <p><b>현재 작동 중인 경로:</b></p>
                        <ul>
                            <li><a href="/">/ (메인 페이지)</a></li>
                            <li><a href="/health">/health (서버 상태 확인)</a></li>
                            <li><a href="/docs">/docs (API 문서)</a></li>
                        </ul>
                    </div>
                </body>
            </html>
            """,
            status_code=404
        )
    return await request.app.default_exception_handler(request, exc)
