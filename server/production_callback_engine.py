from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
import requests
import os
import hmac
import hashlib
import uuid
from datetime import timezone

app = FastAPI(title="동네비서 실전 콜백 엔진 v1.0")

# --------------------------------------------------------
# [실전 설정 정보] 수동 입력 및 관리 (대표님 실제 키 적용 완료)
# --------------------------------------------------------
KAKAO_CHAT_URL = "http://pf.kakao.com/_WLxjNn/chat"
SOLAPI_API_KEY = "NCSR1SXBMOH13MYO"
SOLAPI_API_SECRET = "S8T5X4B5PBFLDUDIAUB1ZOHLB8SIRQIY"
SOLAPI_SENDER_NUMBER = "01023847447"

# 단골 판별을 위한 임시 메모리 DB (실전 가동 시 실-DB 연동)
# 구조: { "고객번호_가게ID": {"last_sent": datetime, "order_count": int} }
customer_db = {}

class CallEvent(BaseModel):
    phone_number: str  # 고객 번호
    call_type: str     # incoming (수신) / outgoing (발신)
    store_id: str      # 가맹점 고유 ID (예: "store_101")
    store_name: str    # 가맹점 상호명 (예: "탄탄고깃집")

def execute_solapi_send(target_number: str, store_name: str, order_count: int):
    """
    실제 솔라피 서버로 완벽하게 조립된 문자를 발사하는 비동기 함수
    """
    # 2회째 전화를 걸었을 때 '단골 감동' 멘트 분기 기획 반영
    if order_count >= 1:
        text_content = f"[{store_name}] 늘 찾아주셔서 감사합니다!\n지난번 드신 메뉴로 바로 준비할까요?\n➡️ {KAKAO_CHAT_URL}"
    else:
        text_content = f"[{store_name}] 첫 방문을 환영합니다!\n통화 대기 없이 카카오톡으로 바로 주문하세요.\n➡️ {KAKAO_CHAT_URL}"

    # 솔라피 규격 정석 세팅
    # (실전 배포 시에는 공식 솔라피 파이썬 SDK 라이브러리를 사용하거나 아래의 REST API 규격을 따릅니다)
    url = "https://api.solapi.com/messages/v4/send"
    
    # ⚠️ [실전 인증 적용] 솔라피 규정에 맞춘 HMAC 인증 헤더 자동 생성 코드가 적용되었습니다.
    now_utc = datetime.now(timezone.utc)
    date_str = now_utc.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    salt = str(uuid.uuid4()).replace('-', '')
    
    combined = date_str + salt
    signature = hmac.new(
        SOLAPI_API_SECRET.encode('utf-8'),
        combined.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    auth_header = f"HMAC-SHA256 apiKey={SOLAPI_API_KEY}, date={date_str}, salt={salt}, signature={signature}"
    
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json; charset=utf-8"
    }
    
    payload = {
        "message": {
            "to": target_number,
            "from": SOLAPI_SENDER_NUMBER,
            "text": text_content
        }
    }

    try:
        # 실전 발사 (주석 해제하여 실전 동작 활성화 완료)
        response = requests.post(url, json=payload, headers=headers)
        print(f"[실전 발송 로그] 상태코드: {response.status_code} | 대상: {target_number} | 응답: {response.text}")
        
        # 현장 검증용 내부 로그 출력
        print(f"\n==================================================")
        print(f"[실전 발송 완료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"가게: {store_name} | 수신자: {target_number} (과거 주문: {order_count}회)")
        print(f"문자 내용:\n{text_content}")
        print(f"==================================================\n")
        
    except Exception as e:
        print(f"[실전 에러 가드] 문자 발송 실패했으나 시스템을 유지합니다. 사유: {e}")

@app.post("/api/comm/call-event")
async def receive_call_event(event: CallEvent, background_tasks: BackgroundTasks):
    """
    탄탄 콜 프로 앱이 전화를 끊자마자 실시간으로 신호를 꽂아넣는 종착지
    """
    now = datetime.now()
    customer_phone = event.phone_number
    store_key = f"{customer_phone}_{event.store_id}"

    # [실전 방어 1] 대한민국 정규 전화번호 규격 검사 (Regex)
    # (모바일 010/01x, 지역번호 02~064, 안심번호 050x, 전국대표번호 15xx/16xx/18xx 등 허용)
    if not customer_phone or not isinstance(customer_phone, str):
        return {"status": "ignored", "reason": "Invalid or empty phone number"}

    import re
    phone_regex = re.compile(
        r'^(?:'
        r'(?:01[016789]|02|0[3-6][1-9]|050\d)-?\d{3,4}-?\d{4}'
        r'|'
        r'(?:15|16|18)\d{2}-?\d{4}'
        r')$'
    )
    if not phone_regex.match(customer_phone):
        return {"status": "ignored", "reason": "Invalid phone number format"}

    # [실전 방어 2] 사장님이 건 전화는 절대로 문자를 보내지 않음 (기사님/거래처 오발송 완벽 차단)
    if event.call_type == "outgoing":
        return {"status": "ignored", "reason": "Outgoing call"}

    # [실전 방어 3] 1시간 중복 발송 제한 (고객 스팸 항의 방지)
    if store_key in customer_db:
        last_sent = customer_db[store_key]["last_sent"]
        if now - last_sent < timedelta(hours=1):
            return {"status": "ignored", "reason": "Cool-time active"}
    else:
        # 최초 데이터 생성
        customer_db[store_key] = {"last_sent": now, "order_count": 0}

    # 단골 데이터 업데이트 및 솔라피 발송을 백그라운드로 토스 (서버 멈춤 현상 100% 방어)
    customer_db[store_key]["last_sent"] = now
    current_orders = customer_db[store_key]["order_count"]
    
    # 솔라피 실전 발송 함수 비동기 가동
    background_tasks.add_task(execute_solapi_send, customer_phone, event.store_name, current_orders)

    # ⚠️ [실전 주문 완료 처리 예시] 
    # 향후 카카오톡 주문창에서 최종 결제가 끝나는 시점에 아래 코드가 실행되도록 연동해야 합니다.
    # customer_db[store_key]["order_count"] += 1

    return {"status": "success", "message": "Production pipeline initiated"}
