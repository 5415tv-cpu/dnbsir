from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import db_manager as db
import sms_manager as sms
import datetime
import os
import requests

router = APIRouter(prefix="/api/comm", tags=["comm"])

import re
from pydantic import BaseModel, Field, field_validator

class CallEventRequest(BaseModel):
    customer_phone: str = Field(..., description="전화번호 (010, 지역번호, 안심번호, 대표번호 등)")
    store_id: str = Field(default="SYSTEM", max_length=50)
    call_type: str = Field(default="발신")
    auth_token: str = Field(..., min_length=10)

    @field_validator('customer_phone')
    def sanitize_phone(cls, v):
        if not v:
            return ""
        return str(v).strip()

class MessageRequest(BaseModel):
    customer_phone: str
    message: str
    store_id: Optional[str] = "SYSTEM"

@router.post("/call-event")
async def handle_call_event(payload: CallEventRequest, request: Request):
    """
    Triggered when the Android app initiates a call.
    Automatically sends a smart callback message to the customer.
    """
    import os
    APP_API_TOKEN = os.environ.get("APP_API_TOKEN", "DONGNE_BISEO_APP_SECRET_2026_!@")
    if payload.auth_token != APP_API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized app token")

    # --------------------------------------------------------
    # [방어 0] DB 진입 전 유효성 검사 (정규식 검증)
    # (모바일 010/01x, 지역번호 02~064, 안심번호 050x, 전국대표번호 15xx/16xx/18xx 등 허용)
    # --------------------------------------------------------
    phone_number = payload.customer_phone
    if not phone_number:
        return {"success": False, "message": "Ignored: Empty phone number"}

    phone_regex = re.compile(
        r'^(?:'
        r'(?:01[016789]|02|0[3-6][1-9]|050\d)-?\d{3,4}-?\d{4}'
        r'|'
        r'(?:15|16|18)\d{2}-?\d{4}'
        r')$'
    )
    if not phone_regex.match(phone_number):
        return {"success": True, "status": "ignored", "reason": "Invalid phone number format (DB insert blocked)"}

    store_name = "동네비서"
    if payload.store_id and payload.store_id != "SYSTEM":
        store = db.get_store(payload.store_id)
        if store:
            store_name = store.get("name", "동네비서")

    # 1. Send Smart Callback SMS
    ok, msg, msg_content = sms.send_smart_callback(
        store_id=payload.store_id,
        customer_phone=payload.customer_phone,
        store_name=store_name
    )

    # 2. Log to Database
    db.log_sms(
        payload.store_id or "SYSTEM",
        payload.customer_phone,
        "APP_COMM",
        payload.call_type,
        "OK" if ok else "FAIL",
        msg
    )

    # 2.5 Save to ai_call_logs for dashboard visibility
    try:
        event_type = "CALLBACK_SUCCESS" if ok else "CALLBACK_FAILED"
        db.save_ai_call_log(
            store_id=payload.store_id or "SYSTEM",
            customer_phone=payload.customer_phone,
            customer_name="이름 미상",
            intent="수신/부재중" if payload.call_type == "부재중" else "자동 콜백",
            summary=f"앱 수신 통화 이벤트 감지. 자동 콜백 결과: {msg}",
            audio_url="",
            event_type=event_type,
            event_details=msg_content
        )
    except Exception as db_err:
        print(f"Error logging call to ai_call_logs in comm: {db_err}")

    # 3. Save to call_logs for history
    try:
        from db_async import database
        query = """
        INSERT INTO call_logs (customer_phone, my_number, call_type, received_at, status)
        VALUES (:customer_phone, :my_number, :call_type, :received_at, :status)
        """
        values = {
            "customer_phone": payload.customer_phone,
            "my_number": "", 
            "call_type": payload.call_type,
            "received_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "완료"
        }
        await database.execute(query=query, values=values)
    except Exception as e:
        print(f"Error logging to call_logs: {e}")
        pass

    if not ok:
        raise HTTPException(status_code=500, detail=msg)

    return {"success": True, "message": "Call event processed and callback sent"}

@router.get("/history")
async def get_comm_history(store_id: str = "SYSTEM", limit: int = 50):
    """
    Fetches the recent communication/call history for the app.
    """
    try:
        # Fetching from call_logs for history
        from db_async import database
        query = "SELECT * FROM call_logs ORDER BY received_at DESC LIMIT :limit"
        rows = await database.fetch_all(query=query, values={"limit": limit})
        return {"success": True, "history": [dict(row) for row in rows]}
    except Exception as e:
        # Fallback to sms logs if call_logs table doesn't exist or error
        try:
            logs = db.get_sms_logs(store_id, limit)
            history = []
            if hasattr(logs, "to_dict"):
                logs = logs.to_dict(orient="records")
            for row in logs:
                history.append({
                    "customer_phone": row.get("phone", "알 수 없음"),
                    "call_type": "발신" if row.get("category") == "APP_COMM" else "수신",
                    "received_at": row.get("created_at", ""),
                    "status": row.get("status", "완료")
                })
            return {"success": True, "history": history}
        except Exception as e2:
            return {"success": False, "error": str(e), "fallback_error": str(e2)}

@router.post("/send-message")
async def send_custom_message(payload: MessageRequest):
    """
    Explicitly send an SMS from the server upon app request.
    """
    ok, msg = sms.send_sms(
        to_phone=payload.customer_phone,
        message=payload.message,
        store_id=payload.store_id
    )

    db.log_sms(
        payload.store_id or "SYSTEM",
        payload.customer_phone,
        "APP_MANUAL",
        "SMS",
        "OK" if ok else "FAIL",
        msg
    )

    if not ok:
        raise HTTPException(status_code=500, detail=msg)

    return {"success": True, "message": "Message sent"}

# 행정안전부에서 발급받은 오픈 API 승인키 (절대 외부에 노출하지 않음)
JUSO_API_KEY = os.environ.get("JUSO_API_KEY", "발급받은_행안부_API_승인키")
JUSO_API_URL = "https://business.juso.go.kr/addrlink/addrLinkApi.do"

@router.get("/search-address")
async def search_address(keyword: str):
    """
    어르신이 입력한 검색어를 받아 행안부 서버를 찌르고, 
    정제된 결과만 스마트폰으로 돌려주는 중계 함수입니다.
    """
    # 행안부 서버가 요구하는 필수 데이터 규격 세팅
    params = {
        "confmKey": JUSO_API_KEY,
        "currentPage": 1,
        "countPerPage": 10, # 어르신 화면에 맞게 최대 10개만 노출
        "keyword": keyword,
        "resultType": "json"
    }

    try:
        # 한국에 있는 서버끼리의 통신이므로 지연 시간(Latency)이 거의 없습니다.
        response = requests.get(JUSO_API_URL, params=params)
        data = response.json()
        
        # 행안부 API 에러 코드 방어
        if data["results"]["common"]["errorCode"] != "0":
            error_msg = data["results"]["common"]["errorMessage"]
            return {"status": "error", "message": f"검색 오류: {error_msg}"}

        # 스마트폰 화면에 뿌려주기 좋게 데이터 가공 (복잡한 정보 제거)
        address_list = []
        for item in data["results"]["juso"]:
            address_list.append({
                "zip_code": item["zipNo"],              # 우편번호 (5자리)
                "road_address": item["roadAddr"],       # 전체 도로명 주소
                "building_name": item["bdNm"]           # 건물명 (어르신들 식별용)
            })
            
        return {"status": "success", "data": address_list}

    except Exception as e:
        return {"status": "error", "message": "주소 검색 서버와 통신할 수 없습니다."}
