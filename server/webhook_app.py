import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import db_manager as db
from logger import logger

# Routers
from routers.auth import router as auth_router
from routers.admin import router as admin_router
from routers.market import router as market_router
from routers.courier import router as courier_router
from routers.webhooks import router as webhooks_router
from routers.citizen import router as citizen_router
from routers.crm import router as crm_router
from routers.system import router as system_router
from routers.search import router as search_router
from routers.silver import router as silver_router
from routers.communication import router as communication_router
from routers.comm import router as comm_router
from dongne_biseo.router import router as dongne_biseo_router
from routers.settlement import router as settlement_router

load_dotenv()
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
from templates_config import templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

API_URL = os.getenv("API_URL", "https://dongnebiseo.com")

# ── CORS VIP 도메인 명단 (끝에 슬래시 금지) ──
origins = [
    "https://dongnebiseo.com",         # 일반 사용자·사장님 도메인
    "https://www.dongnebiseo.com",      # www 서브도메인
    "https://tantanfab.com",            # 탄탄제작소 어드민 (로그 위젯 embed)
    "https://www.tantanfab.com",        # tantanfab www
    "http://localhost:3000",            # 로컬 개발 (React/CRA)
    "http://localhost:5173",            # 로컬 개발 (Vite)
    "http://localhost:8000",            # 로컬 FastAPI 직접 테스트
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # 명시된 도메인만 허용 (*, 와일드카드 금지)
    allow_credentials=True,            # 쿠키·인증 토큰 전달 허용
    allow_methods=["*"],               # GET, POST, PUT, DELETE 등 전체 허용
    allow_headers=["*"],               # 커스텀 헤더(X-Admin-Token 등) 전달 허용
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Error | Path: {request.url.path} | {type(exc).__name__}: {exc}")
    if request.url.path.startswith("/api/"):
         return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Internal Server Error: {str(exc)}", "fallback": True}
         )
    return HTMLResponse(
        content=f"<html><body><h1>System Error</h1><p>{exc}</p><a href='/'>Go Home</a></body></html>",
        status_code=500
    )

from fastapi.responses import RedirectResponse
@app.get("/", response_class=HTMLResponse)
async def root_redirect(request: Request):
    import os
    api_url = os.getenv("API_URL", "https://dongnebiseo.com")
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "api_url": api_url
    })
from db_async import database

@app.on_event("startup")
async def startup_event():
    try:
        await database.connect()
        print("[-] Async DB Connected.")
    except Exception as e:
        print(f"[!] Async DB connection failed (non-fatal): {e}")
    print("[-] Checking DB Data on Startup...")
    try:
        try:
            db.init_db()
            print("[-] DB Tables Initialized.")
        except Exception as e:
            print(f"[!] Init DB Warning: {e}")
        
        store_id = "test_store"
        products = db.get_products(store_id)
        if hasattr(products, 'empty') and products.empty:
            try:
                db.save_user(store_id, "1234", "AI Store", "010-1234-5678")
                db.save_product(store_id, "맛있는 김치 10kg", 35000, "static/images/premium_kimchi.png", "김치")
                db.save_product(store_id, "유기농 쌀 20kg", 60000, "static/images/premium_rice.png", "쌀")
                db.save_order(store_id, "맛있는 김치 10kg", 35000, "홍길동", "010-1111-2222", "서울시", "문앞", "010-1111-2222")
                db.save_order(store_id, "유기농 쌀 20kg", 60000, "홍길동", "010-1111-2222", "서울시", "문앞", "010-1111-2222")
                print("[+] Mock Data Injected Successfully")
            except Exception as e:
                print(f"[!] Data Injection Check Failed: {e}")
    except Exception as e:
        print(f"[!] Startup Logic Error: {e}")

    # dongne_biseo callback_logs table init
    try:
        from dongne_biseo.database import init_callback_tables
        init_callback_tables()
    except Exception as e:
        print(f"[!] dongne_biseo init error: {e}")

    # 정산 테이블 초기화
    try:
        from settlement_db import init_settlement_tables
        init_settlement_tables()
    except Exception as e:
        logger.error(f"정산 테이블 초기화 실패: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await database.disconnect()
    print("[-] Async DB Disconnected.")

app.extra["WEBHOOK_TOKEN"] = os.environ.get("WEBHOOK_TOKEN", "")
app.extra["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "https://dongnebiseo.com")
app.extra["ADMIN_ALERT_PHONE"] = os.environ.get("ADMIN_ALERT_PHONE", "010-2384-7447")
app.extra["ENABLE_WEBHOOK_TEST_NOTIFY"] = os.environ.get("ENABLE_WEBHOOK_TEST_NOTIFY", "true")
app.extra["PAYMENT_WEBHOOK_SECRET"] = os.environ.get("PAYMENT_WEBHOOK_SECRET", "your_shared_secret_key")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(market_router)
app.include_router(courier_router)
app.include_router(webhooks_router)
app.include_router(citizen_router)
app.include_router(crm_router)
app.include_router(system_router)
app.include_router(search_router)
app.include_router(silver_router)
app.include_router(communication_router)
app.include_router(comm_router)
app.include_router(dongne_biseo_router)
app.include_router(settlement_router)
