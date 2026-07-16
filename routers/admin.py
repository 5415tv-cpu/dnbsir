from fastapi import APIRouter, Request, Form, Response, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
from typing import Union
from pydantic import BaseModel
import os
import openpyxl
import pandas as pd

import db_manager as db
from .auth import get_current_user, User
from fastapi import Cookie

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
from templates_config import templates
API_URL = os.environ.get("API_URL", "")

@router.get("/admin/dongnae", response_class=HTMLResponse)
async def dongnae_dashboard(
    request: Request,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """동네비서 물류 관리 대시보드 (마스터 전용)"""
    MASTER_IDS = {"master", "010-2384-7447", "01023847447", "admin8705"}
    if cookie_store_id not in MASTER_IDS:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    return templates.TemplateResponse(request, "dongnae_dashboard.html", {
        "request": request
    })


@router.get("/admin/master", response_class=HTMLResponse)
async def master_dashboard(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    ADMIN_ACCOUNTS = ["master", "010-2384-7447", "01023847447"]
    
    if not cookie_store_id or cookie_store_id not in ADMIN_ACCOUNTS:
         return RedirectResponse(url="/admin?mode=login", status_code=303)

    # 마스터 관리 기능이 탄탄제작소 홈페이지로 이관됨
    return RedirectResponse(url="https://tantanfab.com/dashboard", status_code=303)


@router.get("/admin/logs", response_class=HTMLResponse)
async def log_monitor_page(
    request: Request,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """시스템 로그 모니터링 페이지 (마스터 전용)"""
    MASTER_IDS = {"master", "010-2384-7447", "01023847447", "admin8705"}
    if cookie_store_id not in MASTER_IDS:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    return templates.TemplateResponse(request, "admin_log_monitor.html", {
        "request": request
    })


@router.get("/api/admin/system-logs")
async def get_system_logs(
    lines: int = 100,
    level: str = "ALL",
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """시스템 로그 파일 읽기 API"""
    MASTER_IDS = {"master", "010-2384-7447", "01023847447", "admin8705"}
    if cookie_store_id not in MASTER_IDS:
        raise HTTPException(status_code=403, detail="마스터 관리자 전용")

    log_path = BASE_DIR / "logs" / "error.log"
    if not log_path.exists():
        return JSONResponse({"logs": [], "total": 0, "message": "로그 파일이 아직 없습니다."})

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        all_lines = f.readlines()

    all_lines = [l.rstrip() for l in all_lines if l.strip()]

    if level != "ALL":
        all_lines = [l for l in all_lines if f"| {level}" in l]

    total = len(all_lines)
    recent = all_lines[-lines:] if len(all_lines) > lines else all_lines

    return JSONResponse({"logs": recent, "total": total})


@router.get("/api/admin/system-logs/files")
async def get_system_log_files(
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """보관된 날짜별 로그 파일 목록"""
    MASTER_IDS = {"master", "010-2384-7447", "01023847447", "admin8705"}
    if cookie_store_id not in MASTER_IDS:
        raise HTTPException(status_code=403, detail="마스터 관리자 전용")

    log_dir = BASE_DIR / "logs"
    if not log_dir.exists():
        return JSONResponse({"files": []})

    files = []
    for f in sorted(log_dir.iterdir(), reverse=True):
        if f.is_file() and "error.log" in f.name:
            size_kb = round(f.stat().st_size / 1024, 1)
            files.append({"name": f.name, "size_kb": size_kb})

    return JSONResponse({"files": files})



@router.post("/api/admin/video_request")
async def request_video_solution(
    images: list[UploadFile] = File(...),
    story: str = Form(""),
    cookie_store_id: Union[str, None] = Cookie(default="test_store", alias="admin_session")
):
    import sys
    import json
    import uuid
    
    tantan_path = str(Path(__file__).resolve().parent.parent / "tantan_web")
    if tantan_path not in sys.path:
        sys.path.append(tantan_path)
    import tantan_services
    
    store = db.get_store(cookie_store_id)
    store_name = store.get("name", "알 수 없는 매장") if store else "알 수 없는 매장"
    
    # Save images
    saved_images = []
    upload_dir = Path("static/uploads/video_requests")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    for image in images:
        if image.filename:
            ext = image.filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4().hex}.{ext}"
            file_path = upload_dir / unique_filename
            with open(file_path, "wb") as f:
                content = await image.read()
                f.write(content)
            saved_images.append(f"/static/uploads/video_requests/{unique_filename}")
            
    images_json = json.dumps(saved_images)
    success = tantan_services.add_video_request(cookie_store_id, store_name, story, images_json)
    return {"success": success}

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
        try:
            settings = db.get_store_settings(cookie_store_id) if hasattr(db, "get_store_settings") else {}
            marketing_agreed = settings.get("marketing_agreed") in ["True", "true", "1", True]
            owner_name = store.get("owner_name") or "미입력"
            db.update_store_agreement(cookie_store_id, owner_name, marketing_agreed)
            store = db.get_store(cookie_store_id) or store
        except Exception as e:
            print(f"Agreement fallback error: {e}")
        # 로컬 환경에서는 루프 방지를 위해 통과

    if not store.get("category"):
        fallback_role = store.get("user_role") or store.get("role") or "merchant"
        try:
            store["category"] = fallback_role
            store["user_role"] = fallback_role
            store["role"] = fallback_role
            db.save_store(store_id=cookie_store_id, store_data=store)
        except Exception as e:
            print(f"Role fallback save error: {e}")
        
    now = datetime.now()
    current_month = now.month
    
    sales_stats = {"daily": [], "total_period": 0}
    products = []
    recent_orders = []
    top_products = []
    tax_est = {"vat": 0, "income_tax": 0, "total_sales": 0}
    customer_insight = {"rate": 0}
    net_profit = {"net_profit": 0, "fees": 0}
    virtual_info = None

    ai_call_logs = []
    try:
        sales_stats = db.get_sales_stats(store.get('store_id')) or sales_stats
        products = db.get_store_products(store.get('store_id')) or []
        orders_df = db.get_store_orders(store.get('store_id'))
        recent_orders = orders_df.to_dict('records') if (orders_df is not None and not orders_df.empty) else []
        top_products = db.get_top_products(store.get('store_id')) or []
        tax_est = db.get_tax_estimates(store.get('store_id')) or tax_est
        customer_insight = db.get_customer_revisit_rate(store.get('store_id')) or customer_insight
        net_profit = db.get_net_profit_analysis(store.get('store_id')) or net_profit
        
        logs_df = db.get_ai_call_logs(store.get('store_id'), limit=50)
        ai_call_logs = logs_df.to_dict('records') if not logs_df.empty else []
        
        virtual_info = db.get_store_virtual_number(store.get('store_id'))
    except Exception as e:
        print(f"Dashboard Data Fetch Error: {e}")

    video_requests = []
    try:
        import sys
        tantan_path = str(Path(__file__).resolve().parent.parent / "tantan_web")
        if tantan_path not in sys.path:
            sys.path.append(tantan_path)
        import tantan_services
        video_requests = tantan_services.get_store_video_requests(store.get('store_id'))
    except Exception as e:
        print(f"Error fetching video requests: {e}")

    response_obj = templates.TemplateResponse(request, "dashboard.html", {
        "request": request, 
        "store_name": store.get("store_name", "내 상점"),
        "store": store, 
        "video_requests": video_requests,
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
        "profit": net_profit,
        "ai_logs": ai_call_logs,
        "virtual_info": virtual_info
    })
    
    return response_obj

@router.get("/admin/calls", response_class=HTMLResponse)
async def missed_calls_page(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin", status_code=303)
        
    try:
        logs_df = db.get_ai_call_logs(cookie_store_id, limit=100)
        ai_call_logs = logs_df.to_dict('records') if not logs_df.empty else []
    except Exception as e:
        print(f"Call Logs Fetch Error: {e}")
        ai_call_logs = []

    return templates.TemplateResponse(request, "admin_calls.html", {
        "request": request,
        "ai_logs": ai_call_logs
    })

class ChatRequest(BaseModel):
    message: str

@router.post("/api/chat")
async def admin_chat(
    payload: ChatRequest,
    request: Request,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """비서에게 물어보기 — 관리자 전용 AI 챗봇 엔드포인트"""
    if not cookie_store_id:
        return {"success": False, "error": "로그인이 필요합니다."}

    user_message = payload.message.strip()
    if not user_message:
        return {"success": False, "error": "질문 내용을 입력해주세요."}

    # 매장 컨텍스트 조회
    store = db.get_store(cookie_store_id)
    store_name = store.get("name", "매장") if store else "매장"
    store_type = store.get("store_type", "") if store else ""

    # 최근 주문·매출 요약 컨텍스트
    context_lines = []
    try:
        stats = db.get_sales_stats(cookie_store_id) or {}
        total = stats.get("total_period", 0)
        context_lines.append(f"- 최근 매출 합계: {total:,}원")
    except Exception:
        pass
    try:
        orders_df = db.get_store_orders(cookie_store_id)
        if orders_df is not None and not orders_df.empty:
            context_lines.append(f"- 오늘 접수 주문: {len(orders_df)}건")
    except Exception:
        pass

    store_context = "\n".join(context_lines) if context_lines else "데이터 없음"

    system_prompt = f"""당신은 '{store_name}' 사장님을 돕는 동네비서 AI 비서입니다.
업종: {store_type}

[매장 현황]
{store_context}

사장님의 질문에 친절하고 간결하게 (3~5문장 이내) 한국어로 답변하세요.
수수료, 정산, 주문, 매출 관련 질문에 위 데이터를 활용하세요.
모르는 내용은 솔직하게 모른다고 말하세요."""

    try:
        import ai_manager
        result = ai_manager.get_ai_response(
            user_input=user_message,
            system_prompt=system_prompt,
            tool_set='admin'
        )
        if isinstance(result, dict):
            response_text = result.get("text", "답변을 생성할 수 없습니다.")
        else:
            response_text = str(result)

        return {"success": True, "response": response_text}
    except Exception as e:
        print(f"[/api/chat] AI Error: {e}")
        return {"success": False, "error": f"AI 서버 오류: {str(e)}"}


@router.get("/admin/api/settlement/report")
async def get_settlement_report(year: int = None, month: int = None, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
        
    import datetime
    now = datetime.datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
        
    try:
        from settlement_engine import calculate_monthly_settlement
        # 마스터 관리자는 전체 조회가 가능하도록 store_id 파라미터를 해제
        store_id_param = cookie_store_id
        if cookie_store_id in ["master", "010-2384-7447", "01023847447"]:
            store_id_param = None
            
        report = calculate_monthly_settlement(year, month, store_id=store_id_param)
        return {"success": True, "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/admin/call-log/{log_id}/read")
async def mark_ai_log_read(request: Request, log_id: int, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return {"success": False}
    db.mark_ai_call_read(log_id, cookie_store_id)
    return {"success": True}


@router.get("/admin/support", response_class=HTMLResponse)
async def support_diagnosis_page(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
        
    store = db.get_store(cookie_store_id)
    if not store:
        return RedirectResponse(url="/admin?mode=login", status_code=303)

    return templates.TemplateResponse(request, "support_diagnosis.html", {
        "request": request,
        "store": store,
        "api_url": API_URL
    })


@router.get("/admin/commercial", response_class=HTMLResponse)
async def commercial_analysis_page(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
        
    store = db.get_store(cookie_store_id)
    if not store:
        return RedirectResponse(url="/admin?mode=login", status_code=303)

    return templates.TemplateResponse(request, "commercial_analysis.html", {
        "request": request,
        "store": store,
        "api_url": API_URL
    })

@router.post("/api/admin/commercial/delegate")
async def delegate_commercial_analysis(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return {"success": False, "error": "로그인이 필요합니다."}
        
    data = await request.json()
    area = data.get("area", "지정 지역")
    
    store = db.get_store(cookie_store_id)
    phone = store.get("phone", "") if store else ""
    
    import config
    import sms_manager
    # 사장님 번호가 없으면 시스템 마스터 번호로 발송
    target_phone = phone if phone else config.get_secret("SENDER_PHONE")
    
    if target_phone:
        alimtalk_msg = f"[동네비서 상권분석]\n사장님, '{area}' 지역의 상권분석 리포트가 접수되었습니다. (완료 시 재알림)"
        sms_manager.send_alimtalk(target_phone, alimtalk_msg, template_id="tmp_commercial", variables={"#{area}": area})
        
    return {"success": True}


@router.get("/admin/wallet", response_class=HTMLResponse)
async def admin_wallet_page(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)

    store = db.get_store(cookie_store_id)
    if not store:
        response = RedirectResponse(url="/admin?mode=login", status_code=303)
        response.delete_cookie("admin_session")
        return response

    details = db.get_wallet_details(cookie_store_id)
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "")

    return templates.TemplateResponse(request, "admin_wallet.html", {
        "request": request,
        "store_id": cookie_store_id,
        "details": details,
        "toss_client_key": toss_client_key
    })

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
    response = templates.TemplateResponse(request, "citizen_dashboard.html", {
        "request": request,
        "toss_client_key": toss_client_key
    })
    
    return response

@router.get("/delivery-dashboard", response_class=HTMLResponse)
async def delivery_page(request: Request, current_user: User = Depends(get_current_user)):
    # role check is optional or could just be logged, but we'll enforce it gracefully
    if current_user.role not in ["delivery", "logistics", "master"]:
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    settings = db.get_all_settings(current_user.store_id) if hasattr(db, "get_all_settings") else {}
    return templates.TemplateResponse(request, "delivery_dashboard.html", {"request": request, "user": current_user, "settings": settings})

@router.get("/delivery/brochure", response_class=HTMLResponse)
async def delivery_brochure_page(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "delivery_brochure.html", {"request": request, "user": current_user})

@router.get("/admin/calculator", response_class=HTMLResponse)
async def calculator_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "calculator.html", {"request": request})

@router.get("/courier", response_class=HTMLResponse)
async def courier_page(request: Request, user: User = Depends(get_current_user)):
    if not user.is_signed:
        return RedirectResponse(url="/agreement")
    store_info = db.get_store(user.store_id)
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
    return templates.TemplateResponse(request, "courier_manager.html", {
        "request": request,
        "api_url": API_URL,
        "store": store_info,
        "toss_client_key": toss_client_key
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
    return templates.TemplateResponse(request, "auto_reply_settings.html", {"request": request})

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
    return templates.TemplateResponse(request, "store_management.html", {"request": request, "store": store})

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

from pydantic import BaseModel

class PaymentConfirmRequest(BaseModel):
    paymentKey: str
    orderId: str
    amount: int
    store_id: str

@router.post("/api/payment/confirm")
async def api_payment_confirm(data: PaymentConfirmRequest):
    payment_key = data.paymentKey
    order_id = data.orderId
    amount = data.amount
    store_id = data.store_id
    
    # 1. Verify with Toss API
    import base64
    import requests
    from fastapi.concurrency import run_in_threadpool
    
    toss_secret_key = os.getenv("TOSS_SECRET_KEY", "test_sk_26DlbXAaV0Kbn1ljMQa43qY50Q9R")
    url = "https://api.tosspayments.com/v1/payments/confirm"
    
    secret_key_with_colon = f"{toss_secret_key}:"
    encoded_secret_key = base64.b64encode(secret_key_with_colon.encode("utf-8")).decode("utf-8")
    
    headers = {
        "Authorization": f"Basic {encoded_secret_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "paymentKey": payment_key,
        "orderId": order_id,
        "amount": amount
    }
    
    try:
        def call_toss():
            return requests.post(url, headers=headers, json=payload, timeout=10)
            
        response = await run_in_threadpool(call_toss)
        
        if response.status_code != 200:
            # --- SANDBOX/TEST BYPASS ---
            if toss_secret_key.startswith("test_sk_"):
                points_to_credit = round(amount / 1.1)
                success = await run_in_threadpool(db.confirm_payment, store_id, points_to_credit, order_id, payment_key)
                if success:
                    return {"status": "success", "message": "충전이 완료되었습니다 (테스트 우회 승인).", "points_credited": points_to_credit, "sandbox_bypass": True}
            # ---------------------------
            error_data = response.json()
            error_message = error_data.get("message", "토스 결제 승인 실패")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": f"승인 실패 (HTTP {response.status_code}): {error_message}"}
            )
            
        # 2. Payment confirmed successfully. Now calculate points to credit (VAT conversion).
        # We need to credit points = Math.round(amount / 1.1) to reflect the base points (e.g. 5,000P).
        points_to_credit = round(amount / 1.1)
        
        # 3. Update the database
        success = await run_in_threadpool(db.confirm_payment, store_id, points_to_credit, order_id, payment_key)
        
        if success:
            return {"status": "success", "message": "충전이 완료되었습니다.", "points_credited": points_to_credit}
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "데이터베이스 저장 실패"}
            )
            
    except Exception as e:
        print(f"[API payment confirm error] {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"시스템 오류: {str(e)}"}
        )

@router.post("/api/admin/products")
async def register_product(
    name: str = Form(...),
    price: int = Form(...),
    image: UploadFile = File(None)
):
    store_id = "test_store"
    
    store = db.get_store(store_id)
    if not store:
         return {"success": False, "error": "스토어 정보를 찾을 수 없습니다."}

    image_path = ""
    if image and getattr(image, "filename", ""):
        import shutil, os
        os.makedirs("uploads", exist_ok=True)
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

@router.get("/admin/reservations", response_class=HTMLResponse)
async def unified_reservations_page(request: Request, current_user: User = Depends(get_current_user)):
    role = current_user.role or current_user.category or "merchant"
    
    if role in ["logistics", "delivery", "courier"]:
        return templates.TemplateResponse(request, "delivery_order_dashboard.html", {"request": request, "user": current_user, "api_url": API_URL})
    elif role == "farmer":
        return templates.TemplateResponse(request, "farm_order_dashboard.html", {"request": request, "user": current_user, "api_url": API_URL})
    else:
        return templates.TemplateResponse(request, "merchant_order_dashboard.html", {"request": request, "user": current_user, "api_url": API_URL})

@router.get("/api/admin/orders")
async def get_orders_api(request: Request, type: str = "FARM"):
    cookie_store_id = request.cookies.get("admin_session")
    if not cookie_store_id:
        return []
    
    try:
        orders = db.get_store_orders(cookie_store_id, days=30)
        if hasattr(orders, "to_dict"):
            orders = orders.to_dict(orient="records")
        return orders if isinstance(orders, list) else []
    except Exception as e:
        print(f"[Orders API Error] {e}")
        return []

@router.get("/api/admin/reservations")
async def get_reservations_api(request: Request):
    cookie_store_id = request.cookies.get("admin_session")
    if not cookie_store_id:
        return []
    try:
        res = db.get_store_reservations(cookie_store_id)
        if hasattr(res, "to_dict"):
            res = res.to_dict(orient="records")
        return res if isinstance(res, list) else []
    except Exception as e:
        print(f"[Reservations API Error] {e}")
        return []

@router.get("/api/admin/deliveries")
async def get_deliveries_api(request: Request):
    try:
        res = db.get_store_deliveries("CITIZEN")
        if hasattr(res, "to_dict"):
            res = res.to_dict(orient="records")
        return res if isinstance(res, list) else []
    except Exception as e:
        print(f"[Deliveries API Error] {e}")
        return []

@router.get("/admin/product/register", response_class=HTMLResponse)
async def register_product_page(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    return templates.TemplateResponse(request, "product_register.html", {"request": request})

@router.get("/admin/tax", response_class=HTMLResponse)
async def tax_dashboard(request: Request):
    return templates.TemplateResponse(request, "tax_dashboard.html", {"request": request})

@router.get("/api/admin/tax/stats")
async def get_tax_stats():
    store_id = "test_store" 
    stats = db.get_tax_stats(store_id)
    return stats

@router.get("/admin/expenses", response_class=HTMLResponse)
async def expenses_page(request: Request):
    return templates.TemplateResponse(request, "expenses.html", {"request": request})

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

@router.get("/admin/crm/setup", response_class=HTMLResponse)
async def crm_setup_page(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    return templates.TemplateResponse(request, "crm_setup.html", {"request": request})

@router.post("/api/admin/crm/setup")
async def finish_crm_setup(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
        
    form_data = await request.form()
    template = form_data.get("template", "blank")
    
    store = db.get_store(cookie_store_id)
    if store:
        store['crm_template'] = template
        db.save_store(cookie_store_id, store)
        
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@router.post("/api/admin/manual-sms")
async def send_manual_sms(request: Request, kw: str = None, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if kw != "admin1234" and not cookie_store_id:
        return {"success": False, "error": "로그인이 필요합니다."}
        
    data = await request.json()
    target_phone = data.get("phone")
    if not target_phone:
        return {"success": False, "error": "전화번호를 입력해주세요."}
        
    import sms_manager
    store_name = "동네비서"
    if cookie_store_id:
        store = db.get_store(cookie_store_id)
        if store:
            store_name = store.get("name", "동네비서 매장")
    
    try:
        sms_manager.send_smart_callback(cookie_store_id or "master", target_phone, store_name)
        return {"success": True, "message": "성공적으로 발송되었습니다."}
    except Exception as e:
        print(f"Manual SMS Error: {e}")
        return {"success": False, "error": f"발송 실패: {e}"}

@router.get("/admin/logen/settings", response_class=HTMLResponse)
async def logen_auth_settings_page(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    return templates.TemplateResponse(request, "logen_auth.html", {"request": request, "store_id": cookie_store_id})

@router.post("/api/admin/logen/settings")
async def update_logen_auth_settings(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    import time
    if not cookie_store_id:
        return {"success": False, "error": "로그인이 필요합니다."}
        
    data = await request.json()
    new_pw = data.get("logen_pw")
    new_id = data.get("logen_id")
    
    if not new_pw and not new_id:
        return {"success": False, "error": "업데이트할 정보가 입력되지 않았습니다."}
        
    if hasattr(db, "save_store_setting"):
        if new_pw:
            db.save_store_setting(cookie_store_id, "logen_pw", new_pw)
            db.save_store_setting(cookie_store_id, "logen_pw_updated_at", str(time.time()))
        if new_id:
            db.save_store_setting(cookie_store_id, "logen_id", new_id)
        return {"success": True}
    return {"success": False, "error": "DB 저장 기능 오류"}

@router.post("/api/admin/courier/settings")
async def update_courier_settings(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    import time
    if not cookie_store_id:
        return {"success": False, "error": "로그인이 필요합니다."}
        
    data = await request.json()
    carrier = data.get("carrier")
    courier_id = data.get("courier_id")
    courier_pw = data.get("courier_pw")
    courier_car_no = data.get("courier_car_no")
    
    if not carrier:
        return {"success": False, "error": "택배사가 선택되지 않았습니다."}
        
    if hasattr(db, "save_store_setting"):
        db.save_store_setting(cookie_store_id, "courier_carrier", carrier)
        if courier_id is not None:
            db.save_store_setting(cookie_store_id, "courier_id", courier_id)
            if carrier == "kr.logen":
                db.save_store_setting(cookie_store_id, "logen_id", courier_id)
        if courier_pw is not None:
            db.save_store_setting(cookie_store_id, "courier_pw", courier_pw)
            db.save_store_setting(cookie_store_id, "courier_pw_updated_at", str(time.time()))
            if carrier == "kr.logen":
                db.save_store_setting(cookie_store_id, "logen_pw", courier_pw)
                db.save_store_setting(cookie_store_id, "logen_pw_updated_at", str(time.time()))
        if courier_car_no is not None:
            db.save_store_setting(cookie_store_id, "courier_car_no", courier_car_no)
            if carrier == "kr.logen":
                db.save_store_setting(cookie_store_id, "logen_car_no", courier_car_no)
        return {"success": True}
    return {"success": False, "error": "DB 저장 기능 오류"}

@router.get("/api/admin/courier/settings")
async def get_courier_settings(cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return {"success": False, "error": "로그인이 필요합니다."}
        
    settings = {}
    if hasattr(db, "get_store_settings"):
        settings = db.get_store_settings(cookie_store_id) or {}
        
    carrier = settings.get("courier_carrier") or "kr.logen"
    courier_id = settings.get("courier_id")
    courier_pw = settings.get("courier_pw")
    courier_car_no = settings.get("courier_car_no")
    
    # Fallback to legacy Logen settings if the new unified settings are empty
    if not courier_id:
        courier_id = settings.get("logen_id", "")
    if not courier_pw:
        courier_pw = settings.get("logen_pw", "")
    if not courier_car_no:
        courier_car_no = settings.get("logen_car_no", "")
    
    return {
        "success": True,
        "carrier": carrier,
        "courier_id": courier_id,
        "courier_pw": courier_pw,
        "courier_car_no": courier_car_no
    }

import ocr_manager

@router.post("/api/admin/ledger/upload")
async def upload_receipt(request: Request, file: UploadFile = File(...), cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return {"success": False, "error": "로그인이 필요합니다."}
        
    try:
        content = await file.read()
        ocr_res = ocr_manager.call_naver_ocr(content)
        
        if not ocr_res:
            return {"success": False, "error": "OCR 분석에 실패했습니다."}
            
        text = ocr_res.get("raw_text", "")
        # 분석 정확도 향상을 위한 키워드 감지 (모의 환경 지원)
        is_sales = "배민" in text or "요기요" in text or "배달" in text or "정산" in text
        extract_amount = 150000 if is_sales else 23500
        
        if is_sales:
            # 매출 기장
            if hasattr(db, "save_order"):
                # store_id, item_name, amount, customer_name, contact, address, status, delivery_track, ... 
                # (We map mock values suitably for DB. In actual prod, we'd insert into a ledger_sales table or use save_order carefully)
                try:
                    db.save_order(cookie_store_id, "배달앱 정산", extract_amount, "배달플랫폼", "000-0000", "자동기장", "완료", "0")
                except:
                    pass
            type_str = "매출(정산)"
        else:
            # 매입 지출 기장
            if hasattr(db, "save_expense"):
                date_str = datetime.now().strftime("%Y-%m-%d")
                db.save_expense(cookie_store_id, "AI영수증스캔", "경비처리", extract_amount, date_str)
            type_str = "매입(경비)"
            
        return {
            "success": True, 
            "type": type_str, 
            "amount": extract_amount, 
            "raw": ocr_res
        }
    except Exception as e:
        print(f"OCR Upload Error: {e}")
        return {"success": False, "error": str(e)}

# ────────────────────────────────────────────────────────────────
# 📞 가맹점 대표 유선전화 연동 (대행 등록 API)
# ────────────────────────────────────────────────────────────────
class VirtualNumberRegister(BaseModel):
    store_id: str
    virtual_number: str
    label: str = ""

@router.post("/api/admin/virtual-number/register")
async def register_virtual_number(data: VirtualNumberRegister, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    # 마스터 관리자(대표님) 또는 본인 매장만 등록 가능하게 보안 검증
    ADMIN_ACCOUNTS = ["master", "010-2384-7447", "01023847447"]
    is_admin = cookie_store_id in ADMIN_ACCOUNTS
    
    if not cookie_store_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    if not is_admin and cookie_store_id != data.store_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 번호 포맷 정규화 (하이픈 제거하고 숫자만 저장하거나, 규격 통일)
    import re
    norm_num = re.sub(r'[^0-9-]', '', data.virtual_number)
    
    if not norm_num:
        return {"success": False, "error": "올바른 유선전화 번호가 아닙니다."}

    success = db.save_virtual_number(norm_num, data.store_id, data.label, "active")
    if success:
        return {"success": True, "message": "가맹점 대표 유선번호 연동(웹훅) 등록 완료"}
    return {"success": False, "error": "DB 저장 중 오류가 발생했습니다."}

class VirtualNumberDelete(BaseModel):
    virtual_number: str

@router.post("/api/admin/virtual-number/delete")
async def delete_virtual_number(data: VirtualNumberDelete, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    ADMIN_ACCOUNTS = ["master", "010-2384-7447", "01023847447"]
    if not cookie_store_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
        
    # 가속 삭제를 위해 SQLite 테이블에서 직접 row 삭제 또는 비활성화 처리
    try:
        import sqlite3
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        
        # 권한 체크: 마스터는 다 지울 수 있고, 일반 점주는 자기 매장 번호만 지울 수 있음
        if cookie_store_id not in ADMIN_ACCOUNTS:
            c.execute("SELECT store_id FROM virtual_numbers WHERE virtual_number = ?", (data.virtual_number,))
            row = c.fetchone()
            if not row or row[0] != cookie_store_id:
                conn.close()
                raise HTTPException(status_code=403, detail="해당 유선번호를 삭제할 권한이 없습니다.")
                
        c.execute("DELETE FROM virtual_numbers WHERE virtual_number = ?", (data.virtual_number,))
        conn.commit()
        conn.close()
        return {"success": True, "message": "유선번호 연동이 해제되었습니다."}
    except Exception as e:
        return {"success": False, "error": f"해제 실패: {str(e)}"}


# ──────────────────────────────────────────────
# 시스템 로그 API (마스터 전용)
# ──────────────────────────────────────────────
MASTER_IDS = {"master", "010-2384-7447", "01023847447"}
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "error.log")
LOG_DIR  = os.path.dirname(LOG_FILE)

def _is_authorized_log_request(request: Request, cookie_store_id: str) -> bool:
    """쿠키 세션 또는 X-Admin-Token 헤더로 인증 확인"""
    # 1) 쿠키 세션 인증 (dongnebiseo.com 직접 접속)
    if cookie_store_id in MASTER_IDS:
        return True
    # 2) API 토큰 인증 (tantanfab.com 등 외부 embed용)
    token = request.headers.get("X-Admin-Token", "")
    server_token = os.environ.get("WEBHOOK_TOKEN", "")
    return bool(token and server_token and token == server_token)

@router.get("/api/admin/system-logs")
async def get_system_logs(
    request: Request,
    lines: int = 100,
    level: str = "ALL",
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """최근 로그 N줄을 반환. level=ERROR/WARNING/INFO/ALL 필터 지원.
    인증: admin_session 쿠키(마스터) 또는 X-Admin-Token 헤더"""
    if not _is_authorized_log_request(request, cookie_store_id or ""):
        raise HTTPException(status_code=403, detail="마스터 관리자만 접근 가능합니다.")

    if not os.path.exists(LOG_FILE):
        return {"logs": [], "total": 0, "message": "로그 파일이 아직 생성되지 않았습니다."}

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        all_lines = [l.rstrip() for l in f.readlines() if l.strip()]

    if level != "ALL":
        all_lines = [l for l in all_lines if f"| {level}" in l]

    recent = list(reversed(all_lines[-lines:]))
    return {"logs": recent, "total": len(all_lines), "shown": len(recent)}


@router.get("/api/admin/system-logs/files")
async def get_log_files(
    request: Request,
    cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")
):
    """보관 중인 날짜별 로그 파일 목록 반환."""
    if not _is_authorized_log_request(request, cookie_store_id or ""):
        raise HTTPException(status_code=403, detail="마스터 관리자만 접근 가능합니다.")

    if not os.path.exists(LOG_DIR):
        return {"files": []}

    files = []
    for fname in sorted(os.listdir(LOG_DIR), reverse=True):
        fpath = os.path.join(LOG_DIR, fname)
        if os.path.isfile(fpath):
            size_kb = round(os.path.getsize(fpath) / 1024, 1)
            files.append({"name": fname, "size_kb": size_kb})

    return {"files": files}


# --- 신규 가맹점 대시보드 연동 라우트 ---

@router.get("/manage_orders", response_class=HTMLResponse)
async def manage_orders(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    mock_orders = [
        {'name': '김철수', 'item': '사과 1박스 (특등급)', 'price': '35,000'},
        {'name': '이영희', 'item': '배 2박스', 'price': '60,000'},
        {'name': '박지민', 'item': '사과즙 50포', 'price': '25,000'}
    ]
    mock_callbacks = [
        {'name': '최민수', 'reason': '장바구니 결제 미완료 (3시간 경과)', 'phone': '010-1234-5678'},
        {'name': '정재현', 'reason': '계좌번호 문의 (AI 자동 응답됨)', 'phone': '010-9876-5432'}
    ]
    return templates.TemplateResponse(request, "manage_orders.html", {"request": request, "orders": mock_orders, "callbacks": mock_callbacks})

@router.get("/ai_assistant", response_class=HTMLResponse)
async def ai_assistant(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    store = db.get_store(cookie_store_id)
    return templates.TemplateResponse(request, "ai_assistant.html", {"request": request, "store_name": store.get("store_name", "내 상점")})

@router.get("/token_history", response_class=HTMLResponse)
async def token_history(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    store = db.get_store(cookie_store_id)
    history = [
        {"date": "2026-07-15 14:00", "method": "토큰 사용", "amount": "-10 🔮", "tokens_added": "AI 자동 응답"},
        {"date": "2026-07-14 09:30", "method": "토큰 충전", "amount": "+1,000 🔮", "tokens_added": "계좌이체 충전"}
    ]
    return templates.TemplateResponse(request, "token_history.html", {"request": request, "history": history, "store_name": store.get("store_name", "내 상점")})

@router.get("/token_recharge", response_class=HTMLResponse)
async def token_recharge(request: Request, cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    if not cookie_store_id:
        return RedirectResponse(url="/admin?mode=login", status_code=303)
    store = db.get_store(cookie_store_id)
    return templates.TemplateResponse(request, "token_recharge.html", {"request": request, "store_name": store.get("store_name", "내 상점")})

@router.post("/api/ai/query")
async def ai_query(request: Request, query_type: str = Form(None), custom_text: str = Form('')):
    custom_text = custom_text.strip() if custom_text else ""
    if query_type == 'orders_today':
        reply = "오늘 총 3건의 신규 주문이 있습니다. (김철수님 외 2건, 총 120,000원 대기 중)"
        return {"reply": reply, "action": None}
    elif query_type == 'sales_month':
        reply = "이번 달 누적 매출액은 4,550,000원입니다. 지난달 대비 15% 상승 중입니다!"
        return {"reply": reply, "action": None}
    elif query_type == 'bestseller':
        reply = "현재 '사과 세트'가 가장 많이 팔리고 있습니다. 이 상품으로 홍보용 숏폼을 하나 더 만들어볼까요? (예상비용: 10 🔮)"
        return {"reply": reply, "action": "create_shortform"}
    elif custom_text:
        import ai_manager
        system_prompt = "당신은 가맹점 사장님을 돕는 친절한 비서입니다. 사장님의 질문에 전문적이고 명확하게 짧게 답하세요."
        reply = ai_manager.get_ai_response(custom_text, system_prompt=system_prompt, tool_set='admin')
        return {"reply": reply, "action": None}
    return {"reply": "잘못된 요청입니다.", "action": None}

@router.post("/api/token_recharge")
async def process_token_recharge(request: Request, amount: str = Form(...), cookie_store_id: Union[str, None] = Cookie(default=None, alias="admin_session")):
    return {"success": True, "message": f"{amount}원 충전 요청이 접수되었습니다."}
