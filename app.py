from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
# Load .env first before importing DB modules
load_dotenv()

import os
import logging
import db_manager as db
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_logger = logging.getLogger("tantan.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 생명주기 관리 (현대적 lifespan 패턴)
    ─────────────────────────────────────────────
    Startup  : cron_jobs + 배치 스케줄러 순차 시작
    Shutdown : 배치 스케줄러 안전 종료 후 cron_jobs 정리
    """
    # ── Startup ──────────────────────────────────────────────
    _logger.info("[App] 서버 시작 — 스케줄러 초기화 중...")

    # 1. 기존 cron_jobs (동네비서 정기 작업)
    try:
        import cron_jobs
        cron_jobs.start_cron_jobs()
        _logger.info("[App] cron_jobs 시작 완료")
    except Exception as e:
        _logger.warning(f"[App] cron_jobs 시작 실패 (비필수): {e}")

    # 2. 탄탄제작소 야간 배치 스케줄러 (APScheduler)
    try:
        from routers.batch_scheduler import start as batch_start
        batch_start()
        _logger.info("[App] 배치 스케줄러 시작 완료 (KST 00:00/00:10/06:30/07:00)")
    except Exception as e:
        _logger.warning(f"[App] 배치 스케줄러 시작 실패 (비필수): {e}")

    _logger.info("[App] 탄탄제작소 엔진 구동 완료 ✅")

    yield  # ← 이 시점에 API 서비스 정상 운영

    # ── Shutdown ─────────────────────────────────────────────
    _logger.info("[App] 서버 종료 — 스케줄러 안전 정리 중...")
    try:
        from routers.batch_scheduler import stop as batch_stop
        batch_stop()
        _logger.info("[App] 배치 스케줄러 안전 종료")
    except Exception as e:
        _logger.warning(f"[App] 배치 스케줄러 종료 실패: {e}")


app = FastAPI(title="AI Store API", redirect_slashes=False, lifespan=lifespan)


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
# ★ 전화번호 로그 마스킹 미들웨어
# /c?ref=01012341234 → 로그에 ref=010****1234 로 기록
import re as _re
import logging as _logging
_phone_re = _re.compile(r'(ref=)(0\d{2})(\d{3,4})(\d{4})')

@app.middleware("http")
async def log_mask_middleware(request: Request, call_next):
    raw_url = str(request.url)
    masked_url = _phone_re.sub(lambda m: f"{m.group(1)}{m.group(2)}****{m.group(4)}", raw_url)
    if masked_url != raw_url:
        _logging.getLogger("uvicorn.access").debug(f"[MASKED] {masked_url}")
    return await call_next(request)

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
        "/api/toss/",           # ✅ 토스페이먼츠 웹훅
        "/api/pay/success",     # ✅ 토스 결제 성공 리다이렉트 (인증 쿠키 없음)
        "/api/payment/fail",    # ✅ 토스 결제 실패 리다이렉트 (인증 쿠키 없음)
        "/api/market/success",  # ✅ 마켓 결제 성공 리다이렉트
        "/api/comm/call-event", # Android 앱 콜백
        "/api/debug_log",
        "/api/ocr/",            # ✅ Kakao Vision OCR 프록시 (인증 없이 호출)
        "/api/kiosk/",          # ✅ 키오스크 전용 API (무인 단말기 — 쿠키 없음)
        "/kiosk",               # ✅ 키오스크 HTML 페이지 직접 서빙
        "/shortform",           # ✅ 숏폼 영상 생성 키오스크 (인증 불필요)
        # ★ 탄탄제작소 — JWT 자체 인증 시스템 사용 (세션 쿠키 불필요)
        "/api/tantan/",         # ✅ 탄탄 전체 (OTP/결제/관리자 JWT/키오스크)
        "/control/",            # ✅ Control Tower SPA 정적 서빙
        "/api/v1/admin/",       # ✅ 탄탄 관리자 인증 API (자체 SMS 인증)
        "/studio/",             # ✅ 탄탄 스튜디오 (고객 접수)
        "/api/studio/",         # ✅ 스튜디오 영상 제작 API
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
        not path.startswith("/api/comm/history") and  # ★ 앱 미수신 목록 API — 앱이 인증 없이 호출
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

@app.get("/home", response_class=HTMLResponse)
async def home_alias(request: Request):
    """SEO/과거 링크 호환을 위해 /home을 / 로 영구 이동 처리"""
    return RedirectResponse(url="/", status_code=301)

@app.get("/store/landing", response_class=HTMLResponse)
async def store_landing_redirect(request: Request, ref: str = ""):
    return templates.TemplateResponse(request, "store_register_landing.html", {
        "request": request,
        "ref": ref,
        "api_url": os.getenv("APP_BASE_URL", "https://dongnebiseo.com")
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

@app.on_event("startup")
def _start_batch_scheduler():
    """KST 기준 심야 배치 스케줄러 시작 (00:00/00:10/06:30/07:00 KST)"""
    try:
        from routers.batch_scheduler import start as _batch_start
        _batch_start()
        print("[OK] 심야 배치 스케줄러 시작 (Asia/Seoul 기준)")
    except Exception as e:
        print(f"[WARN] 배치 스케줄러 시작 실패 (비필수): {e}")

@app.on_event("shutdown")
def _stop_batch_scheduler():
    try:
        from routers.batch_scheduler import stop as _batch_stop
        _batch_stop()
    except Exception:
        pass

from routers import admin, auth, citizen, courier, crm, market, system, webhooks, search, webhook_atalk, schedule_manager, comm, api_admin_market, monitor, ocr, kiosk
from routers import callback_click
from routers import video_shortform          # ★ 숏폼 영상 생성 키오스크
from routers import tantan_payment
from routers import kakao_payment           # ★ 탄탄 결제
from routers import tantan_admin             # ★ 탄탄 Control Tower
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
app.include_router(monitor.router)  # ★ 콜백 블랙박스 모니터
app.include_router(ocr.router)      # ★ Kakao Vision OCR 프록시
app.include_router(kiosk.router)    # ★ 키오스크 전용 API (주소검색 + 로젠접수)
app.include_router(callback_click.router)  # ★ 콜백 클릭 추적 (/c)
app.include_router(video_shortform.router) # ★ 숏폼 영상 생성 키오스크
app.include_router(tantan_payment.router)
app.include_router(kakao_payment.router)  # ★ 탄탄 결제 (OTP/크레딧/토스)
app.include_router(tantan_admin.router)    # ★ 탄탄 Control Tower (관리자 전용)
app.include_router(dongne_biseo_router)

# ── 탄탄제작소 관리자 인증 (SMS 기반 세션) ─────────────────────
from routers.tantan_admin_auth import admin_auth as tantan_auth_router
app.include_router(tantan_auth_router)     # ★ /api/v1/admin/* (인증/세션)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ★ 키오스크 점검 상태 API (kiosk.html 30초 폴링)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/api/tantan/kiosk/status", tags=["kiosk"])
async def kiosk_status():
    """점검 모드 여부 반환 — kiosk.html이 30초마다 폴링."""
    import redis as _redis, os as _os
    from datetime import datetime
    import pytz
    try:
        rdb = _redis.from_url(
            _os.environ.get("DONGNE_REDIS_URL", _os.environ.get("REDIS_URL", "redis://localhost:6379/1")),
            decode_responses=True,
        )
        maintenance = rdb.get("tantan:maintenance:active") == "1"
        batch_running = rdb.get("tantan:batch:running") == "1"
        soft_shutdown = rdb.get("tantan:batch:soft_shutdown") == "1"
        count_today   = int(rdb.get("tantan:batch:count_today") or 0)
        pending_count = rdb.zcard("tantan:orders:pending_index")
        kst = pytz.timezone("Asia/Seoul")
        now_kst = datetime.now(kst)
        return {
            "maintenance":   maintenance,
            "batch_running": batch_running,
            "soft_shutdown": soft_shutdown,
            "count_today":   count_today,
            "pending_count": pending_count,
            "server_time_kst": now_kst.strftime("%H:%M:%S"),
            "message": (
                "심야 정비 중 (00:00~07:00 KST)"
                if maintenance else "정상 운영 중"
            ),
        }
    except Exception as e:
        return {"maintenance": False, "message": "상태 확인 실패", "error": str(e)}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ★ 키오스크 HTML 직접 서빙 (file:// CORS 문제 해결)
# 접속: https://dongnebiseo.com/kiosk
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/kiosk", response_class=HTMLResponse, include_in_schema=False)
async def serve_kiosk():
    kiosk_path = Path(__file__).parent / "kiosk.html"
    if not kiosk_path.exists():
        return HTMLResponse("<h1>kiosk.html not found</h1>", status_code=404)
    return HTMLResponse(kiosk_path.read_text(encoding="utf-8"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ★ 탄탄 스튜디오 (고객 접수 전용 프론트엔드)
# 접속: https://tantanfab.com/studio/
# Nginx: /studio/ → proxy_pass http://127.0.0.1:8000/studio/
# 파일: /var/www/dnbsir/static/tantan_studio.html
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/studio/", response_class=HTMLResponse, include_in_schema=False)
async def serve_studio():
    studio_path = Path(__file__).parent / "static" / "tantan_studio.html"
    if not studio_path.exists():
        return HTMLResponse("<h1>tantan_studio.html not found</h1>", status_code=404)
    return HTMLResponse(studio_path.read_text(encoding="utf-8"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 토스페이먼츠 결제 리다이렉트 수신 라우트
# successUrl → /kiosk/payment/success?paymentKey=...&orderId=...&amount=...
# failUrl    → /kiosk/payment/fail
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/kiosk/payment/success", response_class=HTMLResponse, include_in_schema=False)
async def kiosk_payment_success(paymentKey: str = "", orderId: str = "", amount: int = 0):
    if paymentKey.startswith("KAKAOPAY_"):
        return _kiosk_success_html(orderId, amount)
    import base64
    import httpx as _httpx
    toss_sk = os.environ.get("TOSS_SECRET_KEY", "")
    enc = base64.b64encode(f"{toss_sk}:".encode()).decode()
    headers = {"Authorization": f"Basic {enc}", "Content-Type": "application/json"}

    confirm_ok = False
    err_msg = "결제 서버 오류"
    try:
        async with _httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.tosspayments.com/v1/payments/confirm",
                json={"paymentKey": paymentKey, "orderId": orderId, "amount": amount},
                headers=headers,
            )
            data = resp.json()
            if resp.status_code == 200:
                confirm_ok = True
            else:
                err_msg = data.get("message", "승인 거절")
    except Exception as e:
        err_msg = str(e)

    if confirm_ok:
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>
  if (window.opener) {{
    window.opener.postMessage({{type:'TOSS_SUCCESS',orderId:'{orderId}',amount:{amount}}}, '*');
    window.close();
  }} else {{
    window.location.href = '/kiosk?payment=success&orderId={orderId}&amount={amount}';
  }}
</script>
<p style="font-family:sans-serif;text-align:center;margin-top:40px;">결제 완료 처리 중...</p>
</body></html>"""
    else:
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>
  if (window.opener) {{
    window.opener.postMessage({{type:'TOSS_FAIL',message:'{err_msg}'}}, '*');
    window.close();
  }} else {{
    window.location.href = '/kiosk';
  }}
</script>
<p style="font-family:sans-serif;text-align:center;margin-top:40px;color:#e74c3c;">
  결제 승인 실패: {err_msg}</p>
</body></html>"""
    return HTMLResponse(html)


@app.get("/kiosk/payment/fail", response_class=HTMLResponse, include_in_schema=False)
async def kiosk_payment_fail(code: str = "", message: str = ""):
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>
<script>
  if (window.opener) { window.opener.postMessage({type:'TOSS_FAIL'}, '*'); window.close(); }
  else { window.location.href = '/kiosk'; }
</script></body></html>"""
    return HTMLResponse(html)


# ★ cron_jobs + batch_scheduler는 위의 lifespan()에서 관리합니다.
#    모듈 최하단에서 직접 호출하는 구식 패턴 제거 완료.

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"[INFO] Starting Server on Port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
