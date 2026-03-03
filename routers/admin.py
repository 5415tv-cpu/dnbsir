from fastapi import APIRouter, Request, Form, Response, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
from typing import Union
import os
import openpyxl
import pandas as pd

import db_manager as db
from .auth import get_current_user, User
from fastapi import Cookie

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
API_URL = os.environ.get("API_URL", "")

@router.get("/admin/master", response_class=HTMLResponse)
async def master_dashboard(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    ADMIN_ACCOUNTS = ["master", "010-2384-7447", "01023847447"]
    
    if not cookie_store_id or cookie_store_id not in ADMIN_ACCOUNTS:
         return RedirectResponse(url="/admin?mode=login", status_code=303)

    try:
        total_sales = db.get_platform_orders(days=3650)
        revenue = sum([o['amount'] for o in total_sales])
        stores = db.get_all_stores()
        active_stores_count = len(stores)
        system_status = "Healthy"
        logs = db.get_sms_logs(limit=10)
    except Exception as e:
        print(f"Master Dashboard Error: {e}")
        revenue = 0
        active_stores_count = 0
        system_status = f"Error: {e}"
        logs = pd.DataFrame()
        stores = []

    return templates.TemplateResponse("master_dashboard.html", {
        "request": request,
        "revenue": revenue,
        "store_count": active_stores_count,
        "system_status": system_status,
        "logs": logs.to_dict('records') if hasattr(logs, 'to_dict') else [],
        "stores": stores,
        "api_url": API_URL,
        "kw": "admin1234"
    })

@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
        
    store = db.get_store(cookie_store_id)
    if not store:
        response = RedirectResponse(url="/admin?mode=login", status_code=303)
        response.delete_cookie("admin_session")
        return response

    if not store.get('user_role'):
        store['user_role'] = 'merchant'

    if not store.get("is_signed"):
        return RedirectResponse(url="/agreement", status_code=303)

    if not store.get("category"):
         return RedirectResponse(url="/select-role", status_code=303)
        
    now = datetime.now()
    current_month = now.month
    
    sales_stats = {"daily": [], "total_period": 0}
    products = []
    recent_orders = []
    top_products = []
    tax_est = {"vat": 0, "income_tax": 0, "total_sales": 0}
    customer_insight = {"rate": 0}
    net_profit = {"net_profit": 0, "fees": 0}

    try:
        sales_stats = db.get_sales_stats(store.get('store_id')) or sales_stats
        products = db.get_store_products(store.get('store_id')) or []
        recent_orders = db.get_store_orders(store.get('store_id')) or []
        top_products = db.get_top_products(store.get('store_id')) or []
        tax_est = db.get_tax_estimates(store.get('store_id')) or tax_est
        customer_insight = db.get_customer_revisit_rate(store.get('store_id')) or customer_insight
        net_profit = db.get_net_profit_analysis(store.get('store_id')) or net_profit
    except Exception as e:
        print(f"Dashboard Data Fetch Error: {e}")

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request, 
        "store": store, 
        "stats": {
            "revenue": sales_stats.get('total_period', 0),
            "margin": int(sales_stats.get('total_period', 0) * 0.1),
            "order_count": len(recent_orders)
        },
        "sales_chart_data": sales_stats.get('daily', []),
        "products": products,
        "recent_orders": recent_orders,
        "top_products": top_products,
        "current_month": current_month,
        "today_date": now.strftime("%Y년 %m월 %d일"),
        "api_url": API_URL,
        "tax": tax_est, 
        "insight": customer_insight,
        "profit": net_profit
    })

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, user: User = Depends(get_current_user)):
    if not user.is_signed:
        return RedirectResponse(url="/agreement")
    return templates.TemplateResponse("citizen_dashboard.html", {"request": request})

@router.get("/delivery-dashboard")
async def delivery_page(current_user: User = Depends(get_current_user)):
    check_user_role(current_user, "delivery")
    return {"message": "사장님 전용 데이터를 불러옵니다."}

@router.get("/admin/calculator", response_class=HTMLResponse)
async def calculator_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("calculator.html", {"request": request})

@router.get("/courier", response_class=HTMLResponse)
async def courier_page(request: Request, user: User = Depends(get_current_user)):
    if not user.is_signed:
        return RedirectResponse(url="/agreement")
    return templates.TemplateResponse("courier_form.html", {
        "request": request,
        "api_url": API_URL,
        "store": db.get_store(user.store_id)
    })

@router.get("/api/admin/report")
async def get_report(start: str, end: str, request: Request):
    store_id = "test_store"
    try:
        orders = db.get_store_orders(store_id, days=365)
        
        total_sales = 0
        for order in orders:
            # Check if order is dict or pandas series depending on get_store_orders implementation
            # Since get_store_orders previously returned DataFrame sometimes, let's treat order as dict
            amount = order.get('amount', 0) if isinstance(order, dict) else getattr(order, 'amount', 0)
            total_sales += amount
            
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

@router.get("/api/admin/download-tax-excel")
async def download_tax_excel(start: str, end: str):
    store_id = "test_store"
    data = db.get_tax_report_data(store_id, start, end) if hasattr(db, 'get_tax_report_data') else None
    
    if not data:
        data = {
            'total_sales': 0,
            'total_vat': 0,
            'total_fee': 0,
            'net_margin': 0
        }
        
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "세무 신고 자료"
    
    headers = ["기간", "총 매출(VAT포함)", "공급가액", "부가세", "카드수수료", "순마진"]
    ws.append(headers)
    
    row = [
        f"{start} ~ {end}",
        data['total_sales'],
        data['total_sales'] - data['total_vat'],
        data['total_vat'],
        data['total_fee'],
        data['net_margin']
    ]
    ws.append(row)
    
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)
        
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

