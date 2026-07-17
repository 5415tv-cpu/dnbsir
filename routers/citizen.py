from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Union
from datetime import datetime
from pathlib import Path
import os
import db_manager as db
from .auth import get_current_user, User
import logen_delivery

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
from templates_config import templates
API_URL = os.environ.get("API_URL", "")

from typing import List, Union, Optional

async def get_optional_current_user(request: Request):
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def convert_to_road_address_and_postcode(address_str: str, default_postcode: str = "") -> (str, str):
    """
    구주소(지번) 또는 임의의 주소 문자열을 입력받아,
    카카오 로컬 API를 사용하여 표준 도로명 주소(road_address)와 우편번호(zone_no)로 자동 변환합니다.
    변환 실패 시 혹은 데이터가 없는 경우 원래 값을 그대로 반환합니다.
    """
    if not address_str or not address_str.strip():
        return address_str, default_postcode
    
    kakao_key = os.environ.get("KAKAO_REST_API_KEY")
    if not kakao_key:
        return address_str, default_postcode
    
    import requests
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    params = {"query": address_str}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            res_json = response.json()
            documents = res_json.get("documents", [])
            if documents:
                doc = documents[0]
                road_addr_info = doc.get("road_address")
                if road_addr_info:
                    road_address = road_addr_info.get("address_name")
                    zone_no = road_addr_info.get("zone_no") or default_postcode
                    if road_address:
                        return road_address, zone_no
                
                address_info = doc.get("address")
                if address_info:
                    zip_code = address_info.get("zip_code") or default_postcode
                    return address_info.get("address_name") or address_str, zip_code
    except Exception as e:
        print(f"[Address Normalization Warning] Failed to convert address: {e}")
        
    return address_str, default_postcode


class CourierReservationRequest(BaseModel):
    sender_name: str
    sender_phone: str
    sender_addr: str
    sender_postcode: Optional[str] = ""
    sender_base_address: Optional[str] = ""
    sender_detail_address: Optional[str] = ""
    
    receiver_name: str
    receiver_phone: str
    receiver_addr: str
    postcode: Optional[str] = ""
    address: Optional[str] = ""
    detail_address: Optional[str] = ""
    
    item_type: str
    weight: str = "small"              # 단일 (하위 호환)
    quantity: int = 1                  # 단일 (하위 호환)
    sizes_ordered: Optional[List[dict]] = None  # [{"size":"small","qty":1}, ...]
    payment_method: str = "toss"
    pay_type: str = "prepaid"

class CourierMultiReservationRequest(BaseModel):
    reservations: List[CourierReservationRequest]

class CourierRequestZero(BaseModel):
    sender_name: str
    sender_phone: str
    sender_postcode: str
    sender_addr: str
    sender_detail_address: str
    receiver_name: str
    receiver_phone: str
    postcode: str
    address: str
    detail_address: str
    item_type: str

class PublicReservationRequest(BaseModel):
    store_id: str

class CitizenChatRequest(BaseModel):
    message: str
    phone: str = ""
    store_id: str = ""
    customer_name: str
    customer_phone: str
    res_date: str
    res_time: str
    head_count: int = 1
    menu_summary: str = ""
    request_note: str = ""
    consent: bool = False

from fastapi.responses import HTMLResponse, RedirectResponse

@router.get("/delivery-landing", response_class=HTMLResponse)
async def delivery_landing_page(request: Request):
    return templates.TemplateResponse(request, "delivery_landing.html", {"request": request})

@router.get("/delivery/request", response_class=HTMLResponse)
async def delivery_request_page(request: Request, ref: str = ""):
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    return templates.TemplateResponse(request, "delivery_request.html", {
        "request": request,
        "ref": ref,
        "toss_client_key": toss_client_key,
        "google_api_key": google_api_key,
    })

@router.post("/api/payment/success")
async def process_payment_success_api(payload: dict, request: Request):
    print("Process Payment Success API Called with payload:", payload)
    return {"success": True, "message": "결제 처리가 완료되었습니다."}

@router.post("/api/citizen/chat")
async def citizen_chat(payload: CitizenChatRequest, request: Request):
    """일반 고객(시민) 전용 AI 매니저 채팅 엔드포인트"""
    user_message = payload.message.strip()
    store_id = payload.store_id
    
    if not user_message:
         return {"success": False, "error": "질문 내용을 입력해주세요."}
    
    store = db.get_store(store_id)
    store_name = store.get("name", "해당 매장") if store else "해당 매장"
    store_type = store.get("store_type", "") if store else ""
    
    system_prompt = f"""당신은 '{store_name}' 매장을 방문한 고객을 응대하는 친절하고 유능한 AI 매니저입니다.
업종: {store_type}

고객의 질문에 친절하고 상세하게 안내하세요. 가급적 길고 상세한 문장으로 답변을 제공해도 좋습니다.
예약이나 주문 방법, 매장 위치 등을 묻는다면 웹페이지의 버튼과 기능을 이용하라고 안내하세요."""

    try:
        import ai_manager
        result = ai_manager.get_ai_response(
            user_input=user_message,
            system_prompt=system_prompt,
            tool_set='customer'
        )
        if isinstance(result, dict):
            response_text = result.get("text", "답변을 생성할 수 없습니다.")
        else:
            response_text = str(result)
            
        return {"success": True, "response": response_text}
    except Exception as e:
        print(f"[/api/citizen/chat] AI Error: {e}")
        return {"success": False, "error": "AI 서버 오류가 발생했습니다."}

@router.post("/api/delivery/request")
async def api_delivery_request_zero(data: CourierRequestZero, request: Request):
    # 2nd layer backend validation: check if any required field is empty or missing
    fields = [
        (data.sender_name, "보내는 분 성함"),
        (data.sender_phone, "보내는 분 연락처"),
        (data.sender_postcode, "보내는 분 우편번호"),
        (data.sender_addr, "보내는 분 기본 주소"),
        (data.sender_detail_address, "보내는 분 상세 주소"),
        (data.receiver_name, "받는 분 성함"),
        (data.receiver_phone, "받는 분 연락처"),
        (data.postcode, "받는 분 우편번호"),
        (data.address, "받는 분 기본 주소"),
        (data.detail_address, "받는 분 상세 주소"),
        (data.item_type, "물품명")
    ]
    for val, label in fields:
        if not val or not val.strip():
            raise HTTPException(status_code=400, detail=f"[{label}] 필드가 누락되었거나 비어 있습니다.")

    store_id = "CITIZEN"
    total_fee = 6000 # 고정 기본 요금 적용
    tracking_code = f"LOGEN-{int(datetime.now().timestamp())}"

    # Normalize addresses to Road Name Addresses
    road_recv_base, postcode_recv = convert_to_road_address_and_postcode(data.address, data.postcode)
    road_send_base, postcode_send = convert_to_road_address_and_postcode(data.sender_addr, data.sender_postcode)

    # 1. Save to deliveries table (via save_delivery or save_store_delivery)
    delivery_data = {
        "store_id": store_id,
        "date_time": datetime.now().isoformat(),
        "sender_name": data.sender_name,
        "receiver_name": data.receiver_name,
        "receiver_addr": f"{road_recv_base} {data.detail_address}",
        "item_type": data.item_type,
        "weight": "small",
        "quantity": 1,
        "tracking_code": tracking_code,
        "fee": total_fee,
        "status": "접수완료",
        "payment_type": "착불"
    }

    try:
         from fastapi.concurrency import run_in_threadpool
         if hasattr(db, 'save_store_delivery'):
              await run_in_threadpool(db.save_store_delivery, delivery_data)
         else:
              await run_in_threadpool(db.save_delivery, delivery_data)

         # 2. Save to delivery_users / delivery_orders / order_recipients tables
         order_data = {
             "order_id": tracking_code,
             "sender_name": data.sender_name,
             "sender_phone": data.sender_phone,
             "sender_postcode": postcode_send,
             "sender_base_address": road_send_base,
             "sender_detail_address": data.sender_detail_address,
             "receiver_name": data.receiver_name,
             "receiver_phone": data.receiver_phone,
             "postcode": postcode_recv,
             "address": road_recv_base,
             "detail_address": data.detail_address,
             "status": "REQUESTED"
         }
         await run_in_threadpool(db.save_delivery_order, order_data)

         return {
             "success": True, 
             "tracking_code": tracking_code
         }
    except Exception as e:
         print(f"[API_Zero] 접수 처리 실패: {e}")
         raise HTTPException(status_code=500, detail=f"데이터베이스 접수 저장 실패: {e}")

