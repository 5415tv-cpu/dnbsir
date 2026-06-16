from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv
# Load .env first before importing DB modules
load_dotenv()

import os
import db_manager as db
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="AI Store API", redirect_slashes=False)


API_URL = os.environ.get("API_URL", "https://dongnebiseo.com")
origins = [
    API_URL,
    "*" # Keep wildcard for mobile testing if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# 🔒 전역 인증 방어벽 (Auth Guard Middleware)
# 모든 요청이 라우터에 도달하기 전에 여기서 걸러집니다.
# ──────────────────────────────────────────────
@app.middleware("http")
async def auth_guard(request: Request, call_next):
    path = request.url.path

    # 공개 허용 경로 (로그인 페이지 자체, 정적 파일 등)
    PUBLIC_PREFIXES = [
        "/static", "/favicon.ico",
        "/admin/login", "/admin/register",
        "/auth/", "/store/landing",
        "/citizen", "/subsidy", "/support",
        "/api/auth/",           # 로그인 API 자체는 열어둠
        "/api/public/",         # ✅ 미가입자용 무료 공개 API
        "/api/webhook",         # 외부 웹훅 수신
        "/api/comm/call-event", # Android 앱 콜백
        "/api/debug_log",
    ]
    # /admin 이지만 쿼리에 mode=login 이 있으면 허용 (로그인 폼 진입)
    query = str(request.url.query)
    is_login_form = path == "/admin" and "mode=login" in query

    if is_login_form or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)

    # 보호 대상 경로 판별
    is_admin_page = path.startswith("/admin")
    is_protected_api = (
        path.startswith("/api/") and
        not path.startswith("/api/public/") and   # 공개 API 제외
        not path.startswith("/api/auth/") and     # 인증 API 제외
        not path.startswith("/api/webhook") and   # 웹훅 제외
        not path.startswith("/api/comm/call-event") and
        not path.startswith("/api/debug_log")
    )

    if is_admin_page or is_protected_api:
        has_session = request.cookies.get("admin_session")

        if not has_session:
            if is_admin_page:
                # 화면 접근 → 로그인 폼으로 리다이렉트
                return RedirectResponse(url="/admin?mode=login", status_code=303)
            else:
                # API 접근 → 401 JSON 반환
                return JSONResponse(
                    status_code=401,
                    content={"error": "인증 만료", "detail": "로그인이 필요합니다."}
                )

    return await call_next(request)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=401, content={"detail": exc.detail})
        
        response = RedirectResponse(url="/store/landing", status_code=303)
        response.delete_cookie("admin_session")
        return response
    
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/", response_class=HTMLResponse)
async def root_redirect(request: Request):
    import os
    cookie_store_id = request.cookies.get("admin_session")
    if cookie_store_id:
        store = db.get_store(cookie_store_id)
        if store:
            role = store.get("role") or store.get("user_role") or "owner"
            if role == "citizen":
                return RedirectResponse(url="/dashboard", status_code=303)
            elif role == "farmer":
                return RedirectResponse(url="/admin/dashboard?mode=farmer", status_code=303)
            else:
                return RedirectResponse(url="/admin/dashboard", status_code=303)

    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "toss_client_key": toss_client_key
    })

@app.get("/store/landing", response_class=HTMLResponse)
async def store_landing_redirect(request: Request):
    return templates.TemplateResponse(request, "store_register_landing.html", {
        "request": request
    })

@app.get("/citizen/home", response_class=HTMLResponse)
async def citizen_home_redirect(request: Request):
    return templates.TemplateResponse(request, "citizen_home.html", {
        "request": request
    })

# Mount Static Files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
from templates_config import templates

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(str(BASE_DIR / "static" / "favicon.ico"))

@app.on_event("startup")
async def startup_event():
    print("[INFO] Server Starting (app.py)... Initializing Database...")
    try:
        # 1. 중앙 통제소(db_backend.py)를 통한 안전한 초기화
        import db_backend as db
        
        # SQLite 환경일 경우 비동기(async) 초기화가 아닐 수 있으므로 검사 후 실행
        if hasattr(db, "init_db"):
            if callable(db.init_db):
                import asyncio
                if asyncio.iscoroutinefunction(db.init_db):
                    await db.init_db()
                else:
                    db.init_db()

        # 2. 강제 하드코딩된 Mock 데이터 주입 로직 제거 (위험 요인 제거)
        # 로컬 테스트용 데이터는 앱 구동 후 회원가입 화면이나 관리자 화면에서 직접 입력하는 것이 안전합니다.
        print("[OK] Database Connection Verified (Data injection skipped)")

        # 3. 콜백 테이블 초기화 우회 경로 차단 (중앙 통제소 의존)
        # 만약 dongne_biseo.database 모듈이 반드시 필요하다면, 
        # 이 역시 db_backend.py 내부로 옮겨서 스위칭의 통제를 받게 해야 합니다.
        # 현재는 로컬 테스트 충돌을 막기 위해 안전하게 건너뜁니다.
        print("[OK] Callback Tables Initialization Deferred (Managed by db_backend)")

    except Exception as e:
        print(f"[ERROR] Database Init Failed (Safe Mode Engaged): {e}")

@app.on_event("startup")
def _load_webhook_token():
    app.extra["WEBHOOK_TOKEN"] = os.environ.get("WEBHOOK_TOKEN", "")
    app.extra["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "https://dongnebiseo.com")
    app.extra["ADMIN_ALERT_PHONE"] = os.environ.get("ADMIN_ALERT_PHONE", "010-2384-7447")
    app.extra["ENABLE_WEBHOOK_TEST_NOTIFY"] = os.environ.get("ENABLE_WEBHOOK_TEST_NOTIFY", "true")
    app.extra["PAYMENT_WEBHOOK_SECRET"] = os.environ.get("PAYMENT_WEBHOOK_SECRET", "your_shared_secret_key")
    
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

from routers import admin, auth, citizen, courier, crm, market, system, webhooks, search, webhook_atalk, schedule_manager, comm, api_admin_market
from dongne_biseo.router import router as dongne_biseo_router

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(citizen.router)
app.include_router(courier.router)
app.include_router(crm.router)
app.include_router(market.router)
app.include_router(system.router)
app.include_router(webhooks.router)
app.include_router(search.router)
app.include_router(webhook_atalk.router)
app.include_router(schedule_manager.router)
app.include_router(comm.router)
app.include_router(api_admin_market.router)
app.include_router(dongne_biseo_router)

import cron_jobs
cron_jobs.start_cron_jobs()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"[INFO] Starting Server on Port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
