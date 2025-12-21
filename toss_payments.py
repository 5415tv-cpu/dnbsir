"""
💳 토스페이먼츠 빌링 API 모듈
- 빌링키 발급 (카드 등록)
- 빌링키로 자동 결제
- 결제 내역 조회
"""

import requests
import base64
import streamlit as st
from datetime import datetime, timedelta
import json

# ==========================================
# 🔑 토스페이먼츠 API 설정
# ==========================================

def get_toss_credentials():
    """토스페이먼츠 API 키 가져오기"""
    try:
        secret_key = st.secrets.get("TOSS_SECRET_KEY", "")
        client_key = st.secrets.get("TOSS_CLIENT_KEY", "")
        return secret_key, client_key
    except:
        return "", ""


def get_auth_header():
    """Basic Auth 헤더 생성"""
    secret_key, _ = get_toss_credentials()
    if not secret_key:
        return None
    
    # 시크릿 키를 Base64 인코딩
    credentials = f"{secret_key}:"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


# ==========================================
# 💳 빌링키 발급 (카드 등록)
# ==========================================

def get_billing_auth_url(customer_key: str, success_url: str, fail_url: str):
    """
    빌링키 발급용 인증 URL 생성
    - customer_key: 고객 고유 식별자 (store_id 사용)
    - success_url: 성공 시 리다이렉트 URL
    - fail_url: 실패 시 리다이렉트 URL
    """
    _, client_key = get_toss_credentials()
    
    if not client_key:
        return None, "토스페이먼츠 API 키가 설정되지 않았습니다."
    
    # 토스페이먼츠 빌링 인증 페이지 URL
    auth_url = (
        f"https://api.tosspayments.com/v1/brandpay/authorizations/card"
        f"?clientKey={client_key}"
        f"&customerKey={customer_key}"
        f"&successUrl={success_url}"
        f"&failUrl={fail_url}"
    )
    
    return auth_url, None