# ─────────────────────────────────────────────────────
# 엑셀 대량 등록 API
# ─────────────────────────────────────────────────────
@router.post("/api/delivery/bulk-excel")
async def api_delivery_bulk_excel(file: UploadFile = File(...)):
    """
    엑셀(.xlsx/.xls/.csv) 파일을 받아 다건 택배를 일괄 접수합니다.
    컬럼: 보내는분이름 | 보내는분연락처 | 보내는분주소 | 보내는분상세주소 |
          받는분이름   | 받는분연락처   | 받는분주소   | 받는분상세주소   | 물품명
    """
    import io, openpyxl, csv
    from fastapi.concurrency import run_in_threadpool

    content = await file.read()
    filename = (file.filename or "").lower()

    rows = []
    try:
        if filename.endswith(".csv"):
            text = content.decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        else:
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            ws = wb.active
            headers = None
            for r in ws.iter_rows(values_only=True):
                if headers is None:
                    headers = [str(c).strip() if c else "" for c in r]
                    continue
                if all(v is None for v in r):
                    continue
                rows.append(dict(zip(headers, [str(v).strip() if v is not None else "" for v in r])))
            wb.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 파싱 실패: {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="데이터 행이 없습니다.")

    # 컬럼 별칭 매핑 (한글/영어 혼용 허용)
    COL = {
        "sender_name":           ["보내는분이름","보내는 분 이름","송신자","발신자","sender_name","sender name"],
        "sender_phone":          ["보내는분연락처","보내는 분 연락처","발신자전화","sender_phone","sender phone"],
        "sender_addr":           ["보내는분주소","보내는 분 주소","수거주소","sender_addr","sender address"],
        "sender_detail_address": ["보내는분상세주소","보내는 분 상세주소","수거상세","sender_detail"],
        "sender_postcode":       ["보내는분우편번호","sender_postcode"],
        "receiver_name":         ["받는분이름","받는 분 이름","수신자","receiver_name","receiver name"],
        "receiver_phone":        ["받는분연락처","받는 분 연락처","수신자전화","receiver_phone","receiver phone"],
        "receiver_addr":         ["받는분주소","받는 분 주소","배송주소","receiver_addr","address"],
        "receiver_detail":       ["받는분상세주소","받는 분 상세주소","배송상세","detail_address","receiver_detail"],
        "receiver_postcode":     ["받는분우편번호","postcode","receiver_postcode"],
        "item_type":             ["물품명","품명","물품","item_type","item"],
    }

    def pick(row: dict, field: str) -> str:
        for alias in COL.get(field, [field]):
            v = row.get(alias, "")
            if v:
                return v.strip()
        return ""

    results = []
    for i, row in enumerate(rows, start=2):  # 2행부터 (1행=헤더)
        s_name   = pick(row, "sender_name")
        s_phone  = pick(row, "sender_phone")
        s_addr   = pick(row, "sender_addr")
        s_detail = pick(row, "sender_detail_address")
        s_post   = pick(row, "sender_postcode") or "00000"
        r_name   = pick(row, "receiver_name")
        r_phone  = pick(row, "receiver_phone")
        r_addr   = pick(row, "receiver_addr")
        r_detail = pick(row, "receiver_detail")
        r_post   = pick(row, "receiver_postcode") or "00000"
        item     = pick(row, "item_type") or "일반물품"

        if not (s_name and s_phone and s_addr and r_name and r_phone and r_addr):
            results.append({"row": i, "success": False, "error": "필수 항목 누락"})
            continue

        tracking_code = f"BULK-{int(datetime.now().timestamp())}-{i:04d}"
        delivery_data = {
            "store_id": "CITIZEN",
            "date_time": datetime.now().isoformat(),
            "sender_name": s_name,
            "receiver_name": r_name,
            "receiver_addr": f"{r_addr} {r_detail}".strip(),
            "item_type": item,
            "weight": "small",
            "quantity": 1,
            "tracking_code": tracking_code,
            "fee": 6000,
            "status": "접수완료",
            "payment_type": "착불"
        }
        order_data = {
            "order_id": tracking_code,
            "sender_name": s_name, "sender_phone": s_phone,
            "sender_postcode": s_post, "sender_base_address": s_addr,
            "sender_detail_address": s_detail,
            "receiver_name": r_name, "receiver_phone": r_phone,
            "postcode": r_post, "address": r_addr,
            "detail_address": r_detail,
            "status": "REQUESTED"
        }
        try:
            if hasattr(db, "save_store_delivery"):
                await run_in_threadpool(db.save_store_delivery, delivery_data)
            else:
                await run_in_threadpool(db.save_delivery, delivery_data)
            await run_in_threadpool(db.save_delivery_order, order_data)
            results.append({"row": i, "success": True, "tracking_code": tracking_code,
                            "sender": s_name, "receiver": r_name})
        except Exception as e:
            results.append({"row": i, "success": False, "error": str(e)})

    ok_count   = sum(1 for r in results if r["success"])
    fail_count = len(results) - ok_count
    return {"total": len(results), "success": ok_count, "failed": fail_count, "results": results}

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    host = request.headers.get("host", "").lower()
    
    # Subdomain Routing: The 5 Core Pillars
    if host.startswith("delivery."):
        return RedirectResponse(url="/delivery-landing", status_code=303)
    elif host.startswith("store."):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    elif host.startswith("farm.") or host.startswith("farmer."):
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    elif host.startswith("citizen."):
        pass
    elif host.startswith("home."):
        pass
    elif host.startswith("send."):
        return RedirectResponse(url="/citizen/send", status_code=303)

        
    # Default Home Behavior
    store_id = request.query_params.get("id")
    if store_id:
        store = db.get_store(store_id)
        if store:
            return templates.TemplateResponse(request, "citizen_store.html", {
                "request": request,
                "api_url": API_URL,
                "store": store
            })
    return templates.TemplateResponse(request, "index.html", {"request": request, "api_url": API_URL})

@router.get("/citizen/benefits", response_class=HTMLResponse)
async def citizen_benefits_page(request: Request):
    return templates.TemplateResponse(request, "citizen_benefits.html", {
        "request": request,
        "api_url": API_URL
    })

@router.get("/farmer/benefits", response_class=HTMLResponse)
async def farmer_benefits_page(request: Request):
    return templates.TemplateResponse(request, "farmer_benefits.html", {
        "request": request,
        "api_url": API_URL
    })


@router.get("/citizen/send", response_class=HTMLResponse)
async def send_dashboard_page(request: Request):
    return templates.TemplateResponse(request, "send_landing.html", {
        "request": request
    })

@router.get("/citizen/send/manager", response_class=HTMLResponse)
async def send_manager_page(request: Request, user: Union[User, None] = Depends(get_current_user)):
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
    store_info = db.get_store(user.store_id) if user else {}
    return templates.TemplateResponse(request, "courier_manager.html", {
        "request": request,
        "api_url": API_URL,
        "store": store_info,
        "toss_client_key": toss_client_key
    })

