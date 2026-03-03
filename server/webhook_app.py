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

load_dotenv()
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

API_URL = os.getenv("API_URL", "https://dnbsir-api-ap33e42daq-uc.a.run.app")
origins = ["http://localhost:8080", "http://127.0.0.1:8080", API_URL, "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[!] Global Error: {exc} (Path: {request.url.path})")
    if request.url.path.startswith("/api/"):
         return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Internal Server Error: {str(exc)}", "fallback": True}
         )
    return HTMLResponse(
        content=f"<html><body><h1>System Error</h1><p>{exc}</p><a href='/'>Go Home</a></body></html>",
        status_code=500
    )

@app.on_event("startup")
async def startup_event():
    print("[-] Checking DB Data on Startup...")
    try:
        try:
            db.init_db()
            print("[-] DB Tables Initialized.")
        except Exception as e:
            print(f"[!] Init DB Warning: {e}")
        
        store_id = "test_store"
        products = db.get_products(store_id)
        if not products:
            try:
                db.save_user(store_id, "1234", "AI Store", "010-1234-5678")
                db.save_product(store_id, "맛있는 김치 10kg", 35000, "static/sample_kimchi.jpg", "김치")
                db.save_product(store_id, "유기농 쌀 20kg", 60000, "static/sample_rice.jpg", "쌀")
                db.save_order(store_id, "맛있는 김치 10kg", 35000, "홍길동", "010-1111-2222", "서울시", "문앞", "010-1111-2222")
                db.save_order(store_id, "유기농 쌀 20kg", 60000, "홍길동", "010-1111-2222", "서울시", "문앞", "010-1111-2222")
                print("[+] Mock Data Injected Successfully")
            except Exception as e:
                print(f"[!] Data Injection Check Failed: {e}")
    except Exception as e:
        print(f"[!] Startup Logic Error: {e}")

app.extra["WEBHOOK_TOKEN"] = os.environ.get("WEBHOOK_TOKEN", "")
app.extra["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "https://dnbsir.com")
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
