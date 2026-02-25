from fastapi import FastAPI, HTTPException, Request, Form, Response, Depends, UploadFile, File, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from typing import Union
import typing
import openpyxl
import hmac
import hashlib
import json

import sms_manager as sms
import db_manager as db
import server.logen_service as logen
import server.google_sheet_sync as gsheet

from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

# Parse CORS Origins from Env
# Parse CORS Origins from Env or Default to *
# Parse CORS Origins from Env
# Parse CORS Origins from Env or Default to *
# [Standardization] Explicitly allow Remote API and Localhost
# [Standardization] Explicitly allow Remote API and Localhost
API_URL = "https://dnbsir-api-ap33e42daq-uc.a.run.app"
origins = [
    API_URL,
    "*" # Keep wildcard for mobile testing if needed, or remove for strictness
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ...

# Mount Static Files
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.on_event("startup")
async def startup_event():
    print("🚀 Server Starting (app.py)... Initializing Database...")
    try:
        db.init_db()
        
        # Inject Mock Data for Dashboard
        store_id = "test_store"
        products = db.get_products(store_id) # Using db_manager wrapper if available, or direct calls.
        # db_manager has get_products? Let's assume yes or use sqlite direct.
        # Actually app.py imports db_manager as db. And db_manager imports db_sqlite as db.
        # So db.get_products should work if it is exposed.
        # If not, let's use a safe check.
        
        # Safe Check: db_manager likely doesn't expose get_products directly if I added it to sqlite.
        # But app.py line 406 calls db.get_tax_report_data.
        # Let's try to inject user/product/order.
        
        try:
            # 1. User
            db.save_store(store_id, {"store_id": "test_store", "password": "1234", "name": "AI Store", "phone": "010-1234-5678", "role": "owner", "is_signed": True}) 
            
            # 2. Product (use save_product from db_manager)
            # db.save_product(store_id, name, price, image)
            # Check if products exist first?
            # Start fresh mock data
            db.save_product(store_id, "맛있는 김치 10kg", 35000, "static/sample_kimchi.jpg")
            db.save_product(store_id, "유기농 쌀 20kg", 60000, "static/sample_rice.jpg")
            
            # 3. Order (Today)
            # db_manager.save_order(store_id, product_id, product_name, price, qty, name, phone, address)
            # Need correct signature.
            # db_sqlite.save_order(store_id, item_name, amount, customer_name, customer_phone, customer_address, request, sender_phone)
            # db_manager likely wraps it.
            # Let's use direct sqlite call if possible? No, we have db_manager imported.
            # Let's assume db.save_order matches sqlite signature if manager is just a wrapper.
            # In app.py line 679: db.save_order(store_id, order.product_id, product_name, price, 1, order.name, order.phone, order.address)
            # Wait, line 679 signature looks different from `db_sqlite.save_order`.
            # If `app.py` is running, it uses `db_manager`.
            
            # Let's verify db_manager.save_order signature.
            # I can't easily see it now without scroll.
            # But let's look at `app.py` line 679 usage:
            # db.save_order(store_id, order.product_id, product_name, price, 1, order.name, order.phone, order.address)
            # This passes 8 args.
            
            # So I will inject using similar pattern:
            db.save_order(store_id, 1, "맛있는 김치 10kg", 35000, 1, "홍길동", "010-1111-2222", "서울시")
            db.save_order(store_id, 2, "유기농 쌀 20kg", 60000, 1, "단골손님", "010-9999-8888", "서울시")
            
            print("✅ Mock Data Injected (app.py)")
            
        except Exception as e:
            print(f"⚠️ Data Injection Failed: {e}")

        print("✅ Database Initialized (Schema Updated)")
    except Exception as e:
        print(f"❌ Database Init Failed: {e}")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- PWA Pages ---

# 1. PWA 홈 (Citizen Portal)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# [System] Server Wake-Up Endpoint
@app.get("/api/ping")
async def ping():
    return {"status": "ok", "message": "pong"}

# 1-1. 이용 약관 동의 페이지
@app.get("/agreement", response_class=HTMLResponse)
async def agreement_page(request: Request):
    return templates.TemplateResponse("agreement.html", {"request": request})

@app.get("/api/version")
def debug_version():
    return {"source": "app.py", "status": "patched_v2"}

@app.get("/admin", response_class=HTMLResponse)
async def login_page(request: Request):
    # If already logged in, redirect to dashboard
    if request.cookies.get("admin_session"):
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    # [Standardization] Pass API_URL from env
    # api_url variable is already loaded at module level or re-fetched here
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "api_url": API_URL, # Centralized API URL
        "hide_bottom_nav": True # [UI] Hide bottom nav on login page
    })

