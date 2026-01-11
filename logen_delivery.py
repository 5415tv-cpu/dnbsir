"""
🚚 로젠택배 연동 모듈
- 택배 예약 및 요금 계산
- 대량 접수 처리
- API 연동 준비 (사업자 계약 후 실제 API 연결 가능)

Note: 현재는 시뮬레이션 모드로 작동하며, 
      실제 로젠택배 API 계약 후 연동 가능하도록 구조화됨
"""

import streamlit as st
from datetime import datetime, timedelta
import json
import requests
from typing import Optional, Dict, List, Tuple

# ==========================================
# 📦 로젠택배 설정
# ==========================================

# 로젠택배 웹사이트 URL
LOGEN_WEB_URL = "https://www.ilogen.com"
LOGEN_PERSONAL_URL = "https://www.ilogen.com/m/personal/tkPersonalWaybillSave.dev"
LOGEN_BULK_URL = "https://www.ilogen.com/m/personal/tkPersonalWaybillList.dev"

# API 모드 (🚨 중요: 로젠택배 API 키를 받으시면 True로 변경하세요)
USE_REAL_API = False

# API 설정 (사업자 계약 후 secrets.toml 또는 관리자 페이지에서 설정 가능하도록 구조화)
LOGEN_API_BASE_URL = "https://api.ilogen.com"  # 로젠택배 실제 API 엔드포인트
LOGEN_API_KEY = st.secrets.get("LOGEN_API_KEY", "") # API KEY
LOGEN_USER_ID = st.secrets.get("LOGEN_USER_ID", "") # 본사 아이디


# ==========================================
# 💰 택배 요금표 (2024년 기준 / 시뮬레이션용)
# ==========================================

# 무게별 기본 요금 (일반택배)
WEIGHT_RATES = {
    '2kg': 3500,
    '5kg': 4000,
    '10kg': 5000,
    '20kg': 6000,
    '30kg': 8000,
}

# 크기별 추가 요금
SIZE_SURCHARGE = {
    '소형': 0,      # 60cm 이하
    '중형': 500,    # 80cm 이하
    '대형': 1500,   # 120cm 이하
    '특대형': 3000, # 120cm 초과
}

# 지역별 추가 요금 (도서/산간 지역)
REMOTE_AREA_SURCHARGE = {
    '일반': 0,
    '도서': 3000,
    '산간': 2000,
}

# 부가 서비스 요금
ADDITIONAL_SERVICES = {
    '착불': 0,
    '선불': 0,
    '신선식품': 2000,
    '파손주의': 500,
    '귀중품': 1000,
}


def get_logen_credentials() -> Tuple[str, str]:
    """로젠택배 API 인증 정보 가져오기"""
    try:
        api_key = st.secrets.get("LOGEN_API_KEY", "")
        api_secret = st.secrets.get("LOGEN_API_SECRET", "")
        return api_key, api_secret
    except Exception:
        return "", ""


# ==========================================
# 💵 요금 계산 함수
# ==========================================

def calculate_delivery_fee(
    weight_kg: float,
    size_category: str = '소형',
    is_remote: str = '일반',
    additional_services: List[str] = None,
    is_prepaid: bool = True
) -> Dict:
    """
    택배 예상 요금 계산
    
    Args:
        weight_kg: 무게 (kg)
        size_category: 크기 ('소형', '중형', '대형', '특대형')
        is_remote: 지역 ('일반', '도서', '산간')
        additional_services: 부가 서비스 리스트
        is_prepaid: 선불 여부
    
    Returns:
        요금 정보 딕셔너리
    """
    if additional_services is None:
        additional_services = []
    
    # 무게별 기본 요금 결정
    if weight_kg <= 2:
        base_fee = WEIGHT_RATES['2kg']
        weight_category = '2kg 이하'
    elif weight_kg <= 5:
        base_fee = WEIGHT_RATES['5kg']
        weight_category = '5kg 이하'
    elif weight_kg <= 10:
        base_fee = WEIGHT_RATES['10kg']
        weight_category = '10kg 이하'
    elif weight_kg <= 20:
        base_fee = WEIGHT_RATES['20kg']
        weight_category = '20kg 이하'
    else:
        base_fee = WEIGHT_RATES['30kg']
        weight_category = '30kg 이하'
    
    # 크기 추가 요금
    size_fee = SIZE_SURCHARGE.get(size_category, 0)
    
    # 지역 추가 요금
    remote_fee = REMOTE_AREA_SURCHARGE.get(is_remote, 0)
    
    # 부가 서비스 요금
    service_fee = sum(ADDITIONAL_SERVICES.get(s, 0) for s in additional_services)
    
    # 총 요금
    total_fee = base_fee + size_fee + remote_fee + service_fee
    
    return {
        'base_fee': base_fee,
        'weight_category': weight_category,
        'size_fee': size_fee,
        'size_category': size_category,
        'remote_fee': remote_fee,
        'remote_category': is_remote,
        'service_fee': service_fee,
        'additional_services': additional_services,
        'total_fee': total_fee,
        'is_prepaid': is_prepaid,
        'payment_type': '선불' if is_prepaid else '착불'
    }