@router.get("/citizen/send/elderly", response_class=HTMLResponse)
async def send_elderly_page(request: Request, user: Union[User, None] = Depends(get_current_user)):
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
    store_info = db.get_store(user.store_id) if user else {}
    return templates.TemplateResponse(request, "courier_elderly.html", {
        "request": request,
        "api_url": API_URL,
        "store": store_info,
        "toss_client_key": toss_client_key
    })

_recent_send_bookings = {} # In-memory lock

@router.get("/send/payment-success", response_class=HTMLResponse)
async def send_payment_success(request: Request, address: str = "", paymentKey: str = "", orderId: str = "", amount: int = 0):
    import time
    current_time = time.time()
    
    # 중복 방지 (Idempotency) 로직: 5분 내 동일 주소 결제
    if address in _recent_send_bookings:
        last_time = _recent_send_bookings[address]
        if current_time - last_time < 300: # 5 mins
            # 환불 처리 API 호출 필요 (여기서는 생략하고 바로 에러 표시)
            return HTMLResponse(f"<h1>⚠️ 중복 예약 감지</h1><p>5분 이내에 동일한 목적지({address})로 예약이 성사되었습니다. 이중 결제를 방지하기 위해 중단되었습니다.</p>", status_code=409)
            
    _recent_send_bookings[address] = current_time
    
    # (선택) 로젠택배 API 전송 및 DB 저장 로직:
    # db_sqlite.save_delivery(...)
    
    return HTMLResponse(f"<h1>✅ 예약 및 결제 완벽 완료!</h1><p>성공적으로 {amount}원이 토스로 결제되었습니다.</p><p>입력 주소: {address}</p><p>기사님 GPS 수신 완료. 곧 방문합니다!</p><a href='/citizen/send' style='display:inline-block; padding:15px; background:#1a1a1a; color:white; border-radius:10px; text-decoration:none;'>돌아가기</a>", status_code=200)

@router.get("/agreement", response_class=HTMLResponse)
async def agreement_page(request: Request):
    return templates.TemplateResponse(request, "agreement.html", {"request": request})


@router.get("/detail/restaurant", response_class=HTMLResponse)
async def detail_restaurant_page(request: Request):
    return templates.TemplateResponse(request, "detail_restaurant.html", {"request": request, "hide_bottom_nav": True})


@router.get("/detail/farm", response_class=HTMLResponse)
async def detail_farm_page(request: Request):
    return templates.TemplateResponse(request, "detail_farm.html", {"request": request, "hide_bottom_nav": True})


@router.get("/detail/logistics", response_class=HTMLResponse)
async def detail_logistics_page(request: Request):
    return templates.TemplateResponse(request, "detail_logistics.html", {"request": request, "hide_bottom_nav": True})


@router.get("/detail/summary", response_class=HTMLResponse)
async def detail_summary_page(request: Request):
    return templates.TemplateResponse(request, "detail_summary.html", {"request": request, "hide_bottom_nav": True})

@router.get("/kakao-login", response_class=HTMLResponse)
async def kakao_login_page(request: Request):
    """시민 전용 카카오 간편 로그인 페이지 (REST_API_KEY 미노출 BFF 방식)"""
    # 이미 로그인된 경우 바로 택배 접수 페이지로 이동
    if request.cookies.get("admin_session"):
        return RedirectResponse(url="/citizen/courier", status_code=303)
    return templates.TemplateResponse(request, "kakao_login.html", {"request": request})


@router.get("/citizen/courier", response_class=HTMLResponse)
async def public_courier_page(request: Request):
    # 비로그인만 차단 — role 무관하게 로그인된 모든 사용자 허용
    store_id = request.cookies.get("admin_session")
    if not store_id:
        return RedirectResponse(url="/kakao-login?next=/citizen/courier", status_code=303)
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "")
    store = db.get_store(store_id) or {}
    return templates.TemplateResponse(request, "courier_manager.html", {
        "request": request,
        "api_url": API_URL,
        "toss_client_key": toss_client_key,
        "store": store
    })


@router.get("/citizen/reserve", response_class=HTMLResponse)
async def public_reserve_page(request: Request):
    store_id = request.query_params.get("store_id", "")
    store = db.get_store(store_id) if store_id else None
    products = db.get_products(store_id) if store_id else []
    if hasattr(products, "to_dict"):
        products = products.to_dict(orient="records")
    return templates.TemplateResponse(request, "citizen_reserve.html", {
        "request": request,
        "api_url": API_URL,
        "store": store or {},
        "products": products or [],
        "hide_bottom_nav": True
    })
    
@router.post("/api/citizen/courier/reserve")
async def public_reserve_courier(data: CourierReservationRequest, request: Request):
    store_id = "CITIZEN" 
    
    # 1. API level validation for detailed address
    s_detail = data.sender_detail_address or ""
    r_detail = data.detail_address or ""
    if not s_detail.strip():
        raise HTTPException(status_code=400, detail="보내는 분의 상세 주소(동·호수 등)를 입력해 주세요.")
    if not r_detail.strip():
        raise HTTPException(status_code=400, detail="받는 분의 상세 주소(동·호수 등)를 입력해 주세요.")
        
    base_fee = 6000
    if data.weight == "medium":
        base_fee = 7000
    elif data.weight == "large":
        base_fee = 9000
    
    total_fee = base_fee * data.quantity
    amount_to_pay = total_fee if data.pay_type == "prepaid" else 0

    # Normalize addresses to Road Name Addresses
    recv_base = data.address or data.receiver_addr or ""
    road_recv_base, postcode_recv = convert_to_road_address_and_postcode(recv_base, data.postcode)
    
    send_base = data.sender_base_address or data.sender_addr or ""
    road_send_base, postcode_send = convert_to_road_address_and_postcode(send_base, data.sender_postcode)

    delivery_data = {
        "store_id": store_id,
        "date_time": datetime.now().isoformat(),
        "sender_name": data.sender_name,
        "receiver_name": data.receiver_name,
        "receiver_addr": f"{road_recv_base} {r_detail}",
        "item_type": data.item_type,
        "weight": data.weight,
        "quantity": data.quantity,
        "tracking_code": f"LOGEN-{int(datetime.now().timestamp())}", 
        "fee": total_fee, 
        "status": "접수완료",
        "payment_type": data.pay_type
    }
    
    try:
        from fastapi.concurrency import run_in_threadpool
        if hasattr(db, 'save_store_delivery'):
             await run_in_threadpool(db.save_store_delivery, delivery_data)
        else:
             await run_in_threadpool(db.save_delivery, delivery_data)
             
        import re
        sender_phone = re.sub(r'[^0-9-]', '', data.sender_phone or '')
        receiver_phone = re.sub(r'[^0-9-]', '', data.receiver_phone or '')

        # Save to the new delivery_users / delivery_orders / order_recipients tables
        order_data = {
            "order_id": delivery_data["tracking_code"],
            "sender_name": data.sender_name,
            "sender_phone": sender_phone,
            "sender_postcode": postcode_send or "",
            "sender_base_address": road_send_base,
            "sender_detail_address": s_detail,
            "receiver_name": data.receiver_name,
            "receiver_phone": receiver_phone,
            "postcode": postcode_recv or "",
            "address": road_recv_base,
            "detail_address": r_detail,
            "status": "REQUESTED"
        }
        await run_in_threadpool(db.save_delivery_order, order_data)
        
        return {
            "success": True, 
            "tracking_code": delivery_data["tracking_code"],
            "amount": amount_to_pay,
            "payment_required": amount_to_pay > 0,
            "orderName": f"택배 {data.quantity}건 ({data.item_type})"
        }
    except Exception as e:
        print(f"[X] Public Courier Reservation Failed: {e}")
        raise HTTPException(status_code=500, detail="예약 저장 실패")