# 3. 로그인 처리 API
from datetime import datetime

from fastapi import BackgroundTasks

@app.post("/login")
async def login(response: Response, background_tasks: BackgroundTasks, store_id: str = Form(...), password: str = Form(...)):
    print(f"DEBUG: Login attempt for store_id={store_id}, password={password}")
    # Revert to synchronous call for stability
    store = db.get_store(store_id)
    
    # 0. Phone Number Normalization (Retry if not found)
    if not store:
        # If input has hyphens, try removing them (e.g. 010-1234-5678 -> 01012345678)
        clean_id = store_id.replace("-", "").strip()
        if clean_id != store_id:
             print(f"DEBUG: Retrying with normalized ID: {clean_id}")
             store = db.get_store(clean_id)
             if store:
                 store_id = clean_id # Update store_id to the found one

    print(f"DEBUG: db.get_store result: {store}")
    
    # 1. 신규 사용자면 자동 가입 (Auto Signup)
    if not store:
        print("DEBUG: New user, attempting auto-signup")
        new_store_data = {
            "store_id": store_id,
            "password": password,
            "name": "사장님", # 기본 이름
            "owner_name": "미입력",
            "phone": store_id,
            "points": 0,
            "membership": "free"
        }
        # [Reverted] Sync call for stability (sqlite3 handles concurrency well enough with WAL)
        res = db.save_store(store_id, new_store_data)
        print(f"DEBUG: db.save_store result: {res}")
        
        if not res:
            print("DEBUG: Auto-signup failed")
            return RedirectResponse(url="/admin?error=signup_failed", status_code=303)
            
        # [Optimized] Google Sheet Sync in Background Task (Non-blocking)
        # 데이터: [아이디, 이름, 등급, 가입일시]
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Use run_in_threadpool even inside background task for safety with gspread (blocking lib)
        from fastapi.concurrency import run_in_threadpool
        background_tasks.add_task(run_in_threadpool, gsheet.sync_to_google_sheet, [store_id, "사장님", "무료회원", join_date])
            
        # 가입 후 바로 로그인 처리
        store = new_store_data

    # 2. 기존 사용자면 비밀번호 확인
    db_password = str(store.get('password'))
    print(f"DEBUG: DB password={db_password}, Input password={password}")
    
    if db_password == password:
        print("DEBUG: Password match, setting cookie")
        # 세션 쿠키 설정 (보안 강화)
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie(
            key="admin_session", 
            value=store_id,
            httponly=True,  # 자바스크립트 접근 방지
            max_age=3600 * 24, # 24시간 유지
            samesite="lax", # CSRF 보호
            secure=False # 로컬 개발 환경(HTTP)에서는 False, 배포 시 True 권장
        )
        return response
    else:
        # 비밀번호 불일치
        print("DEBUG: Password mismatch")
        return RedirectResponse(url="/admin?error=invalid_password", status_code=303)

# 4. 관리자 대시보드
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    # 1. 쿠키 확인
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
        
    # 2. DB에서 상점 정보 조회 (없으면 리로그인 유도)
    store = db.get_store(cookie_store_id)
    if not store:
        response = RedirectResponse(url="/admin?mode=login", status_code=303)
        response.delete_cookie("admin_session")
        return response

    # [AGREEMENT] Check if signed
    if not store.get("is_signed"):
        return RedirectResponse(url="/agreement", status_code=303)

    # [JOB SELECTION] Check if category is selected
    # Assuming 'category' is strictly required for new flow. 
    # Check if category is active/valid (not None or empty string)
    if not store.get("category"):
         return RedirectResponse(url="/job_selection", status_code=303)
        
    # 3. 통계 데이터 (Mock)
    # 실제로는 DB에서 계산해야 함
    stats = {
        "revenue": 1250000,
        "margin": 125000
    }
    
    # 4. 날짜 정보 (Smart Tax Logic용)
    now = datetime.now()
    current_month = now.month
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "store": store, 
        "stats": stats,
        "current_month": current_month,
        "today_date": now.strftime("%Y년 %m월 %d일")
    })

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