def estimate_delivery_date(pickup_date: datetime = None) -> Dict:
    """
    예상 배송일 계산
    
    Args:
        pickup_date: 수거 날짜 (None이면 오늘)
    
    Returns:
        배송 예상 정보
    """
    if pickup_date is None:
        pickup_date = datetime.now()
    
    # 일반 배송: 1-2일
    min_days = 1
    max_days = 2
    
    # 주말 고려
    current_day = pickup_date.weekday()
    if current_day >= 4:  # 금, 토, 일
        max_days += 1
    
    min_delivery = pickup_date + timedelta(days=min_days)
    max_delivery = pickup_date + timedelta(days=max_days)
    
    return {
        'pickup_date': pickup_date.strftime("%Y-%m-%d"),
        'min_delivery_date': min_delivery.strftime("%Y-%m-%d"),
        'max_delivery_date': max_delivery.strftime("%Y-%m-%d"),
        'estimated_text': f"{min_delivery.strftime('%m/%d')} ~ {max_delivery.strftime('%m/%d')} 도착 예정"
    }


# ==========================================
# 📋 예약 번호 생성
# ==========================================

def generate_reservation_number(prefix: str = "LG") -> str:
    """
    택배 예약 번호 생성
    
    Args:
        prefix: 접두사 (기본: LG)
    
    Returns:
        예약 번호 (예: LG20241221143052001)
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    sequence = now.microsecond % 1000
    return f"{prefix}{timestamp}{sequence:03d}"


# ==========================================
# 🚚 택배 예약 API (시뮬레이션 / 실제 API 준비)
# ==========================================

def create_delivery_reservation(
    sender: Dict,
    receiver: Dict,
    package: Dict,
    pickup_date: str = None,
    memo: str = ""
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    택배 예약 생성
    
    Args:
        sender: 보내는 사람 정보 {'name', 'phone', 'address', 'detail_address'}
        receiver: 받는 사람 정보 {'name', 'phone', 'address', 'detail_address'}
        package: 화물 정보 {'type', 'weight', 'size', 'contents'}
        pickup_date: 수거 희망일
        memo: 메모
    
    Returns:
        (예약 결과, 에러 메시지)
    """
    
    if USE_REAL_API:
        # 실제 API 호출 (사업자 계약 후 구현)
        return _call_logen_api(sender, receiver, package, pickup_date, memo)
    else:
        # 시뮬레이션 모드
        return _simulate_reservation(sender, receiver, package, pickup_date, memo)


def _simulate_reservation(
    sender: Dict,
    receiver: Dict,
    package: Dict,
    pickup_date: str,
    memo: str
) -> Tuple[Optional[Dict], Optional[str]]:
    """시뮬레이션 예약 처리"""
    
    # 입력 검증
    if not sender.get('name') or not sender.get('phone') or not sender.get('address'):
        return None, "보내는 분 정보를 모두 입력해주세요."
    
    if not receiver.get('name') or not receiver.get('phone') or not receiver.get('address'):
        return None, "받는 분 정보를 모두 입력해주세요."
    
    # 예약 번호 생성
    reservation_number = generate_reservation_number()
    
    # 요금 계산
    weight = float(package.get('weight', 2))
    size = package.get('size', '소형')
    fee_info = calculate_delivery_fee(weight, size)
    
    # 배송 예상일 계산
    if pickup_date:
        pickup_dt = datetime.strptime(pickup_date, "%Y-%m-%d")
    else:
        pickup_dt = datetime.now()
    delivery_info = estimate_delivery_date(pickup_dt)
    
    # 예약 결과 생성
    result = {
        'success': True,
        'reservation_number': reservation_number,
        'waybill_number': None,  # 운송장 번호 (수거 후 발급)
        'status': '접수완료',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'sender': sender,
        'receiver': receiver,
        'package': package,
        'pickup_date': pickup_date or datetime.now().strftime("%Y-%m-%d"),
        'memo': memo,
        'fee': fee_info,
        'delivery_estimate': delivery_info,
        'logen_web_url': f"{LOGEN_PERSONAL_URL}?ref={reservation_number}",
        'message': f"예약이 완료되었습니다. 예약번호: {reservation_number}"
    }
    
    return result, None


