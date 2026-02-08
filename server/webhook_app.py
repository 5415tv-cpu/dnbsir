from fastapi import FastAPI, HTTPException, Request, Form, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
import typing

import sms_manager as sms
import db_manager as db
import pydantic

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

# 1-1. 이용 약관 동의 페이지
@app.get("/agreement", response_class=HTMLResponse)
async def agreement_page(request: Request):
    return templates.TemplateResponse("agreement.html", {"request": request})

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
        
    stats = db.get_today_stats(store_id)
    
    return templates.TemplateResponse("dashboard.html", {"request": request, "store": store, "stats": stats})

# 5. 로그아웃
@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/admin", status_code=303)
    response.delete_cookie("admin_session")
    return response

# 2. 기존에 잘 작동하던 /docs 기능은 그대로 유지됩니다.



class OrderRequest(BaseModel):
    name: str          # "홍길동"
    phone: str         # "01012345678" (문자로 해야 0이 안 잘림)
    address: str       # "태백시 황지동..."
    order_item: str    # "사과 1박스" (숫자 1도 문자로 취급)
    price: str         # "30000" (계산이 필요 없을 땐 문자가 안전)


class MissedCallWebhook(BaseModel):
    virtual_number: str
    caller_phone: str
    store_id: str | None = None
    store_name: str | None = None
    order_link: str | None = None


def _get_env(app_: FastAPI, key: str, default: str = "") -> str:
    return app_.extra.get(key, default)


    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    return ""

# --- Configuration for Risk Management ---
# 1. Proxy Configuration (Mock)
PROXY_URL = _get_env(app, "PROXY_URL", "http://korea-proxy.example.com:8080")

# 2. MFA Session Manager (Mock)
def get_card_session(store_id, card_name):
    # In real world: db.get_active_token(store_id, card_name)
    return "valid_token_example"


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
    
    store = db.get_store(store_id)
    if not store:
        raise HTTPException(status_code=401, detail="존재하지 않는 사용자입니다.")
        
    # DB에 role 필드가 없으면 기본값 'owner' 사용
    # 만약 store_id가 'delivery_admin'이면 'delivery' 권한 부여 (테스트용 하드코딩 예시)
    role = store.get("role", "owner")
    if store_id == "delivery_master":
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
    return templates.TemplateResponse("courier_form.html", {"request": request})

@app.get("/api/admin/report")
async def get_report(start: str, end: str, request: Request):
    # Mocking user auth for now or use dependency if available
    # user = Depends(get_current_user)
    # store_id = user.store_id
    store_id = "test_store" # Mock
    
    data = db.get_tax_report_data(store_id, start, end)
    if not data:
        return {"error": "데이터가 없습니다."}
    return data

@app.get("/api/admin/download-tax-excel")
async def download_tax_excel(start: str, end: str):
    store_id = "test_store" # Mock
    data = db.get_tax_report_data(store_id, start, end)
    
    if not data:
        return {"error": "데이터가 없습니다."}
        
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

from fastapi import UploadFile, File, Form

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

import hmac
import hashlib
import server.logen_service as logen
import sms_manager as sms

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

    # 3. 데이터 파싱
    data = await request.json()
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
    import random
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
        
    # 3. ZIP Compression (Large File Handling)
    import io
    import zipfile
    
    zip_buffer = io.BytesIO()
    file_name = f"{store_id}_integrated_ledger_{today_full}.csv"
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(file_name, output.encode('utf-8-sig')) # utf-8-sig for Excel
        
    zip_buffer.seek(0)
    
    # 4. Email Simulation (Risk Management)
    if email:
        print(f"📧 [EMAIL SENT] To: {email} | Subject: {today_str} 세무 자료 | Attachment: {file_name}.zip")
        if send_cc:
             print(f"📧 [EMAIL CC] To: Owner (CC) | Backup Record Saved")

    # Return as downloadable ZIP file
    from starlette.responses import Response
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=tax_data_{today_full}.zip"}
    )

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
