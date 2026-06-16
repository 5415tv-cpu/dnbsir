from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import db_manager as db
from .auth import get_current_user, User

router = APIRouter()

# ──────────────────────────────────────────────
# AI 택배 접수 파서 — 아하 모먼트(Aha Moment) API
# ──────────────────────────────────────────────
class CourierParseRequest(BaseModel):
    text: str

@router.post("/api/courier/parse")
async def parse_courier_input(req: CourierParseRequest):
    """
    비정형 자연어 택배 메시지를 구조화된 데이터로 즉시 파싱합니다.

    흐름:
      1. Regex 고속 파싱 (~0ms)
      2. 누락 필드 존재 시 Gemini Flash 보충 (타임아웃 3초)
      3. 결과 즉시 반환 — 에러 대신 누락 필드 안내 메시지

    요청 예시:
      {"text": "태백로 123 홍길동 010-1234-5678로 쌀 한 가마니 보내줘"}
    """
    text = req.text.strip()
    if not text:
        return {
            "success": False,
            "data": None,
            "warning": "입력 내용이 비어 있습니다."
        }

    # 입력 길이 제한 (방어: 과도한 입력으로 AI 과금 방지)
    if len(text) > 500:
        text = text[:500]

    try:
        from core_engine.courier_parser import parse_courier_text
        result = await parse_courier_text(text)
        return {
            "success": True,
            "data": result.to_dict(),
            "warning": result.warning_message
        }
    except Exception as e:
        print(f"[CourierParse] 파싱 오류: {e}")
        import traceback
        traceback.print_exc()
        # 실패해도 에러 대신 빈 결과 반환 (UX 최우선)
        return {
            "success": False,
            "data": None,
            "warning": "잠시 시스템이 응답하지 않습니다. 직접 입력해 주세요."
        }




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

@router.post("/api/courier/reserve")
async def reserve_courier(data: CourierReservationRequest, request: Request, user: User = Depends(get_current_user)):
    store_id = user.store_id
    print(f"📦 [Courier] Reservation Request from {store_id}: {data}")

    delivery_data = {
        "store_id": store_id,
        "date_time": datetime.now().isoformat(),
        "sender_name": data.sender_name,
        "receiver_name": data.receiver_name,
        "receiver_addr": f"{data.receiver_addr1} {data.receiver_addr2}",
        "item_type": data.item_type,
        "tracking_code": f"LOGEN-{int(datetime.now().timestamp())}", 
        "fee": 3000 * data.quantity, 
        "status": "접수완료"
    }
    
    try:
        from fastapi.concurrency import run_in_threadpool
        import logen_delivery
        import logen_crypto
        
        total_fee = 3000 * data.quantity
        margin_logic = logen_crypto.calculate_margin(total_fee)
        
        # 로젠택배 API에 전송할 데이터 구조 매핑 (플랫폼 수익이 완전히 제거된 원가만 담기)
        package_dict = {
            "type": "박스",
            "weight": 2.5,  # 폼에서 전달되지 않을 경우 임시값
            "size": "소형",
            "contents": data.item_type,
            "price": data.item_value,
            "fee": margin_logic['base_fee'], # 기사용 단말기에 찍힐 순수 원가 배송비
            "is_prepaid": data.payment_type == "prepaid" or data.payment_type == "선불"
        }
        
        sender_dict = {
            "name": data.sender_name,
            "phone": data.sender_phone,
            "address": data.sender_addr1,
            "detail_address": data.sender_addr2
        }
        
        receiver_dict = {
            "name": data.receiver_name,
            "phone": data.receiver_phone,
            "address": data.receiver_addr1,
            "detail_address": data.receiver_addr2
        }

        # DB에서 기사님(사장님)의 개별 로젠 계정 정보 조회
        settings = db.get_all_settings(store_id) if hasattr(db, "get_all_settings") else {}
        logen_id = settings.get("logen_id")
        logen_pw = settings.get("logen_pw")

        # 정식 API 통신
        logen_delivery.USE_REAL_API = True
        res_data, err = await run_in_threadpool(
            logen_delivery.create_delivery_reservation,
            sender=sender_dict,
            receiver=receiver_dict,
            package=package_dict,
            pickup_date=data.pickup_date,
            memo="",
            agent_id=logen_id,
            agent_pw=logen_pw
        )
        
        # [자동 캐치 및 업데이트 로직] 비밀번호 변경으로 인한 로그인 실패 시
        if err == "AUTH_FAILED":
            try:
                import sms_manager
                store = db.get_store(store_id)
                admin_phone = store.get("phone") if store else "010-2384-7447"
                
                # 사장님/기사님 폰으로 즉각 알림톡 쏘고 비밀번호 갱신 유도
                alimtalk_msg = f"[로젠택배 연동 오류]\n사장님, 로젠택배 로그인에 실패했습니다. (비밀번호 변경 의심)\n\n원활한 택배 자동 접수를 위해 아래 동네비서 전용 링크를 눌러 새 로젠 비밀번호를 동기화해 주세요!\n\n▶ 업데이트 링크: {request.base_url}admin/logen/settings"
                
                sms_manager.send_alimtalk(
                    to_phone=admin_phone, 
                    message=alimtalk_msg, 
                    template_id="tmp_logen_auth", 
                    variables={}
                )
            except Exception as e:
                print(f"Alimtalk Auth Error warning: {e}")
                
            raise HTTPException(status_code=401, detail="로젠택배 로그인이 만료되었거나 비밀번호가 변경되었습니다. 카카오톡으로 발송된 알림톡을 확인하여 새 비밀번호를 등록해주세요.")
        
        if err:
            raise HTTPException(status_code=500, detail=f"로젠택배 서버 접수 에러: {err}")
            
        real_tracking_code = res_data.get('waybill_number', delivery_data['tracking_code'])
        delivery_data["tracking_code"] = real_tracking_code

        # DB 저장
        if hasattr(db, 'save_store_delivery'):
             await run_in_threadpool(db.save_store_delivery, delivery_data)
        else:
             await run_in_threadpool(db.save_delivery, delivery_data)
             
        # 탄탄제작소 정산 로그 기록 추가 (세무 신고 대비)
        try:
            import settlement_engine
            await run_in_threadpool(
                settlement_engine.calculate_settlement,
                payment_amount=int(total_fee),
                order_id=real_tracking_code,
                customer_phone=data.sender_phone,
                service_type="동네비서_택배",
                persist=True
            )
        except Exception as se:
            print(f"Settlement log saving failed: {se}")
        
        print(f"✅ Real Logen API Call Success: Reserve {real_tracking_code}")
        
        # 카카오 알림톡 발송 (택배 예약)
        try:
            import sms_manager
            alimtalk_msg = f"[동네비서 택배]\n{data.sender_name}님, 예약이 접수되었습니다! (송장: {real_tracking_code})"
            sms_manager.send_alimtalk(
                to_phone=data.sender_phone, 
                message=alimtalk_msg, 
                template_id="tmp_courier", # 나중에 실제 승인된 ID로 교체 필요
                variables={"#{name}": data.sender_name, "#{track}": real_tracking_code}
            )
        except Exception as sms_err:
            print(f"⚠️ Alimtalk warning: {sms_err}")
        
        return {"success": True, "tracking_code": real_tracking_code}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Courier Reservation Failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="예약 시스템 통신 실패")