@router.get("/admin/auto-reply", response_class=HTMLResponse)
async def auto_reply_page(request: Request):
    return templates.TemplateResponse("auto_reply_settings.html", {"request": request})

@router.get("/api/admin/auto-reply/settings")
async def get_auto_reply_settings():
    store_id = "test_store"
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

@router.post("/api/admin/auto-reply/settings")
async def save_auto_reply_settings(request: Request):
    data = await request.json()
    store_id = "test_store"
    
    msg = data.get("auto_reply_msg")
    missed = data.get("auto_reply_missed")
    end = data.get("auto_reply_end")
    
    refill_on = data.get("auto_refill_on", 0)
    refill_amount = data.get("auto_refill_amount", 50000)
    
    res = db.update_store_auto_reply(store_id, msg, missed, end, refill_on, refill_amount)
    if res:
        return {"success": True}
    else:
        return {"success": False, "error": "DB Update Failed"}

@router.get("/admin/store", response_class=HTMLResponse)
async def store_management_page(request: Request, user: User = Depends(get_current_user)):
    store = db.get_store(user.store_id)
    return templates.TemplateResponse("store_management.html", {"request": request, "store": store})

@router.post("/api/admin/store/update")
async def update_store_info(request: Request, user: User = Depends(get_current_user)):
    data = await request.json()
    store_id = user.store_id
    
    current_store = db.get_store(store_id)
    if not current_store:
        return {"success": False, "error": "Store not found"}
        
    current_store.update({
        "name": data.get("name"),
        "owner_name": data.get("owner_name"),
        "phone": data.get("phone"),
        "category": data.get("category"),
        "info": data.get("info"),
        "menu_text": data.get("menu_text")
    })
    
    res = db.save_store(store_id, current_store)
    
    if res:
        return {"success": True}
    else:
        return {"success": False, "error": "Update Failed"}

@router.post("/api/admin/wallet/charge")
async def charge_wallet(request: Request):
    data = await request.json()
    store_id = "test_store"
    
    amount = int(data.get("amount", 0))
    memo = data.get("memo", "충전")
    
    def calculate_bonus_points(recharge_amount: int):
        if recharge_amount >= 100000:
            bonus_rate = 0.10
        elif recharge_amount >= 50000:
            bonus_rate = 0.05
        elif recharge_amount >= 30000:
            bonus_rate = 0.03
        else:
            bonus_rate = 0.00
            
        return round(recharge_amount * bonus_rate)
    
    bonus = calculate_bonus_points(amount)
    new_balance = db.charge_wallet(store_id, amount, bonus, memo)
    
    if new_balance is not None:
        return {"success": True, "new_balance": new_balance, "bonus_applied": bonus}
    else:
        return {"success": False, "error": "Charge Failed"}

@router.post("/api/admin/products")
async def register_product(
    name: str = Form(...),
    price: int = Form(...),
    image: UploadFile = File(None)
):
    store_id = "test_store"
    
    store = db.get_store(store_id)
    if not store or store.get('wallet_balance', 0) < 100:
         return {"success": False, "error": "포인트가 부족합니다. 충전 후 이용해주세요."}

    image_path = ""
    if image:
        import shutil
        file_location = f"uploads/{image.filename}"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(image.file, file_object)
        image_path = file_location
    
    res = db.save_product(store_id, name, price, image_path)
    
    if res:
        print(f"Sending AlimTalk to customers: New Product {name} - {price} won")
        return {"success": True}
    else:
        return {"success": False, "error": "DB Save Failed"}

@router.delete("/api/admin/products/{product_id}")
async def delete_product_endpoint(product_id: str):
    store_id = "test_store" 
    res = db.delete_product(product_id, store_id)
    if res:
         return {"success": True}
    return {"success": False, "error": "Delete Failed"}

from pydantic import BaseModel

class OrderStatusUpdate(BaseModel):
    status: str

@router.post("/api/admin/orders/{order_id}/status")
async def update_order_status_endpoint(order_id: str, data: OrderStatusUpdate):
    res = db.update_order_status(order_id, data.status)
    if res:
        return {"success": True}
    return {"success": False, "error": "Update Failed"}

@router.get("/admin/farm/orders", response_class=HTMLResponse)
async def farm_order_page(request: Request):
    return templates.TemplateResponse("farm_order_dashboard.html", {"request": request})

@router.get("/api/admin/orders")
async def get_orders(type: str = "FARM"):
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

@router.get("/admin/tax", response_class=HTMLResponse)
async def tax_dashboard(request: Request):
    return templates.TemplateResponse("tax_dashboard.html", {"request": request})

@router.get("/api/admin/tax/stats")
async def get_tax_stats():
    store_id = "test_store" 
    stats = db.get_tax_stats(store_id)
    return stats

@router.get("/admin/expenses", response_class=HTMLResponse)
async def expenses_page(request: Request):
    return templates.TemplateResponse("expenses.html", {"request": request})

@router.get("/api/admin/expenses")
async def get_expenses():
    store_id = "test_store"
    df = db.get_monthly_expenses(store_id)
    if df.empty:
        db.save_expense(store_id, "삼성카드(4567)", "차량유지비", 450000, "2026-02-01")
        db.save_expense(store_id, "삼성카드(4567)", "지급수수료", 120000, "2026-02-05")
        df = db.get_monthly_expenses(store_id)
        
    if hasattr(df, 'to_dict'):
        return df.to_dict(orient="records")
    return []
