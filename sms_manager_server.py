"""
📱 SMS 문자 발송 모듈
- Solapi API를 사용한 문자 발송
"""

import config
import requests
import time
import datetime
import uuid
import hmac
import hashlib
import db_manager as db

def _get_secret(key: str, default=""):
    return config.get_secret(key, default)


def _notify_alert(title: str, detail: str):
    webhook = _get_secret("ALERT_WEBHOOK_URL", "")
    if not webhook:
        return
    payload = {
        "text": f"[동네비서 알림] {title}\n{detail}"
    }
    try:
        requests.post(webhook, json=payload, timeout=5)
    except Exception:
        pass


def get_solapi_config():
    """Solapi 설정 가져오기"""
    try:
        return {
            'api_key': _get_secret("SOLAPI_API_KEY", ""),
            'api_secret': _get_secret("SOLAPI_API_SECRET", ""),
            'sender_phone': _get_secret("SENDER_PHONE", "")
        }
    except:
        return {
            'api_key': "",
            'api_secret': "",
            'sender_phone': ""
        }


def send_sms(to_phone, message, config=None, store_id="SYSTEM"):
    """
    SMS 문자 발송 (with DB Logging)
    """
    if config is None:
        config = get_solapi_config()
    
    api_key = config.get('api_key', '')
    api_secret = config.get('api_secret', '')
    sender_phone = config.get('sender_phone', '')
    
    # 🧪 Mock Mode (For Testing without API Keys)
    if not api_key or not api_secret:
        print(f"[Mock SMS] To: {to_phone}, Msg: {message}")
        time.sleep(0.5)
        try:
             db.log_sms(store_id, to_phone, "SMS", message, "SUCCESS", "Mock Mode")
        except: pass
        return True, "문자 발송 성공 (시뮬레이션)"
    
    if not sender_phone:
        return False, "발신번호(sender_phone) 설정이 필요합니다."
    
    if not to_phone:
        return False, "수신자 전화번호가 없습니다."
    
    try:
        # HMAC 인증 헤더 생성
        date = datetime.datetime.now().astimezone().isoformat()
        salt = str(uuid.uuid4().hex)
        data = date + salt
        signature = hmac.new(
            api_secret.encode("utf-8"), 
            data.encode("utf-8"), 
            hashlib.sha256
        ).hexdigest()
        
        header = f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}"
        
        url = "https://api.solapi.com/messages/v4/send"
        headers = {
            "Authorization": header, 
            "Content-Type": "application/json"
        }
        payload = {
            "message": {
                "to": to_phone, 
                "from": sender_phone, 
                "text": message
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            try:
                db.log_sms(store_id, to_phone, "SMS", message, "SUCCESS", "OK")
            except: pass
            return True, "문자 발송 성공!"
        else:
            try:
                db.log_sms(store_id, to_phone, "SMS", message, "FAIL", response.text)
            except: pass
            return False, f"발송 실패: {response.text}"
    
    except requests.exceptions.Timeout:
        return False, "네트워크 시간 초과. 잠시 후 다시 시도해주세요."
    # Catch-all
    except Exception as e:
        try:
            db.log_sms(store_id, to_phone, "SMS", message, "ERROR", str(e))
        except: pass
        return False, f"문자 발송 오류: {str(e)}"


def _get_cloud_sms_provider():
    try:
        return _get_secret("CLOUD_SMS_PROVIDER", "solapi").lower()
    except Exception:
        return "solapi"


def _send_custom_sms(to_phone, message):
    endpoint = _get_secret("CLOUD_SMS_ENDPOINT", "")
    api_key = _get_secret("CLOUD_SMS_API_KEY", "")
    sender = _get_secret("CLOUD_SMS_SENDER", "")
    if not endpoint or not api_key or not sender:
        return False, "클라우드 SMS 설정이 필요합니다."
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"to": to_phone, "from": sender, "text": message}
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        if response.status_code in (200, 202):
            return True, "발송 성공"
        return False, response.text
    except Exception as exc:
        return False, str(exc)


def send_cloud_sms(to_phone, message, store_id="SYSTEM"):
    provider = _get_cloud_sms_provider()
    retries = int(_get_secret("CLOUD_SMS_RETRIES", 2))
    backoff = float(_get_secret("CLOUD_SMS_BACKOFF", 0.6))
    last_err = ""

    for attempt in range(retries + 1):
        if provider == "solapi":
            ok, err = send_sms(to_phone, message, store_id=store_id)
        else:
            ok, err = _send_custom_sms(to_phone, message)

        if ok:
            if provider != "solapi":
                try:
                    db.log_sms(store_id, to_phone, "CLOUD_SMS", message, "SUCCESS", "OK")
                except Exception:
                    pass
            return True, err
        last_err = err
        if attempt < retries:
            time.sleep(backoff * (attempt + 1))

    try:
        db.log_sms(store_id, to_phone, "CLOUD_SMS", message, "FAIL", last_err)
    except Exception:
        pass
    _notify_alert("문자 발송 실패", f"store_id={store_id} to={to_phone} err={last_err}")
    return False, last_err


def _apply_message_charge(store_id, unit_cost, memo):
    balance = db.get_wallet_balance(store_id)
    if balance < unit_cost:
        return False, balance
    new_balance = balance - unit_cost
    db.update_wallet_balance(store_id, new_balance)
    try:
        db.append_wallet_log(store_id, "sms", -unit_cost, new_balance, memo)
    except Exception:
        pass
    return True, new_balance


def send_cloud_callback(store_id, to_phone, message, unit_cost=20):
    if not store_id:
        return False, "매장 정보가 없습니다."
    if not to_phone:
        return False, "수신자 전화번호가 없습니다."

    balance = db.get_wallet_balance(store_id)
    if balance < unit_cost:
        _notify_alert("잔액 부족으로 발송 실패", f"store_id={store_id} balance={balance}")
        return False, "잔액이 부족하여 발송할 수 없습니다."

    ok, err = send_cloud_sms(to_phone, message, store_id=store_id)
    if not ok:
        _notify_alert("클라우드 콜백 발송 실패", f"store_id={store_id} to={to_phone} err={err}")
        return False, f"발송 실패: {err}"

    charged, _ = _apply_message_charge(store_id, unit_cost, "cloud_callback")
    if not charged:
        _notify_alert("정산 실패", f"store_id={store_id} cost={unit_cost}")
        return False, "잔액이 부족하여 정산에 실패했습니다."
    return True, "클라우드 콜백 발송 완료"

async def send_ai_smart_callback(store_id, customer_phone, store_name=""):
    """
    AI가 작성한 동적 커스텀 메세지를 일반 SMS(LMS)로 발송합니다.
    (카카오 알림톡은 고정 구문 심사이므로 해당 로직을 일반 문자로 우회합니다.)
    """
    import ai_manager
    if not store_name:
        store_name = "동네비서"
        
    print(f"[AI 상담사 소환] {customer_phone} 님의 이력을 조회하여 메시지를 작성합니다...")
    
    # 1. AI 지연 방지를 위한 정석: "확인 중입니다" 기본 메시지 선발송
    waiting_msg = f"[{store_name}] 고객님, AI 비서가 이전 예약 내역을 확인 중입니다. 잠시만 기다려주세요!"
    send_sms(customer_phone, waiting_msg, store_id=store_id)
    
    # 2. AI 문장 생성 (2~3초 소요)
    ai_message = await ai_manager.draft_courier_greeting_message(customer_phone)
    
    # 3. AI가 작성해준 문자를 Solapi 서버에 SMS로 쏩니다.
    print(f"[AI 작성 완료] 발송 대기 중:\n{ai_message}")
    
    success, ret_msg = send_sms(customer_phone, ai_message, store_id=store_id)
    if success:
        print(f"[AI SMS 발송 성공] {customer_phone}")
    else:
        print(f"[AI SMS 발송 실패] {ret_msg}")


def process_missed_call_webhook(payload: dict):
    """
    통화 부재 웹훅 처리:
    - payload 예시: {virtual_number, caller_phone, store_id, store_name, order_link}
    """
    virtual_number = payload.get("virtual_number", "")
    caller_phone = payload.get("caller_phone", "")
    store_id = payload.get("store_id") or db.get_store_id_by_virtual_number(virtual_number)
    store_name = payload.get("store_name", "동네비서")
    order_link = payload.get("order_link", "")

    if not store_id:
        _notify_alert("웹훅 매핑 실패", f"virtual_number={virtual_number} caller={caller_phone}")
        return False, "매장 매핑 정보를 찾을 수 없습니다."
        
    store = db.get_store(store_id)
    is_courier = False
    if store:
        role = store.get("role", "")
        category = store.get("category", "")
        if role in ["logistics", "courier"] or category == "택배":
            is_courier = True

    if is_courier:
        base_url = _get_secret("APP_BASE_URL", "https://dongnebiseo.com").rstrip("/")
        order_link = f"{base_url}/delivery/request?ref={caller_phone}"
        message = (
            f"[{store_name}] 통화량 폭주로 연결이 지연되고 있습니다.\n"
            f"아래 링크에서 택배 예약을 진행해 주세요.\n"
            f"{order_link}"
        )
    else:
        message = (
            f"[{store_name}] 부재중입니다.\n"
            f"아래 링크에 주문서를 적어주세요.\n"
            f"{order_link}".strip()
        )
        
    unit_cost = int(_get_secret("cloud_message_unit_cost", 20))
    ok, err = send_cloud_callback(store_id, caller_phone, message, unit_cost=unit_cost)
    return ok, err, message


def send_alimtalk(to_phone, message, template_id=None, pf_id=None, variables=None):
    """
    알림톡 발송 (Solapi)
    - template_id, pf_id가 없으면 SMS로 폴백
    """
    config = get_solapi_config()
    api_key = config.get('api_key', '')
    api_secret = config.get('api_secret', '')
    sender_phone = config.get('sender_phone', '')

    template_id = template_id or _get_secret("SOLAPI_TEMPLATE_ID", "")
    pf_id = pf_id or _get_secret("SOLAPI_PF_ID", "")
    variables = variables or {}
    
    # 템플릿이나 카카오 채널 아이디가 누락된 경우 실제 발송 불가 안내
    if not template_id or not pf_id or template_id == 'your_template_id' or pf_id == 'KA01_0000_PF_ID':
        error_msg = "카카오 알림톡 설정 누락 (.env 파일의 SOLAPI_PF_ID, SOLAPI_TEMPLATE_ID를 실제 값으로 업데이트 해주세요)"
        print(f"[알림톡 발송 불가] To: {to_phone}, Reason: {error_msg}")
        return False, error_msg

    if not api_key or not api_secret or not sender_phone:
        return False, "SMS/알림톡 API 설정이 완료되지 않았습니다."

    # Retry Loop for Fallback
    active_pf_id = pf_id
    max_retries = 1
    current_try = 0

    while current_try <= max_retries:
        try:
            date = datetime.datetime.now().astimezone().isoformat()
            salt = str(uuid.uuid4().hex)
            data = date + salt
            signature = hmac.new(
                api_secret.encode("utf-8"),
                data.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()

            header = f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}"
            url = "https://api.solapi.com/messages/v4/send"
            headers = {
                "Authorization": header,
                "Content-Type": "application/json"
            }
            
            # Payload Construction
            current_payload = {
                "message": {
                    "to": to_phone,
                    "from": sender_phone,
                    "text": message,
                    "kakaoOptions": {
                        "pfId": active_pf_id,
                        "templateId": template_id,
                        "variables": variables
                    }
                }
            }

            response = requests.post(url, headers=headers, json=current_payload, timeout=10)
            
            if response.status_code == 200:
                # Log success channel if needed
                try:
                    # 도메인별 발송 통계 분리를 위해 template_id나 기타 변수로 식별하여 로그 저장
                    domain_tag = "ALIMTALK_" + str(template_id)
                    db.log_sms("MASTER", to_phone, domain_tag, message, "SUCCESS", "OK")
                except: pass
                return True, "알림톡 발송 성공!"
            
            # If Failed
            error_msg = response.text
            default_id = _get_secret("SOLAPI_PF_ID", "")
            
            # Check if we should fallback (Only if we used a custom ID different from default)
            if current_try == 0 and active_pf_id and active_pf_id != default_id:
                print(f"⚠️ [Kakao Fallback] Brand Channel({active_pf_id}) failed. Retrying with Platform Channel.")
                active_pf_id = default_id # Switch to Default
                current_try += 1
                continue
            
            return False, f"알림톡 발송 실패: {error_msg}"
            
        except requests.exceptions.Timeout:
            return False, "네트워크 시간 초과."
        except requests.exceptions.ConnectionError:
            return False, "네트워크 연결 오류."
        except Exception as e:
            return False, f"알림톡 발송 오류: {str(e)}"


def send_order_notification(store_phone, order_data):
    """
    주문 알림 문자 발송 (사장님에게)
    
    Args:
        store_phone: 가게 전화번호
        order_data: 주문 정보 딕셔너리
    
    Returns:
        (success: bool, message: str)
    """
    order_id = order_data.get('order_id', 'N/A')
    order_content = order_data.get('order_content', '')
    customer_phone = order_data.get('customer_phone', '')
    address = order_data.get('address', '')
    total_price = order_data.get('total_price', '')
    
    # 메시지 작성
    message = f"""[새 주문 알림]
주문번호: {order_id}
------------------
{order_content[:100]}{'...' if len(order_content) > 100 else ''}
------------------
금액: {total_price}원
연락처: {customer_phone}
주소: {address[:50]}{'...' if len(address) > 50 else ''}"""

    return send_sms(store_phone, message)


def send_order_confirmation(customer_phone, order_data):
    """
    주문 확인 문자 발송 (고객에게)
    
    Args:
        customer_phone: 고객 전화번호
        order_data: 주문 정보 딕셔너리
    
    Returns:
        (success: bool, message: str)
    """
    order_id = order_data.get('order_id', 'N/A')
    store_name = order_data.get('store_name', '')
    total_price = order_data.get('total_price', '')
    
    message = f"""[주문 접수 완료]
{store_name}
주문번호: {order_id}
결제금액: {total_price}원

맛있게 준비하겠습니다!
감사합니다 🙏"""

    return send_sms(customer_phone, message)


def send_invitation_sms(to_phone, invite_link):
    """
    가맹점 초대 문자 발송
    
    Args:
        to_phone: 수신자 전화번호
        invite_link: 초대 링크
    
    Returns:
        (success: bool, message: str)
    """
    message = f"사장님, 동네비서에 가입하세요! 링크: {invite_link}"
    return send_sms(to_phone, message)


def validate_phone_number(phone):
    """전화번호 유효성 검사"""
    if not phone:
        return False, "전화번호를 입력해주세요."
    
    # 숫자만 추출
    phone_digits = ''.join(filter(str.isdigit, phone))
    
    if len(phone_digits) < 10 or len(phone_digits) > 11:
        return False, "올바른 전화번호 형식이 아닙니다."
    
    if not phone_digits.startswith('01'):
        return False, "휴대폰 번호를 입력해주세요. (01X-XXXX-XXXX)"
    
    return True, phone_digits


def get_solapi_balance(config=None):
    """
    솔라피 계정 잔액 조회 (동기화용)
    """
    if config is None:
        config = get_solapi_config()
    
    api_key = config.get('api_key', '')
    api_secret = config.get('api_secret', '')
    
    if not api_key or not api_secret:
        return None, "API 키가 설정되지 않았습니다."
    
    try:
        # HMAC 인증 헤더 생성
        date = datetime.datetime.now().astimezone().isoformat()
        salt = str(uuid.uuid4().hex)
        data = date + salt
        signature = hmac.new(
            api_secret.encode("utf-8"), 
            data.encode("utf-8"), 
            hashlib.sha256
        ).hexdigest()
        
        header = f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}"
        
        # 잔액 조회 API 호출 (v1 cash balance)
        url = "https://api.solapi.com/cash/v1/balance"
        headers = {
            "Authorization": header, 
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            res_data = response.json()
            # balance: 잔액, point: 포인트
            return {
                'balance': res_data.get('balance', 0),
                'point': res_data.get('point', 0),
                'total': res_data.get('balance', 0) + res_data.get('point', 0)
            }, "성공"
        else:
            return None, f"조회 실패: {response.text}"
            
    except Exception as e:
        return None, f"오류: {str(e)}"

# ==========================================
# 📋 업종별 맞춤형 문자 양식 (Templates)
# ==========================================
def get_sms_templates(biz_type):
    """업종별/길이별 맞춤형 문자 양식 반환"""
    
    # 1. 단문(SMS) 템플릿 - 공통 및 업종별
    sms_templates = {
        "공통: 일반 알림": "[{store_name}] 안내 말씀 드립니다.",
        "공통: 감사 인사": "[{store_name}] 이용해 주셔서 감사합니다. 🙏",
        "택배: 접수 완료": "[로젠택배 {store_name}] 고객님의 택배가 정상 접수되었습니다.",
        "식당: 예약 확인": "[{store_name}] 예약이 정상 접수되었습니다. 곧 뵙겠습니다.",
        "판매: 입고 알림": "[{store_name}] 주문하신 상품이 입고되었습니다. 방문 부탁드립니다."
    }
    
    # 2. 장문(LMS) 템플릿 - 업종별/종류별 상세
    lms_templates = {
        "택배: 주문 안내(ARS)": "[로젠택배 {store_name}]\n안녕하세요, 고객님! 택배 보내실 물건이 있으신가요?\n\n전화 통화 없이 스마트폰 화면에서 바로 접수하고, 예상 요금 확인부터 송장 관리까지 한 번에 해결하세요!\n\n▶ 접수하기: https://dongnebiseo.com/?page=ARS\n\n언제나 빠르고 안전하게 배송하겠습니다.",
        
        "택배: 배송 지연 안내": "[로젠택배 {store_name}]\n항상 저희 지점을 이용해 주셔서 감사합니다.\n\n현재 폭설 및 물량 급증으로 인해 배송이 평소보다 1~2일 정도 지연될 예정입니다. 고객님의 소중한 물품이 안전하게 도착할 수 있도록 최선을 다하고 있으니 조금만 더 기다려 주시면 감사하겠습니다.\n\n불편을 드려 대단히 죄송합니다.",
        
        "식당: 신메뉴 출시": "[{store_name}] 특별 신메뉴 출시 안내!\n\n안녕하세요 사장님입니다. 이번 시즌을 맞아 정성껏 준비한 신메뉴가 드디어 출시되었습니다.\n\n[신메뉴 안내]\n- 메뉴명: {menu_info}\n- 특징: 산지 직송 신선한 재료 사용\n\n본 문자를 보여주시는 고객님께는 음료 1병 서비스를 드립니다. 꼭 방문해 주세요!",
        
        "판매: 시즌 할인 행사": "[{store_name}] 빅 세일(SALE) 안내\n\n단골 고객님들께만 드리는 특별 혜택!\n전 품목 최대 30% 할인 행사를 진행합니다.\n\n- 기간: 이번 주 금~일요일 (3일간)\n- 대상: 포인트 적립 회원 전체\n\n한정 수량으로 조기 품절될 수 있으니 서둘러 방문해 보세요. 감사합니다.",
        
        "농어민: 직거래 장터": "[{store_name}] 산지 직송 알림\n\n새벽에 갓 수확한 싱싱한 {item_name} 주문이 시작되었습니다!\n\n중간 유통 마진을 뺀 착한 가격으로 지금 바로 만나보세요.\n\n- 가격: {price}원 (무료배송)\n- 수량: 한정 50박스\n\n주문은 문자로 '주문'이라고 답장을 주시거나, 전화 주시면 빠르게 도와드리겠습니다."
    }
    
    return {
        "단문 (SMS)": sms_templates,
        "장문 (LMS)": lms_templates
    }


def send_smart_callback(store_id, customer_phone, store_name=""):
    """
    스마트 콜백 문자 발송 (순수 SMS 전용)
    """
    if not store_name:
         store_name = "매장"
         
    # Link Generation (Dynamic based on Config)
    base_url = _get_secret("APP_BASE_URL", "https://dongnebiseo.com")
    if base_url.endswith("/"): base_url = base_url[:-1]
    
    store = db.get_store(store_id)
    is_courier = False
    custom_msg = ""
    if store:
        role = store.get("role", "")
        category = store.get("category", "")
        if role in ["logistics", "courier"] or category == "택배":
            is_courier = True
        custom_msg = store.get("auto_reply_msg", "") or store.get("smart_callback_text", "")
            
    if custom_msg:
        msg = custom_msg.replace("{store_name}", store_name)
    elif is_courier:
        link = f"{base_url}/delivery/request?ref={customer_phone}"
        msg = f"[{store_name}] 전화 감사합니다. 바로 접수하기: {link}"
    else:
        link = f"{base_url}/?id={store_id}"
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        msg = f"[{store_name}] 전화 주셔서 감사합니다.\n기다리지 않고 아래 링크에서 바로 주문하실 수 있습니다.\n\n▶ 모바일 매장 접속:\n{link}\n\n(발송: {now_str})"
    
    # 순수 SMS(LMS) 전송
    success, ret_msg = send_sms(customer_phone, msg, store_id=store_id)
    
    if success:
        print(f"[SmartCallback] SMS Sent to {customer_phone} for {store_id}")
    else:
        print(f"[SmartCallback] SMS Failed: {ret_msg}")
        
    return success, ret_msg, msg


# ==========================================
# 🛣️ 솔라피 메시지 고속도로 (미국 서버 -> 한국)
# ==========================================
import asyncio
from typing import Dict, Any

async def send_highway_alimtalk(customer_phone: str, driver_phone: str, store_id: str = "SYSTEM", driver_name: str = ""):
    """
    솔라피 알림톡 발송 (고객에게) — 실패 시 SMS Failover
    """
    await asyncio.to_thread(_sync_send_highway, customer_phone, driver_phone, store_id, driver_name)

def _sync_send_highway(customer_phone: str, driver_phone: str, store_id: str, driver_name: str = ""):
    config_ = get_solapi_config()
    api_key = config_.get('api_key', '')
    api_secret = config_.get('api_secret', '')

    tz_kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(tz_kst)
    time_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")

    pf_id = _get_secret("SOLAPI_PF_ID", "")
    template_id = _get_secret("SOLAPI_TEMPLATE_ID", "")
    sender_number = _get_secret("SOLAPI_SENDER_NUMBER", driver_phone)
    base_url = _get_secret("APP_BASE_URL", "https://dongnebiseo.com").rstrip("/")

    reservation_no = f"DNB{int(now_kst.timestamp()) % 100000000:08d}"
    # 방문예정: 내일 오전 (실제 예약 후 조율 가능)
    import datetime as dt
    tomorrow = (now_kst + dt.timedelta(days=1)).strftime("%m/%d(%a) 오전 중")
    customer_name = f"고객{customer_phone[-4:]}"
    # 실제 기사님 성함 (DB에서 조회, 없으면 기본값)
    real_driver = driver_name.strip() if driver_name and driver_name.strip() else "담당 기사님"
    # 예약 확인 URL (고객이 클릭해서 상세 예약 가능)
    booking_url = f"{base_url}/order/{reservation_no}"

    # SMS Failover 문구 (알림톡 실패 시)
    fallback_msg = (
        f"[동네비서 택배 예약]\n"
        f"예약번호: {reservation_no}\n"
        f"방문예정: {tomorrow}\n"
        f"담당기사: {real_driver}\n"
        f"기사 연락처: {driver_phone}\n"
        f"예약 확인·변경: {booking_url}"
    )
    
    try:
        # HMAC 인증 헤더 생성 (send_alimtalk와 동일한 방식)
        date = datetime.datetime.now().astimezone().isoformat()
        salt = str(uuid.uuid4().hex)
        sig_data = date + salt
        signature = hmac.new(
            api_secret.encode("utf-8"),
            sig_data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        header = f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}"

        url = "https://api.solapi.com/messages/v4/send"
        headers = {"Authorization": header, "Content-Type": "application/json"}

        # ★ 템플릿 변수: 실제 예약 가능한 내용으로 채움
        payload = {
            "message": {
                "to": customer_phone,
                "from": sender_number,
                "text": fallback_msg,
                "kakaoOptions": {
                    "pfId": pf_id,
                    "templateId": template_id,
                    "variables": {
                        "#{고객명}": customer_name,
                        "#{예약번호}": f"{reservation_no} | {booking_url}",
                        "#{방문일자}": tomorrow,
                        "#{물품명}": "택배 (예약확인 링크에서 수정 가능)",
                        "#{기사님성함}": real_driver
                    }
                }
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)

        # 성공 시 로깅 (KST 기준)
        if response.status_code == 200:
            try:
                db.log_sms(store_id, customer_phone, "HIGHWAY_ALIMTALK", fallback_msg, "SUCCESS", f"OK (KST: {time_str})")
            except: pass
            print(f"[Message Highway] AlimTalk 성공: {customer_phone} / 예약번호: {reservation_no}")
            return
        else:
            raise Exception(f"HTTP {response.status_code}: {response.text[:100]}")

        
    except Exception as e:
        # ⚠️ 알림톡 발송 실패 -> Failover (SMS 문자) 전환
        print(f"[Message Highway] AlimTalk 실패({str(e)}). SMS(일반문자)로 Failover 발송 시도...")
        
        # 기존 send_sms 모듈을 재사용 (내부적으로 requests.post)
        ok, res_msg = send_sms(customer_phone, fallback_msg, store_id=store_id)
        
        if ok:
             print(f"[Message Highway] SMS Failover 성공: {customer_phone}")
        else:
             print(f"[Message Highway] SMS Failover 실패: {res_msg}")
             
        try:
             status = "FAILOVER_SUCCESS" if ok else "FAILOVER_FAIL"
             db.log_sms(store_id, customer_phone, "HIGHWAY_SMS", fallback_msg, status, f"Err: {str(e)[:50]}")
        except: pass