@router.get("/api/courier/today")
async def get_today_pickups(user: User = Depends(get_current_user)):
    store_id = user.store_id
    df = db.get_today_deliveries(store_id)
    if df.empty:
        return []
    # Fill NaN with None for JSON serialization
    df = df.where(pd.notnull(df), None)
    records = df.to_dict('records')
    
    import logen_crypto
    for rec in records:
        if 'fee' in rec and rec['fee']:
            margin_logic = logen_crypto.calculate_margin(int(rec['fee']))
            # HIDE the real fee from API payload entirely to prevent inspection
            rec['encrypted_fee'] = logen_crypto.encrypt_logen_fee(margin_logic['base_fee'])
            rec['fee'] = 0 # Dummy value
            
    return records

class StatusUpdateRequest(BaseModel):
    status: str

@router.post("/api/courier/{delivery_id}/status")
async def update_pickup_status(delivery_id: int, req: StatusUpdateRequest, user: User = Depends(get_current_user)):
    success = db.update_delivery_status(delivery_id, user.store_id, req.status)
    if success:
        return {"success": True, "message": f"상태가 {req.status}로 변경되었습니다."}
    raise HTTPException(status_code=400, detail="상태 업데이트 실패")

class PreRegistrationRequest(BaseModel):
    courier_company: str
    phone: str

@router.post("/api/courier/preregister")
async def preregister_courier(req: PreRegistrationRequest):
    import db_sqlite
    conn = db_sqlite.get_connection()
    c = conn.cursor()
    try:
        c.execute("CREATE TABLE IF NOT EXISTS courier_preregs (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, phone TEXT, created_at TEXT)")
        c.execute("INSERT INTO courier_preregs (company, phone, created_at) VALUES (?, ?, ?)", (req.courier_company, req.phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return {"success": True, "message": "사전 등록이 완료되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail="사전 등록 처리 중 오류 발생")
    finally:
        conn.close()
