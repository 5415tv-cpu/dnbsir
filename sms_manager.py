"""
📱 SMS 문자 발송 모듈
- Solapi API를 사용한 문자 발송
"""

import streamlit as st
import requests
import datetime
import hmac
import hashlib
import uuid


# ==========================================
# 🔑 Solapi API 설정
# ==========================================
def get_solapi_config():
    """Solapi 설정 가져오기"""
    try:
        return {
            'api_key': st.secrets.get("SOLAPI_API_KEY", ""),
            'api_secret': st.secrets.get("SOLAPI_API_SECRET", ""),
            'sender_phone': st.secrets.get("SENDER_PHONE", "")
        }
    except:
        return {
            'api_key': "",
            'api_secret': "",
            'sender_phone': ""
        }


def send_sms(to_phone, message, config=None):
    """
    SMS 문자 발송
    
    Args:
        to_phone: 수신자 전화번호
        message: 메시지 내용
        config: Solapi 설정 (없으면 secrets에서 가져옴)
    
    Returns:
        (success: bool, message: str)
    """
    if config is None:
        config = get_solapi_config()
    
    api_key = config.get('api_key', '')
    api_secret = config.get('api_secret', '')
    sender_phone = config.get('sender_phone', '')
    
    if not api_key or not api_secret or not sender_phone:
        return False, "SMS API 설정이 완료되지 않았습니다."
    
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
            return True, "문자 발송 성공!"
        else:
            return False, f"발송 실패: {response.text}"
    
    except requests.exceptions.Timeout:
        return False, "네트워크 시간 초과. 잠시 후 다시 시도해주세요."
    except requests.exceptions.ConnectionError:
        return False, "네트워크 연결 오류. 인터넷 연결을 확인해주세요."
    except Exception as e:
        return False, f"문자 발송 오류: {str(e)}"


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