def _call_logen_api(
    sender: Dict,
    receiver: Dict,
    package: Dict,
    pickup_date: str,
    memo: str
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    로젠택배 본사 서버로 실제 데이터를 전송하는 핵심 함수
    (API 문서를 받으시는 대로 아래 페이로드 규격을 맞추면 즉시 작동합니다)
    """
    if not LOGEN_API_KEY:
        return None, "로젠택배 API 키가 설정되지 않았습니다."

    try:
        # 📦 로젠택배 본사 전송용 데이터 규격 (표준형 예시)
        payload = {
            "api_key": LOGEN_API_KEY,
            "user_id": LOGEN_USER_ID,
            "order_type": "PREPAID", # 선불/착불 등
            "sender": {
                "name": sender.get('name'),
                "tel": sender.get('phone'),
                "addr": f"{sender.get('address')} {sender.get('detail_address', '')}"
            },
            "receiver": {
                "name": receiver.get('name'),
                "tel": receiver.get('phone'),
                "addr": f"{receiver.get('address')} {receiver.get('detail_address', '')}"
            },
            "item": {
                "name": package.get('contents', '잡화'),
                "weight": package.get('weight', 2),
                "size": package.get('size', '소형'),
                "price": package.get('price', 0)
            },
            "pickup_date": pickup_date,
            "memo": memo
        }
        
        # 🚀 실제 로젠 본사 서버로 전송 (문서 수령 후 아래 주석 해제)
        # response = requests.post(f"{LOGEN_API_BASE_URL}/api/v1/save_order", json=payload, timeout=10)
        # if response.status_code == 200: return response.json(), None
        
        # 지금은 전송 구조 대기 모드 (로그 출력)
        print(f"DEBUG: 로젠택배 본사 서버 전송 준비 완료 - {payload['sender']['name']} -> {payload['receiver']['name']}")
        return {"success": True, "waybill_number": "PENDING_API", "message": "로젠 본사 전송 규격 생성 완료"}, None
            
    except Exception as e:
        return None, f"로젠 본사 서버 통신 에러: {str(e)}"


# ==========================================
# 📊 대량 접수 처리
# ==========================================

def process_bulk_reservations(
    reservations: List[Dict],
    on_progress: callable = None
) -> Dict:
    """
    대량 택배 예약 처리
    
    Args:
        reservations: 예약 정보 리스트
        on_progress: 진행 상황 콜백 함수 (current, total)
    
    Returns:
        처리 결과 {'success_count', 'fail_count', 'results', 'total_fee'}
    """
    results = []
    success_count = 0
    fail_count = 0
    total_fee = 0
    
    for idx, reservation in enumerate(reservations):
        try:
            # 데이터 추출
            sender = {
                'name': reservation.get('sender_name', ''),
                'phone': reservation.get('sender_phone', ''),
                'address': reservation.get('sender_address', ''),
                'detail_address': reservation.get('sender_detail', '')
            }
            
            receiver = {
                'name': reservation.get('receiver_name', ''),
                'phone': reservation.get('receiver_phone', ''),
                'address': reservation.get('receiver_address', ''),
                'detail_address': reservation.get('receiver_detail', '')
            }
            
            package = {
                'type': reservation.get('package_type', '박스'),
                'weight': float(reservation.get('weight', 2)),
                'size': reservation.get('size', '소형'),
                'contents': reservation.get('contents', '')
            }
            
            # 예약 생성
            result, error = create_delivery_reservation(
                sender=sender,
                receiver=receiver,
                package=package,
                pickup_date=reservation.get('pickup_date'),
                memo=reservation.get('memo', '')
            )
            
            if error:
                results.append({
                    'index': idx + 1,
                    'success': False,
                    'error': error,
                    'sender_name': sender['name'],
                    'receiver_name': receiver['name']
                })
                fail_count += 1
            else:
                results.append({
                    'index': idx + 1,
                    'success': True,
                    'reservation_number': result['reservation_number'],
                    'fee': result['fee']['total_fee'],
                    'sender_name': sender['name'],
                    'receiver_name': receiver['name']
                })
                success_count += 1
                total_fee += result['fee']['total_fee']
            
            # 진행 상황 콜백
            if on_progress:
                on_progress(idx + 1, len(reservations))
                
        except Exception as e:
            results.append({
                'index': idx + 1,
                'success': False,
                'error': str(e),
                'sender_name': reservation.get('sender_name', ''),
                'receiver_name': reservation.get('receiver_name', '')
            })
            fail_count += 1
    
    return {
        'success_count': success_count,
        'fail_count': fail_count,
        'total_count': len(reservations),
        'total_fee': total_fee,
        'results': results
    }


# ==========================================
# 🔍 배송 조회 (운송장 번호로)
# ==========================================

def track_delivery(waybill_number: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    배송 조회
    
    Args:
        waybill_number: 운송장 번호
    
    Returns:
        (조회 결과, 에러 메시지)
    """
    if not waybill_number:
        return None, "운송장 번호를 입력해주세요."
    
    if USE_REAL_API:
        # 실제 API 호출
        api_key, _ = get_logen_credentials()
        if not api_key:
            return None, "API 인증 정보가 없습니다."
        
        try:
            response = requests.get(
                f"{LOGEN_API_BASE_URL}/v1/tracking/{waybill_number}",
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=10
            )
            if response.status_code == 200:
                return response.json(), None
            else:
                return None, f"조회 실패: {response.status_code}"
        except Exception as e:
            return None, f"조회 오류: {str(e)}"
    else:
        # 시뮬레이션 - 로젠택배 웹사이트로 리다이렉트 URL 제공
        return {
            'waybill_number': waybill_number,
            'tracking_url': f"https://www.ilogen.com/web/personal/trace/{waybill_number}",
            'message': "로젠택배 웹사이트에서 조회하세요."
        }, None


# ==========================================
# 📋 요금표 조회 UI용
# ==========================================

def get_fee_table_html() -> str:
    """요금표 HTML 생성"""
    return """
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 15px; margin: 1rem 0;">
        <h4 style="margin: 0 0 1rem 0; color: #333;">📦 로젠택배 요금표 (2024년 기준)</h4>
        
        <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden;">
            <thead>
                <tr style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white;">
                    <th style="padding: 12px; text-align: left;">무게</th>
                    <th style="padding: 12px; text-align: right;">기본 요금</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 10px;">2kg 이하</td>
                    <td style="padding: 10px; text-align: right; font-weight: bold;">3,500원</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee; background: #f8f9fa;">
                    <td style="padding: 10px;">5kg 이하</td>
                    <td style="padding: 10px; text-align: right; font-weight: bold;">4,000원</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 10px;">10kg 이하</td>
                    <td style="padding: 10px; text-align: right; font-weight: bold;">5,000원</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee; background: #f8f9fa;">
                    <td style="padding: 10px;">20kg 이하</td>
                    <td style="padding: 10px; text-align: right; font-weight: bold;">6,000원</td>
                </tr>
                <tr>
                    <td style="padding: 10px;">30kg 이하</td>
                    <td style="padding: 10px; text-align: right; font-weight: bold;">8,000원</td>
                </tr>
            </tbody>
        </table>
        
        <div style="margin-top: 1rem; font-size: 0.85rem; color: #666;">
            <p style="margin: 0.3rem 0;">• 크기 추가: 중형 +500원, 대형 +1,500원, 특대형 +3,000원</p>
            <p style="margin: 0.3rem 0;">• 도서지역 +3,000원, 산간지역 +2,000원</p>
            <p style="margin: 0.3rem 0;">• 실제 요금은 로젠택배 고객센터(1588-9988)에서 확인하세요.</p>
        </div>
    </div>
    """


def get_weight_options() -> List[str]:
    """무게 옵션 리스트"""
    return ["2kg 이하", "5kg 이하", "10kg 이하", "20kg 이하", "30kg 이하"]


def get_size_options() -> List[str]:
    """크기 옵션 리스트"""
    return ["소형 (60cm 이하)", "중형 (80cm 이하)", "대형 (120cm 이하)", "특대형 (120cm 초과)"]


def parse_weight(weight_str: str) -> float:
    """무게 문자열을 숫자로 변환"""
    weight_map = {
        "2kg 이하": 2,
        "5kg 이하": 5,
        "10kg 이하": 10,
        "20kg 이하": 20,
        "30kg 이하": 30
    }
    return weight_map.get(weight_str, 2)


def parse_size(size_str: str) -> str:
    """크기 문자열을 카테고리로 변환"""
    if "소형" in size_str:
        return "소형"
    elif "중형" in size_str:
        return "중형"
    elif "대형" in size_str:
        return "대형"
    elif "특대형" in size_str:
        return "특대형"
    return "소형"