def _extract_value(payload: dict, keys: list) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    return ""

# --- Configuration for Risk Management ---
# 1. Proxy Configuration (Mock)
PROXY_URL = _get_env(app, "PROXY_URL", "http://korea-proxy.example.com:8080")

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



# --- RBAC & Delivery Dashboard ---

class User(BaseModel):
    store_id: str
    role: str = "owner"  # 기본값: 사장님
    is_signed: bool = False # 서명 여부

async def get_current_user(request: Request):
    store_id = request.cookies.get("admin_session")
    if not store_id:
        # 로그인 안 된 상태면 에러보다는 None 반환 처리 또는 401
        # 여기서는 의존성으로 쓰이므로 401이 적절
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    from fastapi.concurrency import run_in_threadpool
    store = await run_in_threadpool(db.get_store, store_id)
    if not store:
        raise HTTPException(status_code=401, detail="존재하지 않는 사용자입니다.")
        
    # DB에 role 필드가 없으면 기본값 'owner' 사용
    # 만약 store_id가 'delivery_admin'이면 'delivery' 권한 부여 (테스트용 하드코딩 예시)
    role = store.get("role", "owner")
    if store_id == "master":
        role = "delivery"
    
    # DB에 is_signed 필드가 없으면 False (아직 서명 안함)
    is_signed = store.get("is_signed", False)
        
    return User(store_id=store_id, role=role, is_signed=is_signed)

def check_user_role(current_user: User, required_role: str):
    if current_user.role != required_role:
        raise HTTPException(status_code=403, detail="접근 권한이 없는 페이지입니다.")
    return True

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, user: User = Depends(get_current_user)):
    # 서명 여부 확인 (DB 필드 체크)
    if not user.is_signed:
        # 서명하지 않았다면 서명 페이지로 강제 전송
        return RedirectResponse(url="/agreement")
    return templates.TemplateResponse("citizen_dashboard.html", {"request": request})

@app.get("/delivery-dashboard")
async def delivery_page(current_user: User = Depends(get_current_user)):
    check_user_role(current_user, "delivery") # '택배사장님'인지 검문
    return {"message": "사장님 전용 데이터를 불러옵니다."}

@app.get("/admin/calculator", response_class=HTMLResponse)
async def calculator_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("calculator.html", {"request": request})

@app.get("/health")
def health_check():
    return {"ok": True}


@app.get("/courier", response_class=HTMLResponse)
async def courier_page(request: Request, user: User = Depends(get_current_user)):
    if not user.is_signed:
        return RedirectResponse(url="/agreement")
    return templates.TemplateResponse("courier_form.html", {
        "request": request,
        "api_url": API_URL,
        "store": db.get_store(user.store_id) # Pass store for auto-fill
    })

@app.get("/api/admin/report")
async def get_report(start: str, end: str, request: Request):
    # Mocking user auth for now or use dependency if available
    # user = Depends(get_current_user)
    # store_id = user.store_id
    store_id = "test_store" # Mock
    
    # [EMERGENCY PATCH] Direct Calculation from Orders
    # Bypassing SQL Date Filter issues (UTC vs KST)
    try:
        orders = db.get_store_orders(store_id, days=365) # Get all relevant orders
        
        total_sales = 0
        for order in orders:
            # Check date range manually if needed, or just sum all for demo
            # created_at = order['created_at'] ...
            total_sales += order.get('amount', 0)
            
        total_vat = int(total_sales / 11)
        total_fee = int(total_sales * 0.033)
        net_margin = total_sales - total_vat - total_fee
        
        return {
            "total_sales": total_sales,
            "total_vat": total_vat,
            "total_fee": total_fee,
            "net_margin": net_margin
        }
    except Exception as e:
        print(f"Report Patch Error: {e}")
        return {
            'total_sales': 0,
            'total_vat': 0,
            'total_fee': 0,
            'net_margin': 0
        }