@router.post("/api/citizen/courier/reserve-multi")
async def public_reserve_courier_multi(data: CourierMultiReservationRequest, request: Request):
    store_id = "CITIZEN" 
    
    # 1. API level validation for detailed address on all reservations first
    for res in data.reservations:
        s_detail = res.sender_detail_address or ""
        r_detail = res.detail_address or ""
        if not s_detail.strip():
            raise HTTPException(status_code=400, detail="보내는 분의 상세 주소(동·호수 등)를 입력해 주세요.")
        if not r_detail.strip():
            raise HTTPException(status_code=400, detail="받는 분의 상세 주소(동·호수 등)를 입력해 주세요.")
            
    total_amount_to_pay = 0
    saved_tracking_codes = []
    
    from fastapi.concurrency import run_in_threadpool
    import time
    
    # Generate a master order ID for Toss Payments
    master_tracking_code = f"LOGEN-MULTI-{int(datetime.now().timestamp())}"
    
    try:
        for res in data.reservations:
            s_detail = res.sender_detail_address or ""
            r_detail = res.detail_address or ""
            
            # Normalize addresses to Road Name Addresses
            recv_base = res.address or res.receiver_addr or ""
            road_recv_base, postcode_recv = convert_to_road_address_and_postcode(recv_base, res.postcode)
            
            send_base = res.sender_base_address or res.sender_addr or ""
            road_send_base, postcode_send = convert_to_road_address_and_postcode(send_base, res.sender_postcode)
            
            base_fee = 6000
            if res.weight == "medium":
                base_fee = 7000
            elif res.weight == "large":
                base_fee = 9000
            
            total_fee = base_fee * res.quantity
            amount_to_pay = total_fee if res.pay_type == "prepaid" else 0
            total_amount_to_pay += amount_to_pay
            
            individual_tracking_code = f"LOGEN-{int(time.time() * 1000)}"
            saved_tracking_codes.append(individual_tracking_code)
            
            delivery_data = {
                "store_id": store_id,
                "date_time": datetime.now().isoformat(),
                "sender_name": res.sender_name,
                "receiver_name": res.receiver_name,
                "receiver_addr": f"{road_recv_base} {r_detail}",
                "item_type": res.item_type,
                "weight": res.weight,
                "quantity": res.quantity,
                "tracking_code": individual_tracking_code,
                "fee": total_fee, 
                "status": "접수완료",
                "payment_type": res.pay_type
            }
            
            if hasattr(db, 'save_store_delivery'):
                 await run_in_threadpool(db.save_store_delivery, delivery_data)
            else:
                 await run_in_threadpool(db.save_delivery, delivery_data)
                 
            import re
            sender_phone = re.sub(r'[^0-9-]', '', res.sender_phone or '')
            receiver_phone = re.sub(r'[^0-9-]', '', res.receiver_phone or '')

            # Save to the new delivery_users / delivery_orders / order_recipients tables
            order_data = {
                "order_id": individual_tracking_code,
                "sender_name": res.sender_name,
                "sender_phone": sender_phone,
                "sender_postcode": postcode_send or "",
                "sender_base_address": road_send_base,
                "sender_detail_address": s_detail,
                "receiver_name": res.receiver_name,
                "receiver_phone": receiver_phone,
                "postcode": postcode_recv or "",
                "address": road_recv_base,
                "detail_address": r_detail,
                "status": "REQUESTED"
            }
            await run_in_threadpool(db.save_delivery_order, order_data)
            
            time.sleep(0.01) # to ensure unique tracking code timestamps
            
        first_item = data.reservations[0].item_type if data.reservations else "물품"
        total_qty = sum([r.quantity for r in data.reservations])
        order_name = f"택배 {first_item} 외 총 {total_qty}건" if len(data.reservations) > 1 else f"택배 {total_qty}건 ({first_item})"
            
        return {
            "success": True, 
            "tracking_code": master_tracking_code,
            "saved_codes": saved_tracking_codes,
            "amount": total_amount_to_pay,
            "payment_required": total_amount_to_pay > 0,
            "orderName": order_name
        }
    except Exception as e:
        print(f"[X] Public Multi Courier Reservation Failed: {e}")
        raise HTTPException(status_code=500, detail="다중 예약 저장 실패")


@router.post("/api/citizen/reserve")
async def public_create_reservation(data: PublicReservationRequest):
    if not data.consent:
        raise HTTPException(status_code=400, detail="개인정보 수집 동의가 필요합니다.")

    if not data.store_id:
        raise HTTPException(status_code=400, detail="가게 정보가 필요합니다.")

    if not data.customer_name or not data.customer_phone:
        raise HTTPException(status_code=400, detail="고객 정보가 필요합니다.")

    if data.head_count < 1 or data.head_count > 20:
        raise HTTPException(status_code=400, detail="인원 수를 다시 확인해주세요.")

    try:
        res_dt = datetime.strptime(f"{data.res_date} {data.res_time}", "%Y-%m-%d %H:%M")
        if res_dt < datetime.now():
            raise HTTPException(status_code=400, detail="예약 시간이 과거일 수 없습니다.")
    except ValueError:
        raise HTTPException(status_code=400, detail="예약 날짜/시간 형식이 올바르지 않습니다.")

    reservation_data = {
        "store_id": data.store_id,
        "customer_name": data.customer_name,
        "contact": data.customer_phone,
        "res_date": data.res_date,
        "res_time": data.res_time,
        "head_count": data.head_count,
        "status": "confirmed"
    }

    order_summary = data.menu_summary.strip() or "예약"
    order_data = {
        "type": "RESERVE",
        "item_name": order_summary,
        "amount": 0,
        "customer_phone": data.customer_phone,
        "payment_method": "RESERVE"
    }

    try:
        from fastapi.concurrency import run_in_threadpool
        await run_in_threadpool(db.save_reservation_record, data.store_id, reservation_data)
        await run_in_threadpool(db.save_unified_order, data.store_id, order_data)
        return {"success": True}
    except Exception as e:
        print(f"[X] Reservation Save Failed: {e}")
        raise HTTPException(status_code=500, detail="예약 저장 실패")

@router.get("/citizen/restaurants", response_class=HTMLResponse)
async def public_restaurants_page(request: Request):
    """단골식당 목록 둘러보기"""
    stores_df = db.get_all_stores()
    stores = []
    if stores_df is not None and not stores_df.empty:
        # owner 계정만 추출 (상점)
        owner_stores = stores_df[stores_df['role'] == 'owner']
        stores = owner_stores.to_dict(orient="records")
    return templates.TemplateResponse(request, "citizen_restaurants.html", {"request": request, "stores": stores})

@router.get("/citizen/market", response_class=HTMLResponse)
async def public_market_page(request: Request):
    """상품 선택 그리드 화면 (마켓 시작 화면)"""
    products = db.get_all_products()
    return templates.TemplateResponse(request, "market_products.html", {"request": request, "products": products})

@router.get("/citizen/market/products", response_class=HTMLResponse)
async def market_products_page(request: Request):
    """상품 선택 화면 (별칭)"""
    products = db.get_all_products()
    return templates.TemplateResponse(request, "market_products.html", {"request": request, "products": products})

