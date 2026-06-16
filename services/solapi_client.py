import os
import uuid
import hmac
import hashlib
import httpx
from datetime import datetime
from dotenv import load_dotenv
from logger import logger

load_dotenv()

# 솔라피 API 설정 (반드시 .env 파일에 보관하여 격리 통제)
SOLAPI_API_KEY = os.getenv("SOLAPI_API_KEY")
SOLAPI_API_SECRET = os.getenv("SOLAPI_API_SECRET")
# Fall back to SENDER_PHONE if SOLAPI_SENDER_NUMBER is not set in env
SOLAPI_SENDER_NUMBER = os.getenv("SOLAPI_SENDER_NUMBER") or os.getenv("SENDER_PHONE")

def _generate_solapi_signature() -> str:
    """솔라피 공식 문서 기준 HMAC-SHA256 서명 생성 로직"""
    date = datetime.utcnow().isoformat() + "Z"
    salt = uuid.uuid4().hex
    
    message = date + salt
    signature = hmac.new(
        SOLAPI_API_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"HMAC-SHA256 apiKey={SOLAPI_API_KEY}, date={date}, salt={salt}, signature={signature}"

async def send_sms_async(to_number: str, text: str) -> bool:
    """동네비서 이벤트 루프를 막지 않는 비동기 문자 발송 모듈"""
    # Local debugging / mock fallback if credentials are not fully configured
    is_test_phone = to_number.startswith("0109999") or to_number.startswith("0100000") or to_number == "test"
    is_mock = not SOLAPI_API_KEY or not SOLAPI_API_SECRET or is_test_phone
    
    if is_mock:
        logger.info(f"[MOCK SMS] To: {to_number}, Text: {text}")
        return True

    url = "https://api.solapi.com/messages/v4/send"
    headers = {
        "Authorization": _generate_solapi_signature(),
        "Content-Type": "application/json"
    }
    payload = {
        "message": {
            "to": to_number,
            "from": SOLAPI_SENDER_NUMBER,
            "text": text
        }
    }
    
    # 5초 이상 응답이 없으면 즉시 타임아웃 처리하여 시스템 다운 방지
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status() # 200번대 응답이 아니면 예외 발생
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Solapi 문자 발송 실패 | To: {to_number} | 응답: {e.response.text}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Solapi 네트워크 통신 에러 | To: {to_number} | 에러: {str(e)}")
            return False
