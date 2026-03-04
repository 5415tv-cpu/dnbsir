from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv
import os
import db_manager as db

# Load .env
load_dotenv()

app = FastAPI(title="AI Store API")

API_URL = os.environ.get("API_URL", "https://dnbsir-api-ap33e42daq-uc.a.run.app")
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

# Mount Static Files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.on_event("startup")
async def startup_event():
    print("🚀 Server Starting (app.py)... Initializing Database...")
    try:
        if hasattr(db, "init_db"):
            db.init_db()
        
        # Inject Mock Data for Dashboard
        store_id = "test_store"
        try:
            db.save_store(store_id, {"store_id": "test_store", "password": "1234", "name": "AI Store", "phone": "010-1234-5678", "role": "owner", "is_signed": True}) 
            db.save_product(store_id, "맛있는 김치 10kg", 35000, "static/sample_kimchi.jpg")
            db.save_product(store_id, "유기농 쌀 20kg", 60000, "static/sample_rice.jpg")
            db.save_order(store_id, 1, "맛있는 김치 10kg", 35000, 1, "홍길동", "010-1111-2222", "서울시")
            db.save_order(store_id, 2, "유기농 쌀 20kg", 60000, 1, "단골손님", "010-9999-8888", "서울시")
            print("✅ Mock Data Injected (app.py)")
        except Exception as e:
            print(f"⚠️ Data Injection Failed: {e}")

        print("✅ Database Initialized (Schema Updated)")
    except Exception as e:
        print(f"❌ Database Init Failed: {e}")

@app.on_event("startup")
def _load_webhook_token():
    app.extra["WEBHOOK_TOKEN"] = os.environ.get("WEBHOOK_TOKEN", "")
    app.extra["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "https://dnbsir.com")
    app.extra["ADMIN_ALERT_PHONE"] = os.environ.get("ADMIN_ALERT_PHONE", "010-2384-7447")
    app.extra["ENABLE_WEBHOOK_TEST_NOTIFY"] = os.environ.get("ENABLE_WEBHOOK_TEST_NOTIFY", "true")
    app.extra["PAYMENT_WEBHOOK_SECRET"] = os.environ.get("PAYMENT_WEBHOOK_SECRET", "your_shared_secret_key")
    
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

from routers import admin, auth, citizen, courier, crm, market, system, webhooks, search, silver

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(citizen.router)
app.include_router(courier.router)
app.include_router(crm.router)
app.include_router(market.router)
app.include_router(system.router)
app.include_router(webhooks.router)
app.include_router(search.router)
app.include_router(silver.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting Server on Port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