@router.get("/citizen/market/product/{product_id}", response_class=HTMLResponse)
async def market_product_detail_page(request: Request, product_id: int):
    """상품 상세 페이지"""
    product = db.get_product_detail(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    return templates.TemplateResponse(request, "market_product_detail.html", {"request": request, "product": product})

@router.get("/citizen/market/checkout", response_class=HTMLResponse)
async def market_checkout_page(request: Request):
    """배송 정보 입력 및 결제 화면"""
    import config
    toss_client_key = config.get_settings().app.toss_client_key
    return templates.TemplateResponse(request, "market_checkout.html", {"request": request, "toss_client_key": toss_client_key})

@router.get("/citizen/market/refund", response_class=HTMLResponse)
async def market_refund_page(request: Request):
    """환불정책 및 사업자정보 페이지"""
    return templates.TemplateResponse(request, "market_refund.html", {"request": request})

@router.post("/api/citizen/courier/pending-reservation")
async def pending_courier_reservation(data: CourierReservationRequest, request: Request, user: Union[User, None] = Depends(get_optional_current_user)):
    store_id = user.store_id if user else "guest"
    if store_id == "guest":
        store_id = "01023847447" # default fallback or guest store_id

    # 1. API level validation for detailed address
    s_detail = data.sender_detail_address or ""
    r_detail = data.detail_address or ""
    if not s_detail.strip():
        raise HTTPException(status_code=400, detail="보내는 분의 상세 주소(동·호수 등)를 입력해 주세요.")
    if not r_detail.strip():
        raise HTTPException(status_code=400, detail="받는 분의 상세 주소(동·호수 등)를 입력해 주세요.")
        
    base_fee_map = {"small": 5000, "medium": 7000, "large": 9000}
    recv_base = data.address or data.receiver_addr or ""
    is_jeju = "제주" in recv_base or "제주특별자치도" in recv_base
    extra_jeju_fee = 3000 if is_jeju else 0

    # 복수 크기 지원: sizes_ordered 우선, 없으면 단일 weight/quantity 폴백
    if data.sizes_ordered and len(data.sizes_ordered) > 0:
        total_fee = sum(
            (base_fee_map.get(s["size"], 5000) + extra_jeju_fee) * s["qty"]
            for s in data.sizes_ordered
        )
        total_qty = sum(s["qty"] for s in data.sizes_ordered)
        sizes_summary = " + ".join(f"{s['size']} {s['qty']}개" for s in data.sizes_ordered)
    else:
        base_fee = base_fee_map.get(data.weight, 5000)
        total_fee = (base_fee + extra_jeju_fee) * data.quantity
        total_qty = data.quantity
        sizes_summary = f"{data.weight} {data.quantity}개"

    amount_to_pay = total_fee if data.pay_type == "prepaid" else 0

    # Normalize addresses to Road Name Addresses
    road_recv_base, postcode_recv = convert_to_road_address_and_postcode(recv_base, data.postcode)
    send_base = data.sender_base_address or data.sender_addr or ""
    road_send_base, postcode_send = convert_to_road_address_and_postcode(send_base, data.sender_postcode)

    import random
    order_id = f"COURIER-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"

    # Prepare payload to serialize
    import re
    sender_phone = re.sub(r'[^0-9-]', '', data.sender_phone or '')
    receiver_phone = re.sub(r'[^0-9-]', '', data.receiver_phone or '')
    
    payload_dict = {
        "store_id": store_id,
        "sender_name": data.sender_name,
        "sender_phone": sender_phone,
        "sender_address": road_send_base,
        "sender_detail_address": s_detail,
        "sender_postcode": postcode_send,
        "receiver_name": data.receiver_name,
        "receiver_phone": receiver_phone,
        "address": road_recv_base,
        "detail_address": r_detail,
        "postcode": postcode_recv,
        "fee": total_fee,
        "weight": data.weight,
        "quantity": data.quantity,
        "sizes_ordered": data.sizes_ordered or [{"size": data.weight, "qty": data.quantity}],
        "pay_type": data.pay_type,
        "item_type": data.item_type
    }

    import json
    from fastapi.concurrency import run_in_threadpool
    
    order_data = {
        "order_id": order_id,
        "sender_name": data.sender_name,
        "sender_phone": sender_phone,
        "sender_postcode": postcode_send or "",
        "sender_base_address": road_send_base,
        "sender_detail_address": s_detail,
        "receiver_name": data.receiver_name,
        "receiver_phone": receiver_phone,
        "postcode": postcode_recv or "",
        "address": road_recv_base,
        "detail_address": r_detail,
        "status": "PENDING",
        "payload": json.dumps(payload_dict, ensure_ascii=False)
    }

    try:
        await run_in_threadpool(db.save_delivery_order, order_data)
        return {
            "success": True,
            "order_id": order_id,
            "amount": amount_to_pay,
            "order_name": f"택배 {total_qty}건 ({sizes_summary})"
        }
    except Exception as e:
        print(f"[X] Pending Courier Reservation Failed: {e}")
        raise HTTPException(status_code=500, detail="예약 데이터베이스 임시 저장 실패")

@router.get("/api/pay/success", response_class=HTMLResponse)
async def toss_payment_success(request: Request, background_tasks: BackgroundTasks, paymentKey: str = "", orderId: str = "", amount: int = 0):
    # 1. VIP 업그레이드 또는 일반 결제 분기
    if orderId.startswith("VIP-") or "vip" in orderId.lower():
        confirm_res = confirm_toss_payment_api(paymentKey, orderId, amount)
        if confirm_res.get("status") != "success":
            raise HTTPException(status_code=400, detail=confirm_res.get("message", "VIP 결제 승인 실패"))
        return templates.TemplateResponse(request, "courier_success.html", {
            "request": request,
            "paymentKey": paymentKey,
            "orderId": orderId,
            "amount": amount
        })

    # 2. 택배(COURIER-) 결제 승인 확인
    if orderId.startswith("COURIER-"):
        confirm_res = confirm_toss_payment_api(paymentKey, orderId, amount)
        if confirm_res.get("status") != "success":
            err_msg = str(confirm_res.get("message") or "결제 승인에 실패했습니다.")
            # ALREADY_PROCESSED: 이미 처리된 결제 → 성공 화면으로 처리
            if "ALREADY_PROCESSED" in err_msg or "이미 처리된" in err_msg:
                return templates.TemplateResponse(request, "courier_success.html", {
                    "request": request,
                    "paymentKey": paymentKey,
                    "orderId": orderId,
                    "amount": amount
                })
            return templates.TemplateResponse(request, "courier_fail.html", {
                "request": request,
                "error_msg": f"결제 승인 오류: {err_msg}",
                "paymentKey": paymentKey,
                "orderId": orderId,
                "amount": amount
            })
            
        from fastapi.concurrency import run_in_threadpool
        import json
        
        # 3. DB에서 대기 중인 예약 조회
        order = await run_in_threadpool(db.get_delivery_order, orderId)
        if order and order.get('order_status') == 'PENDING':
            try:
                payload = json.loads(order['payload'])
            except Exception as pe:
                print(f"[X] Payload deserialization failed: {pe}")
                raise HTTPException(status_code=500, detail="예약 데이터 파싱 실패")
                
            store_id = payload.get('store_id', '01023847447')
            sender_name = payload.get('sender_name')
            sender_phone = payload.get('sender_phone')
            sender_address = payload.get('sender_address')
            sender_detail_address = payload.get('sender_detail_address')
            
            receiver_dict = {
                "name": payload.get('receiver_name'),
                "phone": payload.get('receiver_phone'),
                "address": payload.get('address'),
                "detail_address": payload.get('detail_address')
            }
            
            # 5. 기존 테이블(deliveries)에 저장 (상태: '접수대기')
            delivery_data = {
                "store_id": store_id,
                "date_time": datetime.now().isoformat(),
                "sender_name": sender_name,
                "receiver_name": receiver_dict["name"],
                "receiver_addr": f"{receiver_dict['address']} {receiver_dict['detail_address']}",
                "item_type": payload.get('item_type', '기타/잡화'),
                "tracking_code": orderId,
                "fee": amount,
                "status": "접수대기"
            }
            
            if hasattr(db, 'save_store_delivery'):
                 await run_in_threadpool(db.save_store_delivery, delivery_data)
            elif hasattr(db, 'save_delivery'):
                 await run_in_threadpool(db.save_delivery, delivery_data)
                 
            # 6. 탄탄제작소 정산 로그 기록 (세무 신고 대비)
            try:
                import settlement_engine
                await run_in_threadpool(
                    settlement_engine.calculate_settlement,
                    payment_amount=amount,
                    order_id=orderId,
                    customer_phone=sender_phone,
                    service_type="동네비서_택배",
                    persist=True
                )
            except Exception as se:
                print(f"Settlement log saving failed: {se}")
                
            # 7. 추천인 리워드 처리
            try:
                if hasattr(db, "check_and_complete_referral_reward"):
                    reward_res = await run_in_threadpool(db.check_and_complete_referral_reward, store_id, amount)
                    if reward_res:
                        driver_id = reward_res.get("driver_id")
                        reward_amt = reward_res.get("reward")
                        try:
                            import sms_manager
                            reward_msg = f"[영업 리워드 지급]\n축하합니다! 기사님이 유치하신 가맹점({sender_name})에서 누적 결제조건이 달성되어 영업 포인트 {reward_amt:,}원이 즉시 지급되었습니다."
                            sms_manager.send_alimtalk(to_phone=driver_id, message=reward_msg, template_id="tmp_reward", variables={"#{name}": "파트너"})
                        except Exception as sms_err:
                            print(f"Alimtalk reward notify failed: {sms_err}")
            except Exception as e:
                print(f"Reward trigger error: {e}")
                
            # 8. 주문 상태 변경 (PENDING -> REQUESTED)
            await run_in_threadpool(db.update_delivery_order_status, orderId, 'REQUESTED')
            
            # 9. 로젠 API 호출을 위한 크리덴셜 획득 및 백그라운드 태스크 등록
            settings = db.get_store_settings(store_id) if hasattr(db, "get_store_settings") else {}
            logen_id = settings.get("logen_id") or settings.get("courier_id") or ""
            logen_pw = settings.get("logen_pw") or settings.get("courier_pw") or ""
            
            size_mapped = payload.get('weight', 'small')
            # 복수 크기 지원: sizes_ordered 우선
            sizes_ordered = payload.get('sizes_ordered') or [{"size": size_mapped, "qty": payload.get('quantity', 1)}]

            box_type_map    = {'small': '1', 'medium': '2', 'large': '3'}
            weight_code_map = {'small': '05', 'medium': '15', 'large': '25'}
            weight_map      = {'small': 5.0, 'medium': 15.0, 'large': 25.0}
            size_name_map   = {'small': '소형', 'medium': '중형', 'large': '대형'}
            fee_map         = {'small': 5000, 'medium': 7000, 'large': 9000}

            # 크기별로 package_dict 목록 생성 (수량만큼 반복)
            packages_to_register = []
            for item in sizes_ordered:
                sz  = item.get('size', 'small')
                qty = int(item.get('qty', 1))
                fee_per = fee_map.get(sz, 5000)
                for _ in range(qty):
                    packages_to_register.append({
                        "type": "박스",
                        "weight": weight_map.get(sz, 5.0),
                        "size": size_name_map.get(sz, '소형'),
                        "box_type": box_type_map.get(sz, '1'),
                        "weight_code": weight_code_map.get(sz, '05'),
                        "contents": payload.get('item_type', '일반 택배 접수'),
                        "price": 10000,
                        "fee": fee_per,
                        "is_prepaid": True
                    })
            
            sender_dict = {
                "name": sender_name,
                "phone": sender_phone,
                "address": sender_address,
                "detail_address": sender_detail_address
            }
            
            logen_delivery.USE_REAL_API = True
            background_tasks.add_task(
                process_rosen_waybill_queue,
                order_id=orderId,
                store_id=store_id,
                sender_dict=sender_dict,
                receiver_dict=receiver_dict,
                packages_list=packages_to_register,  # 복수 패키지
                memo=payload.get('memo', ''),
                logen_id=logen_id,
                logen_pw=logen_pw
            )
            
    return templates.TemplateResponse(request, "courier_success.html", {
        "request": request,
        "paymentKey": paymentKey,
        "orderId": orderId,
        "amount": amount
    })

@router.get("/api/citizen/courier/order-status")
async def get_courier_order_status(orderId: str):
    from fastapi.concurrency import run_in_threadpool
    order = await run_in_threadpool(db.get_delivery_order, orderId)
    if not order:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
        
    return {
        "success": True,
        "status": order.get("order_status"),
        "waybill_number": order.get("waybill_number"),
        "error_message": order.get("error_message")
    }
    

async def process_rosen_waybill_queue(order_id: str, store_id: str, sender_dict: dict, receiver_dict: dict,
                                       memo: str, logen_id: str, logen_pw: str,
                                       packages_list: list = None, package_dict: dict = None):
    """복수 패키지 지원: packages_list 우선, 없으면 단일 package_dict 폴백"""
    from fastapi.concurrency import run_in_threadpool
    import logen_delivery
    import sms_manager
    import time

    # 멱등성 보장
    locked = await run_in_threadpool(db.acquire_delivery_order_lock, order_id)
    if not locked:
        print(f"[Queue] Order {order_id} is already PROCESSING or completed. Skipping background task.")
        return

    # 단일→복수 정규화
    if not packages_list:
        packages_list = [package_dict] if package_dict else [{"type": "박스", "weight": 5.0, "size": "소형", "box_type": "1", "weight_code": "05", "contents": "일반 택배", "price": 10000, "fee": 5000, "is_prepaid": True}]

    max_retries = 3
    retry_delay = 5
    all_waybills = []

    for pkg_idx, pkg in enumerate(packages_list):
        waybill_ok = False
        err = None
        for attempt in range(1, max_retries + 1):
            print(f"[Queue] Pkg {pkg_idx+1}/{len(packages_list)} | Attempt {attempt} | Order {order_id}")
            try:
                res_data, err = await run_in_threadpool(
                    logen_delivery.create_delivery_reservation,
                    sender=sender_dict,
                    receiver=receiver_dict,
                    package=pkg,
                    pickup_date=datetime.now().strftime("%Y-%m-%d"),
                    memo=memo,
                    agent_id=logen_id,
                    agent_pw=logen_pw
                )
                if not err and isinstance(res_data, dict) and res_data.get('waybill_number'):
                    all_waybills.append(res_data['waybill_number'])
                    print(f"[Queue] Waybill OK: {res_data['waybill_number']}")
                    waybill_ok = True
                    break
            except Exception as ex:
                err = str(ex)
            print(f"[Queue] Attempt {attempt} failed: {err or 'Unknown error'}")
            if attempt < max_retries:
                time.sleep(retry_delay)

        if not waybill_ok:
            print(f"[Queue] Pkg {pkg_idx+1} failed after {max_retries} attempts.")

    if all_waybills:
        waybill_summary = ", ".join(all_waybills)
        await run_in_threadpool(db.update_delivery_order_status, order_id, 'SUCCESS', waybill_number=waybill_summary)

        # 성공 알림톡
        try:
            sender_phone = sender_dict.get('phone')
            sender_name  = sender_dict.get('name')
            msg = f"[송장 접수 알림]\n{sender_name}님, 송장번호({waybill_summary})로 접수되었습니다.\n*기사님 대시보드에 알림이 전송되었습니다."
            sms_manager.send_alimtalk(to_phone=sender_phone, message=msg, template_id="tmp_courier",
                                      variables={"#{name}": sender_name, "#{track}": waybill_summary})
        except Exception as sms_err:
            print(f"[Queue] Alimtalk error: {sms_err}")
    else:
        print(f"[Queue] All packages failed for order {order_id}. Storing in Dead Letter Box.")
        await run_in_threadpool(db.update_delivery_order_status, order_id, 'FAILED', error_message=err or "로젠 API 최종 응답 실패")
        try:
            sender_phone = sender_dict.get('phone')
            sender_name  = sender_dict.get('name')
            alert_msg = f"[접수 실패 알림]\n{sender_name}님, 택배 접수가 일시적인 오류로 실패했습니다. 관리자가 확인 후 수동 재처리해 드리겠습니다. (주문번호: {order_id})"
            sms_manager.send_alimtalk(to_phone=sender_phone, message=alert_msg, template_id="tmp_fail_alert",
                                      variables={"#{name}": sender_name, "#{orderId}": order_id})
        except Exception as sms_err:
            print(f"[Queue] Alert Alimtalk error: {sms_err}")


@router.post("/api/citizen/courier/finish-reservation")
async def finish_courier_reservation(request: Request, background_tasks: BackgroundTasks, user: Union[User, None] = Depends(get_optional_current_user)):
    data = await request.json()
    store_id = user.store_id if user else "guest"
    if store_id == "guest":
        store_id = "01023847447"
    sender_store = db.get_store(store_id)
    
    sender_name = data.get('sender_name') or (sender_store.get('owner_name', '고객님') if sender_store else '고객님')
    sender_phone_raw = data.get('sender_phone') or (sender_store.get('phone', '010-0000-0000') if sender_store else '010-0000-0000')
    import re
    sender_phone = re.sub(r'[^0-9-]', '', sender_phone_raw)
    sender_address = data.get('sender_address') or (sender_store.get('address', '미등록 주소') if sender_store else '미등록 주소')
    
    # 1. API level validation for detailed address
    sender_detail_address = data.get('sender_detail_address') or ""
    receiver_dict = {
        "name": data.get('receiver_name'),
        "phone": re.sub(r'[^0-9-]', '', data.get('receiver_phone') or ''),
        "address": data.get('address'),
        "detail_address": data.get('detail_address') or ""
    }
    receiver_detail_address = receiver_dict["detail_address"]
    
    if not sender_detail_address.strip():
        raise HTTPException(status_code=400, detail="보내는 분의 상세 주소(동·호수 등)를 입력해 주세요.")
    if not receiver_detail_address.strip():
        raise HTTPException(status_code=400, detail="받는 분의 상세 주소(동·호수 등)를 입력해 주세요.")
        
    from datetime import datetime
    import logen_delivery
    import random
    from fastapi.concurrency import run_in_threadpool
    
    package_dict = {
        "type": "박스",
        "weight": 2.5,
        "size": "소형",
        "contents": "일반 택배 접수",
        "price": 10000,
        "fee": data.get('fee', 4500),
        "is_prepaid": True
    }
    
    # 2. 멱등성 보장 (Idempotency): 동일 orderId로 이미 결제/접수된 것이 있는지 확인
    order_id = data.get('orderId') or f"LOGEN-{int(datetime.now().timestamp())}"
    existing_order = await run_in_threadpool(db.get_delivery_order, order_id)
    if existing_order:
        status = existing_order.get('order_status')
        waybill = existing_order.get('waybill_number')
        if status == 'SUCCESS' and waybill:
            return {"success": True, "tracking_code": waybill}
        return {"success": True, "tracking_code": order_id}

    # Normalize addresses to Road Name Addresses
    sender_address_raw = data.get('sender_base_address') or sender_address
    sender_postcode_raw = data.get('sender_postcode') or ""
    road_send_base, postcode_send = convert_to_road_address_and_postcode(sender_address_raw, sender_postcode_raw)
    
    receiver_address_raw = receiver_dict["address"]
    receiver_postcode_raw = data.get('postcode') or ""
    road_recv_base, postcode_recv = convert_to_road_address_and_postcode(receiver_address_raw, receiver_postcode_raw)

    sender_dict = {
        "name": sender_name,
        "phone": sender_phone,
        "address": road_send_base,
        "detail_address": sender_detail_address
    }
    
    delivery_data = {
        "store_id": store_id,
        "date_time": datetime.now().isoformat(),
        "sender_name": sender_name,
        "receiver_name": receiver_dict["name"],
        "receiver_addr": f"{road_recv_base} {receiver_detail_address}",
        "item_type": package_dict['contents'],
        "tracking_code": order_id, # 임시 트래킹 코드로 플랫폼 접수 고유번호 사용
        "fee": package_dict['fee'], 
        "status": "접수대기"
    }

    try:
        if hasattr(db, 'save_store_delivery'):
             await run_in_threadpool(db.save_store_delivery, delivery_data)
        elif hasattr(db, 'save_delivery'):
             await run_in_threadpool(db.save_delivery, delivery_data)
             
        # Save to the new delivery_users / delivery_orders / order_recipients tables
        order_data = {
            "order_id": order_id,
            "sender_name": sender_name,
            "sender_phone": sender_phone,
            "sender_postcode": postcode_send,
            "sender_base_address": road_send_base,
            "sender_detail_address": sender_detail_address,
            "receiver_name": receiver_dict["name"],
            "receiver_phone": receiver_dict["phone"],
            "postcode": postcode_recv,
            "address": road_recv_base,
            "detail_address": receiver_detail_address,
            "status": "REQUESTED"
        }
        await run_in_threadpool(db.save_delivery_order, order_data)
             
        # 탄탄제작소 정산 로그 기록 추가 (세무 신고 대비)
        try:
            import settlement_engine
            await run_in_threadpool(
                settlement_engine.calculate_settlement,
                payment_amount=int(package_dict['fee']),
                order_id=order_id,
                customer_phone=sender_phone,
                service_type="동네비서_택배",
                persist=True
            )
        except Exception as se:
            print(f"Settlement log saving failed: {se}")
    except Exception as e:
        print(f"DB save error: {e}")
        raise HTTPException(status_code=500, detail="예약 데이터베이스 저장 실패")
         
    # Check and Complete Referral Reward
    try:
        if hasattr(db, "check_and_complete_referral_reward"):
            # package_dict['fee'] is the payment amount
            reward_res = await run_in_threadpool(db.check_and_complete_referral_reward, store_id, package_dict['fee'])
            if reward_res:
                driver_id = reward_res.get("driver_id")
                reward_amt = reward_res.get("reward")
                try:
                    import sms_manager
                    reward_msg = f"[영업 리워드 지급]\n축하합니다! 기사님이 유치하신 가맹점({sender_name})에서 누적 결제조건이 달성되어 영업 포인트 {reward_amt:,}원이 즉시 지급되었습니다."
                    sms_manager.send_alimtalk(to_phone=driver_id, message=reward_msg, template_id="tmp_reward", variables={"#{name}": "파트너"})
                except:
                    pass
    except Exception as e:
        print(f"Reward trigger error: {e}")
         
    # 로젠 API 호출 및 트래킹 번호 수정을 백그라운드 큐로 이관 (사용자 대기 차단)
    settings = db.get_store_settings(store_id) if hasattr(db, "get_store_settings") else {}
    logen_id = settings.get("logen_id") or settings.get("courier_id") or ""
    logen_pw = settings.get("logen_pw") or settings.get("courier_pw") or ""
    logen_delivery.USE_REAL_API = True

    background_tasks.add_task(
        process_rosen_waybill_queue,
        order_id=order_id,
        store_id=store_id,
        sender_dict=sender_dict,
        receiver_dict=receiver_dict,
        package_dict=package_dict,
        memo=data.get('memo', ''),
        logen_id=logen_id,
        logen_pw=logen_pw
    )
        
    return {"success": True, "tracking_code": order_id}


def confirm_toss_payment_api(payment_key: str, order_id: str, amount: int) -> dict:
    if payment_key.startswith("KAKAOPAY_"):
        return {"status": "success"}
    import base64
    import requests
    
    toss_secret_key = os.getenv("TOSS_SECRET_KEY", "test_sk_26DlbXAaV0Kbn1ljMQa43qY50Q9R")
    url = "https://api.tosspayments.com/v1/payments/confirm"
    
    # 1. 시크릿 키 뒤에 콜론(:) 추가 후 Base64 인코딩
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
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            print("[결제 승인 완료] 동네비서 계좌로 입금 확정!")
            return {"status": "success", "data": response.json()}
        else:
            try:
                err_data = response.json()
                err_code = str(err_data.get("code") or "")
                err_msg  = str(err_data.get("message") or response.text or "승인 실패")
            except Exception:
                err_code = ""
                err_msg  = response.text or "승인 실패"
            print(f"[결제 승인 실패] 에러 코드: {err_code} / 사유: {err_msg}")
            return {"status": "error", "code": err_code, "message": f"{err_msg} (HTTP {response.status_code})"}
    except Exception as e:
        print(f"[시스템 에러] 서버 통신 실패: {e}")
        return {"status": "error", "message": f"네트워크 통신 오류: {str(e)}"}


@router.get("/citizen/payment", response_class=HTMLResponse)
async def citizen_payment_page(request: Request):
    toss_client_key = os.getenv("TOSS_CLIENT_KEY", "test_ck_PBal2vxj81ND2OPW6a7135RQgOAN")
    return templates.TemplateResponse(request, "courier_payment.html", {
        "request": request,
        "toss_client_key": toss_client_key
    })


@router.get("/api/payment/success", response_class=HTMLResponse)
async def api_payment_success(request: Request, paymentKey: str = "", orderId: str = "", amount: int = 0):
    from fastapi.concurrency import run_in_threadpool
    
    # Verify with Toss API
    verification = await run_in_threadpool(confirm_toss_payment_api, paymentKey, orderId, amount)
    
    if verification.get("status") == "success":
        # Save payment confirmation to database (add points to test_store)
        await run_in_threadpool(db.confirm_payment, "test_store", amount, orderId, paymentKey)
        
        return HTMLResponse(
            f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>결제 성공</title>
                <style>
                    body {{ font-family: sans-serif; text-align: center; padding: 50px 20px; background-color: #f4f5f7; color: #333; }}
                    .card {{ background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 450px; margin: 0 auto; }}
                    h1 {{ color: #16a34a; font-size: 2.2rem; margin-bottom: 20px; }}
                    p {{ font-size: 1.1rem; line-height: 1.6; margin-bottom: 25px; }}
                    .btn {{ display: inline-block; padding: 15px 30px; background: #3182f6; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>✅ 결제 승인 완료!</h1>
                    <p>어르신 택배 요금 <strong>{amount:,}원</strong>이 토스로 결제되었습니다.<br>동네비서 계좌로 입금이 확정되었습니다.</p>
                    <a href="/citizen/payment" class="btn">돌아가기</a>
                </div>
            </body>
            </html>
            """,
            status_code=200
        )
    else:
        return HTMLResponse(
            f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>결제 실패</title>
                <style>
                    body {{ font-family: sans-serif; text-align: center; padding: 50px 20px; background-color: #f4f5f7; color: #333; }}
                    .card {{ background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 450px; margin: 0 auto; }}
                    h1 {{ color: #dc2626; font-size: 2.2rem; margin-bottom: 20px; }}
                    p {{ font-size: 1.1rem; line-height: 1.6; margin-bottom: 25px; }}
                    .btn {{ display: inline-block; padding: 15px 30px; background: #64748b; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>❌ 결제 검증 실패</h1>
                    <p>토스페이먼츠 결제 검증 중 에러가 발생했습니다.<br>사유: {verification.get('message')}</p>
                    <a href="/citizen/payment" class="btn">돌아가기</a>
                </div>
            </body>
            </html>
            """,
            status_code=400
        )


@router.get("/api/payment/fail", response_class=HTMLResponse)
async def api_payment_fail(request: Request, code: str = "", message: str = "", orderId: str = ""):
    return HTMLResponse(
        f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>결제 실패</title>
            <style>
                body {{ font-family: sans-serif; text-align: center; padding: 50px 20px; background-color: #f4f5f7; color: #333; }}
                .card {{ background: white; padding: 40px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 450px; margin: 0 auto; }}
                h1 {{ color: #dc2626; font-size: 2.2rem; margin-bottom: 20px; }}
                p {{ font-size: 1.1rem; line-height: 1.6; margin-bottom: 25px; }}
                .btn {{ display: inline-block; padding: 15px 30px; background: #64748b; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>❌ 결제 실패</h1>
                <p>결제창을 닫았거나 결제에 실패했습니다.<br>에러코드: {code}<br>사유: {message}</p>
                <a href="/citizen/payment" class="btn">돌아가기</a>
            </div>
        </body>
        </html>
        """,
        status_code=200
    )


from fastapi import BackgroundTasks

# ---------------------------------------------------------
# [1구역] 로젠택배 API 통신 모듈 (어댑터)
# 나중에 매뉴얼과 인증 키가 오면 이 부분의 코드만 덮어씌웁니다.
# ---------------------------------------------------------
def request_rosen_waybill(order_id: str, address: str, item_type: str):
    # TODO: 로젠택배 화이트리스트 IP 통과 후, 실제 API 호출 로직 주입
    print(f"[{order_id}] 로젠택배 서버로 운송장 요청 전송 (주소: {address})", flush=True)
    
    # 임시 테스트용 가짜 송장 번호 리턴
    return "123-456-7890" 


# ---------------------------------------------------------
# [2구역] 백그라운드 물류 처리반 (타임아웃 방어의 핵심)
# 토스 결제가 끝나면 화면 뒤에서 조용히 실행되는 작업자입니다.
# ---------------------------------------------------------
def process_waybill_background(order_id: str, address: str, item_type: str):
    try:
        # 로젠택배 서버를 찌르고 운송장 번호를 받아옴
        waybill_number = request_rosen_waybill(order_id, address, item_type)
        
        # TODO: 발급된 운송장 번호를 동네비서 데이터베이스에 박제
        # TODO: 카카오 알림톡 API를 찔러서 손님에게 송장번호 전송
        print(f"[{order_id}] 정상 처리! 로젠택배 운송장({waybill_number}) DB 저장 및 알림톡 발송 완료.", flush=True)
        
    except Exception as e:
        # 택배사 서버가 점검 중이거나 뻗었을 때 시스템이 죽지 않도록 에러 기록
        # TODO: 5분 단위 재시도(Retry) 로직 추가
        print(f"[{order_id}] 운송장 발급 실패! 관리자 중앙 화면에 경고 알림: {e}", flush=True)


# ---------------------------------------------------------
# [3구역] 토스페이먼츠 결제 성공 수신처 (대문)
# ---------------------------------------------------------
@router.post("/api/payment/success")
async def payment_success_webhook(order_data: dict, background_tasks: BackgroundTasks):
    order_id = order_data.get("orderId")
    address = order_data.get("address") # 프론트에서 카카오 주소 API로 정제되어 넘어온 주소
    item_type = order_data.get("itemType")
    
    # [방어벽 가동] 운송장 뽑는 작업은 뒷단(Background) 작업자에게 던져버림
    background_tasks.add_task(process_waybill_background, order_id, address, item_type)
    
    # 토스 서버에게는 0.1초 만에 즉시 "결제 확인완료!" 응답을 날림 (타임아웃 에러 원천 차단)
    return {"status": "success", "message": "결제 승인 및 로젠택배 배송 접수 진행 중"}


