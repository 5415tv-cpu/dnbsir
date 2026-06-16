from fastapi import APIRouter, Request, Depends, HTTPException
import logging
import json
from pydantic import BaseModel

try:
    from core.security_layer import get_current_user_from_header
except ModuleNotFoundError:
    from server.core.security_layer import get_current_user_from_header

router = APIRouter(prefix="/api/relay", tags=["Android Relay Edge"])

class AndroidWebhookPayload(BaseModel):
    app_package_name: str  # ex: com.hanjin.delivery
    notification_title: str
    notification_text: str
    timestamp: str

@router.post("/webhook")
async def receive_android_relay(
    payload: AndroidWebhookPayload,
    current_user: dict = Depends(get_current_user_from_header)
):
    """
    [안드로이드 엣지 컴퓨팅 우회로]
    - 기사님 스마트폰의 Notification / Accessibility Service가 화면 텍스트나 알림을 긁어다 바로 서버로 쏩니다.
    - 보안 1단계: JWT 기반 인증 (current_user)
    - 보안 2단계: 서버 내에서 정규식 파싱 시도
    """
    user_id = current_user.get("sub", "UnknownDriver")
    logging.info(f"[AndroidRelay] Webhook received from User: {user_id}")
    
    courier = "UNKNOWN"
    tracking_no = "N/A"
    status_parsed = "RAW_EXTRACTED"
    
    # [인공지능 기반 정규식 추론 흉내 (Mock Regex Logic)]
    if "한진" in payload.notification_title or "hanjin" in payload.app_package_name.lower():
        courier = "HANJIN_RELAY"
    elif "로젠" in payload.notification_title or "logen" in payload.app_package_name.lower():
        courier = "LOGEN_RELAY"
        
    text = payload.notification_text
    
    if "배달완료" in text or "배송완료" in text:
        status_parsed = "DELIVERED"
    elif "배송 출발" in text or "지점 도착" in text:
        status_parsed = "TRANSIT"
        
    # 송장번호 추출 로직
    import re
    numbers = re.findall(r'\d{9,13}', text) # 통상적 송장 길이
    if numbers:
        tracking_no = numbers[0]

    if tracking_no == "N/A":
        logging.warning("[AndroidRelay] Could not extract tracking number cleanly from string.")
        
    # 데이터베이스 통일화를 위해 자체 DB 장부에 로깅
    try:
        import db_manager as db
        db.save_delivery({
            "store_id": user_id,
            "sender_name": f"{courier}_Scraped",
            "item_name": "Relay_Payload",
            "status": status_parsed,
            "tracking_code": tracking_no,
            "fee": 0
        })
    except Exception as e:
        logging.error(f"[AndroidRelay] DB Sync failed: {e}")

    return {
        "success": True, 
        "message": "Android relay data successfully ingested.",
        "inferred_data": {
            "courier": courier,
            "tracking_no": tracking_no,
            "status": status_parsed
        }
    }