def issue_billing_key(auth_key: str, customer_key: str):
    """
    빌링키 발급 (인증 완료 후 호출)
    - auth_key: 카드 인증 후 받은 인증키
    - customer_key: 고객 고유 식별자
    """
    headers = get_auth_header()
    if not headers:
        return None, "API 인증 실패"
    
    headers["Content-Type"] = "application/json"
    
    url = "https://api.tosspayments.com/v1/billing/authorizations/issue"
    
    payload = {
        "authKey": auth_key,
        "customerKey": customer_key
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        
        if response.status_code == 200:
            billing_key = data.get("billingKey")
            card_info = data.get("card", {})
            return {
                "billing_key": billing_key,
                "card_company": card_info.get("issuerCode", ""),
                "card_number": card_info.get("number", ""),  # 마스킹된 번호
                "card_type": card_info.get("cardType", "")
            }, None
        else:
            error_msg = data.get("message", "빌링키 발급 실패")
            return None, error_msg
            
    except Exception as e:
        return None, f"API 호출 오류: {str(e)}"


def issue_billing_key_with_card(customer_key: str, card_number: str, 
                                  expiry_year: str, expiry_month: str,
                                  card_password: str, id_number: str):
    """
    카드 정보로 직접 빌링키 발급 (키인 결제)
    - customer_key: 고객 고유 식별자
    - card_number: 카드 번호 (16자리)
    - expiry_year: 만료 연도 (YY)
    - expiry_month: 만료 월 (MM)
    - card_password: 카드 비밀번호 앞 2자리
    - id_number: 생년월일 6자리 또는 사업자번호 10자리
    """
    headers = get_auth_header()
    if not headers:
        return None, "API 인증 실패"
    
    headers["Content-Type"] = "application/json"
    
    url = "https://api.tosspayments.com/v1/billing/authorizations/card"
    
    payload = {
        "customerKey": customer_key,
        "cardNumber": card_number.replace("-", "").replace(" ", ""),
        "cardExpirationYear": expiry_year,
        "cardExpirationMonth": expiry_month,
        "cardPassword": card_password,
        "customerIdentityNumber": id_number
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        
        if response.status_code == 200:
            billing_key = data.get("billingKey")
            card_info = data.get("card", {})
            return {
                "billing_key": billing_key,
                "card_company": card_info.get("issuerCode", ""),
                "card_number": card_info.get("number", ""),  # 마스킹된 번호
                "card_type": card_info.get("cardType", "")
            }, None
        else:
            error_msg = data.get("message", "빌링키 발급 실패")
            return None, error_msg
            
    except Exception as e:
        return None, f"API 호출 오류: {str(e)}"


# ==========================================
# 💰 빌링키로 결제 실행
# ==========================================

def execute_billing_payment(billing_key: str, customer_key: str, 
                            amount: int, order_id: str, order_name: str):
    """
    빌링키로 자동 결제 실행
    - billing_key: 발급받은 빌링키
    - customer_key: 고객 고유 식별자
    - amount: 결제 금액 (원)
    - order_id: 주문 고유 ID
    - order_name: 주문명 (예: "AI스토어 월 이용료")
    """
    headers = get_auth_header()
    if not headers:
        return None, "API 인증 실패"
    
    headers["Content-Type"] = "application/json"
    
    url = f"https://api.tosspayments.com/v1/billing/{billing_key}"
    
    payload = {
        "customerKey": customer_key,
        "amount": amount,
        "orderId": order_id,
        "orderName": order_name
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        
        if response.status_code == 200:
            return {
                "payment_key": data.get("paymentKey"),
                "order_id": data.get("orderId"),
                "amount": data.get("totalAmount"),
                "status": data.get("status"),
                "approved_at": data.get("approvedAt"),
                "card_number": data.get("card", {}).get("number", "")
            }, None
        else:
            error_msg = data.get("message", "결제 실패")
            error_code = data.get("code", "")
            return None, f"{error_code}: {error_msg}"
            
    except Exception as e:
        return None, f"API 호출 오류: {str(e)}"


# ==========================================
# 📋 결제 내역 조회
# ==========================================

def get_payment_history(payment_key: str):
    """결제 상세 내역 조회"""
    headers = get_auth_header()
    if not headers:
        return None, "API 인증 실패"
    
    url = f"https://api.tosspayments.com/v1/payments/{payment_key}"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        if response.status_code == 200:
            return data, None
        else:
            return None, data.get("message", "조회 실패")
            
    except Exception as e:
        return None, f"API 호출 오류: {str(e)}"


# ==========================================
# 🔧 유틸리티 함수
# ==========================================

def generate_order_id(store_id: str):
    """주문 ID 생성"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"BILL_{store_id}_{timestamp}"


def calculate_next_payment_date(days: int = 30):
    """다음 결제일 계산"""
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def calculate_expiry_date(days: int = 30):
    """만료일 계산"""
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def is_payment_due(next_payment_date: str):
    """결제일이 되었는지 확인"""
    try:
        due_date = datetime.strptime(next_payment_date, "%Y-%m-%d")
        return datetime.now().date() >= due_date.date()
    except:
        return False


def is_expired(expiry_date: str):
    """만료되었는지 확인"""
    try:
        exp_date = datetime.strptime(expiry_date, "%Y-%m-%d")
        return datetime.now().date() > exp_date.date()
    except:
        return False


# ==========================================
# 💵 무통장 입금 정보
# ==========================================

BANK_ACCOUNT_INFO = {
    "bank_name": "신한은행",
    "account_number": "110-123-456789",
    "account_holder": "동네비서",
    "monthly_fee": 50000,  # 월 이용료 (원)
    "note": "입금 시 가게명을 입금자명에 기재해주세요."
}


def get_bank_transfer_info():
    """무통장 입금 정보 반환"""
    return BANK_ACCOUNT_INFO