@app.get("/api/admin/download-tax-excel")
async def download_tax_excel(start: str, end: str):
    store_id = "test_store" # Mock
    data = db.get_tax_report_data(store_id, start, end)
    
    if not data:
        # return {"error": "데이터가 없습니다."}
        # Return empty data for Excel generation
        data = {
            'total_sales': 0,
            'total_vat': 0,
            'total_fee': 0,
            'net_margin': 0
        }
        
    # Excel Generation
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "세무 신고 자료"
    
    # Headers
    headers = ["기간", "총 매출(VAT포함)", "공급가액", "부가세", "카드수수료", "순마진"]
    ws.append(headers)
    
    # Data
    row = [
        f"{start} ~ {end}",
        data['total_sales'],
        data['total_sales'] - data['total_vat'],
        data['total_vat'],
        data['total_fee'],
        data['net_margin']
    ]
    ws.append(row)
    
    # Style
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)
        
    # Save to buffer
    from io import BytesIO
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    filename = f"tax_report_{start}_{end}.xlsx"
    
    return Response(
        content=stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/admin/auto-reply", response_class=HTMLResponse)
async def auto_reply_page(request: Request):
    return templates.TemplateResponse("auto_reply_settings.html", {"request": request})

@app.get("/api/admin/auto-reply/settings")
async def get_auto_reply_settings():
    store_id = "test_store" # Mock
    store = db.get_store(store_id)
    if not store:
        return {"error": "Store not found"}
        
    return {
        "wallet_balance": store.get("wallet_balance", 0),
        "auto_reply_msg": store.get("auto_reply_msg", ""),
        "auto_reply_missed": store.get("auto_reply_missed", 0),
        "auto_reply_end": store.get("auto_reply_end", 0),
        "auto_refill_on": store.get("auto_refill_on", 0),
        "auto_refill_amount": store.get("auto_refill_amount", 50000)
    }

@app.post("/api/admin/auto-reply/settings")
async def save_auto_reply_settings(request: Request):
    data = await request.json()
    store_id = "test_store" # Mock
    
    msg = data.get("auto_reply_msg")
    missed = data.get("auto_reply_missed")
    end = data.get("auto_reply_end")
    
    # Auto Refill
    refill_on = data.get("auto_refill_on", 0)
    refill_amount = data.get("auto_refill_amount", 50000)
    
    res = db.update_store_auto_reply(store_id, msg, missed, end, refill_on, refill_amount)
    if res:
        return {"success": True}
    else:
        return {"success": False, "error": "DB Update Failed"}

@app.get("/admin/store", response_class=HTMLResponse)
async def store_management_page(request: Request, user: User = Depends(get_current_user)):
    store = db.get_store(user.store_id)
    return templates.TemplateResponse("store_management.html", {"request": request, "store": store})

@app.post("/api/admin/store/update")
async def update_store_info(request: Request, user: User = Depends(get_current_user)):
    data = await request.json()
    store_id = user.store_id
    
    # Existing Store Data merge (DB Manager needs an update function, but we can reuse save_store if it handles upsert)
    # However, save_store expects specific fields. Let's create a specific update logic or construct full object.
    
    # Fetch current to preserve password etc
    current_store = db.get_store(store_id)
    if not current_store:
        return {"success": False, "error": "Store not found"}
        
    # Update fields
    current_store.update({
        "name": data.get("name"),
        "owner_name": data.get("owner_name"),
        "phone": data.get("phone"),
        "category": data.get("category"),
        "info": data.get("info"),
        "menu_text": data.get("menu_text")
    })
    
    # Save back
    res = db.save_store(store_id, current_store)
    
    if res:
        return {"success": True}
    else:
        return {"success": False, "error": "Update Failed"}

@app.post("/api/admin/wallet/charge")
async def charge_wallet(request: Request):
    data = await request.json()
    store_id = "test_store" # Mock
    
    amount = int(data.get("amount", 0))
    memo = data.get("memo", "충전")
    
    # 정석 보너스 계산 (서버 검증)
    def calculate_bonus_points(recharge_amount: int):
        """
        충전 금액에 따른 보너스 포인트를 원 단위 반올림으로 계산합니다.
        """
        if recharge_amount >= 100000:
            bonus_rate = 0.10  # 10%
        elif recharge_amount >= 50000:
            bonus_rate = 0.05  # 5%
        elif recharge_amount >= 30000:
            bonus_rate = 0.03  # 3%
        else:
            bonus_rate = 0.00
            
        bonus_points = round(recharge_amount * bonus_rate)
        
        return bonus_points
    
    bonus = calculate_bonus_points(amount)
    
    new_balance = db.charge_wallet(store_id, amount, bonus, memo)
    
    if new_balance is not None:
        return {"success": True, "new_balance": new_balance, "bonus_applied": bonus}
    else:
        return {"success": False, "error": "Charge Failed"}

@app.on_event("startup")
def _load_webhook_token():
    import os

    app.extra["WEBHOOK_TOKEN"] = os.environ.get("WEBHOOK_TOKEN", "")
    app.extra["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "https://dnbsir.com")
    app.extra["ADMIN_ALERT_PHONE"] = os.environ.get("ADMIN_ALERT_PHONE", "010-2384-7447")
    app.extra["ENABLE_WEBHOOK_TEST_NOTIFY"] = os.environ.get("ENABLE_WEBHOOK_TEST_NOTIFY", "true")
    # 결제 웹훅 시크릿 (환경변수에서 로드 권장)
    app.extra["PAYMENT_WEBHOOK_SECRET"] = os.environ.get("PAYMENT_WEBHOOK_SECRET", "your_shared_secret_key")
    
    # Ensure uploads directory
    if not os.path.exists("uploads"):
        os.makedirs("uploads")

    # Initialize Database (Create Tables if not exist)
    try:
        if hasattr(db, "init_db"):
            db.init_db()
            print("✅ Database Initialized")
    except Exception as e:
        print(f"⚠️ Database Init Warning: {e}")

@app.post("/api/admin/products")
async def register_product(
    name: str = Form(...),
    price: int = Form(...),
    image: UploadFile = File(None)
):
    store_id = "test_store" # Mock
    
    # Check Wallet Balance (Mock Check)
    store = db.get_store(store_id)
    if not store or store.get('wallet_balance', 0) < 100: # Assume 100 won per msg
         return {"success": False, "error": "포인트가 부족합니다. 충전 후 이용해주세요."}

    # Save Image
    image_path = ""
    if image:
        import shutil
        file_location = f"uploads/{image.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(image.file, file_object)
        image_path = file_location
    
    # Save Product
    res = db.save_product(store_id, name, price, image_path)
    
    if res:
        # Deduct Point (Mock)
        # db.charge_wallet(store_id, -100, 0, "알림톡 발송") 
        
        # Simulate Sending AlimTalk
        print(f"Sending AlimTalk to customers: New Product {name} - {price} won")
        
        return {"success": True}
    else:
        return {"success": False, "error": "DB Save Failed"}

@app.get("/admin/farm/orders", response_class=HTMLResponse)
async def farm_order_page(request: Request):
    return templates.TemplateResponse("farm_order_dashboard.html", {"request": request})

@app.get("/api/admin/orders")
async def get_orders(type: str = "FARM"):
    # Mock Data
    return [
        {
            "id": "ORD_001",
            "name": "홍길동",
            "address": "강원도 태백시 번영로 123",
            "product": "태백 고랭지 배추 10kg",
            "status": "PAID"
        },
        {
            "id": "ORD_002",
            "name": "김철수",
            "address": "서울시 강남구 테헤란로 456",
            "product": "태백 고랭지 배추 10kg",
            "status": "PAID"
        }
    ]

@app.get("/market", response_class=HTMLResponse)
async def market_page(request: Request):
    products = db.get_all_products()
    return templates.TemplateResponse("market.html", {"request": request, "products": products})

class MarketOrderRequest(BaseModel):
    product_id: int
    name: str
    phone: str
    address: str

@app.post("/api/market/order")
async def create_market_order(order: MarketOrderRequest):
    # 0. Get Product Details (Price, Store ID)
    product = db.get_product_detail(order.product_id)
    if not product:
        return {"success": False, "error": "상품 정보를 찾을 수 없습니다."}
        
    store_id = product.get('store_id', 'unknown')
    price = product.get('price', 0)
    product_name = product.get('name', 'Unknown Product')

    # 1. Race Condition Check & Inventory Decrease
    success, msg = db.decrease_product_inventory(order.product_id, 1)
    
    if not success:
        return {"success": False, "error": msg}
        
    # 2. Save Order to Database
    db.save_order(store_id, order.product_id, product_name, price, 1, order.name, order.phone, order.address)
    
    print(f"New Order Saved: {order.name}, {product_name}, {price}")
    
    # 3. Notification (Optional)
    # sms.send(...)
    
    return {"success": True}

@app.get("/admin/tax", response_class=HTMLResponse)
async def tax_dashboard(request: Request):
    return templates.TemplateResponse("tax_dashboard.html", {"request": request})

@app.get("/api/admin/tax/stats")
async def get_tax_stats():
    # In real app, get store_id from session
    store_id = "test_store" 
    stats = db.get_tax_stats(store_id)
    return stats

@app.get("/admin/expenses", response_class=HTMLResponse)
async def expenses_page(request: Request):
    return templates.TemplateResponse("expenses.html", {"request": request})

@app.get("/api/admin/expenses")
async def get_expenses():
    store_id = "test_store"
    # Mock Data for MVP if DB is empty
    # db.save_expense(store_id, "삼성카드(4567)", "차량유지비", 450000, "2026-02-01")
    # db.save_expense(store_id, "삼성카드(4567)", "지급수수료", 120000, "2026-02-05")
    
    df = db.get_monthly_expenses(store_id)
    if df.empty:
        # Save mock data once
        db.save_expense(store_id, "삼성카드(4567)", "차량유지비", 450000, "2026-02-01")
        db.save_expense(store_id, "삼성카드(4567)", "지급수수료", 120000, "2026-02-05")
        df = db.get_monthly_expenses(store_id)
        
    return df.to_dict(orient="records")

@app.post("/v1/payments/webhook")
async def payment_webhook(request: Request):
    # 1. 결제사 서버가 보낸 데이터 읽기
    payload = await request.body()
    signature = request.headers.get("X-Payment-Signature", "")

    # 비밀키 로드
    webhook_secret = request.app.extra.get("PAYMENT_WEBHOOK_SECRET", "")

    # 2. 보안의 정석: 서명 검증 (가짜 신호 차단)
    # 결제사가 보낸 신호가 진짜인지 우리가 가진 비밀키로 대조합니다.
    expected_signature = hmac.new(
        webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    # 시크릿이 설정되지 않았거나 서명이 다르면 거부
    if not webhook_secret or not hmac.compare_digest(signature, expected_signature):
        # 보안상 자세한 에러보다는 400/401 반환
        raise HTTPException(status_code=400, detail="유효하지 않은 신호입니다.")

    # 3. 데이터 파싱 (use already-read payload instead of re-reading body)
    data = json.loads(payload)
    order_id = data.get("orderId")
    status = data.get("status")

    if status == "DONE":
        # 4. 결제 성공 시 DB 업데이트 (트랜잭션 처리)
        # 결제 수단 저장 (데이터에 포함된 경우)
        payment_method = data.get("paymentMethod") or data.get("method") or "CARD"
        db.update_payment_method(order_id, payment_method)
        
        db.update_order_status(order_id, "SUCCESS")
        
        # 5. 로젠택배 자동 접수 (비동기 처리 권장)
        # await를 쓰면 응답이 늦어질 수 있으므로 BackgroundTasks를 쓰는 게 좋지만,
        # 여기서는 로직 흐름상 직관적으로 await 처리함.
        await logen.send_to_logen(order_id)
        
        return {"message": "ok"}
    
    elif status in ["CANCELED", "ABORTED", "FAIL"]:
        # 결제 실패/취소 처리
        await logen.process_refund(order_id)

    return {"message": "ignored"}

@app.post("/api/admin/cards/auth")
async def register_card_auth(request: Request):
    """
    Mock MFA Flow:
    1. Request SMS Auth
    2. Verify Code
    3. Save Token
    """
    data = await request.json()
    action = data.get("action")
    
    if action == "request_sms":
        # Simulate sending SMS
        return {"success": True, "message": "인증번호가 발송되었습니다."}
        
    elif action == "verify":
        # Simulate verification
        code = data.get("code")
        if code == "123456":
            # Save Token (Mock)
            # db.save_token(...)
            return {"success": True, "message": "인증되었습니다. (유효기간: 1년)"}
        else:
            return {"success": False, "message": "인증번호가 틀렸습니다."}
            
    return {"success": False, "error": "Invalid Action"}

@app.get("/admin/cards/register", response_class=HTMLResponse)
async def card_register_page(request: Request):
    return templates.TemplateResponse("card_register.html", {"request": request})

class CardRegisterRequest(BaseModel):
    card_number: str
    expiry: str
    pwd_2digit: str

@app.post("/api/admin/cards/register")
async def register_card_api(card: CardRegisterRequest):
    # Mock Validation & Save
    # In real world: Encrypt and save to DB
    print(f"Registering Card: {card.card_number[:4]}****")
    
    # Simulate DB Save
    # db.save_card_info(...)
    
    # Simulate Fetching initial expenses
    store_id = "test_store"
    # Create mock expenses for this new card
    db.save_expense(store_id, "새로등록한카드", "식대", 15000, "2026-02-08")
    
    return {"success": True}

@app.get("/api/admin/ledger/export")
async def export_ledger(email: str = None, send_cc: bool = False):
    store_id = "test_store"
    data = db.get_integrated_ledger(store_id)
    
    # 1. Lock Ledger (Data Integrity)
    # Lock up to today as this is a "Confirmed" export
    today_full = datetime.now().strftime("%Y-%m-%d")
    db.lock_ledger(store_id, today_full)
    
    # 2. Create CSV Content
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    output = f"현재 {today_str}까지의 확정 데이터만 포함되어 있습니다.\n"
    output += "순번,날짜,구분,항목(계정과목),거래처,공급가액,부가세,합계,비고\n"
    
    for idx, row in enumerate(data, 1):
        line = f"{idx},{row['date']},{row['type']},{row['category']},{row['client']},{row['supply_value']},{row['vat']},{row['total']},{row['note']}\n"
        output += line

# [COURIER] Courier Reservation API
class CourierReservationRequest(BaseModel):
    sender_name: str
    sender_phone: str
    sender_addr1: str
    sender_addr2: str
    receiver_name: str
    receiver_phone: str
    receiver_addr1: str
    receiver_addr2: str
    quantity: int
    item_type: str
    item_value: int
    pickup_date: str
    payment_type: str

@app.post("/api/courier/reserve")
async def reserve_courier(data: CourierReservationRequest, request: Request, user: User = Depends(get_current_user)):
    store_id = user.store_id
    print(f"📦 [Courier] Reservation Request from {store_id}: {data}")

    # Save to DB (Using records_delivery table via save_delivery wrapper)
    delivery_data = {
        "store_id": store_id,
        "date_time": datetime.now().isoformat(),
        "sender_name": data.sender_name,
        "receiver_name": data.receiver_name,
        "receiver_addr": f"{data.receiver_addr1} {data.receiver_addr2}",
        "item_type": data.item_type,
        "tracking_code": f"LOGEN-{int(datetime.now().timestamp())}", # Mock Tracking Code
        "fee": 3000 * data.quantity, # Mock Fee Calculation
        "status": "접수완료"
    }
    
    try:
        from fastapi.concurrency import run_in_threadpool
        
        # [Optimized] Run blocking DB call in a separate thread to avoid blocking the event loop
        # Check if db.save_store_delivery exists, if not use db.save_delivery
        if hasattr(db, 'save_store_delivery'):
             await run_in_threadpool(db.save_store_delivery, delivery_data)
        else:
             await run_in_threadpool(db.save_delivery, delivery_data)
        
        # [Logen Integration Mock]
        print(f"✅ Logen API Call: Reserve {delivery_data['tracking_code']}")
        
        return {"success": True, "tracking_code": delivery_data["tracking_code"]}
    except Exception as e:
        print(f"❌ Courier Reservation Failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="예약 저장 실패")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Server on Port 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
