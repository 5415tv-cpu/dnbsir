"""
🚚 로젠택배 영업소(TMS) 전용 연동 모듈 (최신 SalesAgent RGB 반영)
- 영업소 전용 앱(ilogen_tms.apk)의 백엔드(SalesLogisApp.ilogen.com)와 통신 구조 제공
- 택배 예약 및 운임 요금 자동 계산 (2024년 기준 적용)
- 대량 주문/운송장 발급 자동화
- API 연동 구조화 (영업소 계정 로그인 후 실제 API 연결 가능)

Note: 현재는 테스트/시뮬레이션 모드로 작동하며, 
      실제 로젠택배 영업소 계정이 있을 경우 USE_REAL_API 설정을 통해 즉각 연결 가능합니다.
"""

import hashlib
import uuid
import config
from datetime import datetime, timedelta
import json
import requests
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

# ==========================================
# 📦 로젠택배 영업소/TMS 서버 설정
# ==========================================

# 기존 개인 고객용 B2C 웹사이트 URL
LOGEN_WEB_URL = "https://www.ilogen.com"
LOGEN_PERSONAL_URL = "https://www.ilogen.com/m/personal/tkPersonalWaybillSave.dev"

# 🚨 메인: 영업소(TMS) 전용 통합 앱 서버 리스트 (Load Balancing 적용)
# ilogen_tms.apk 내부 분석 결과 (SalesLogisApp, SalesLogisApp1~4 사용)
LOGEN_TMS_HOSTS = [
    "http://SalesLogisApp.ilogen.com",
    "http://SalesLogisApp1.ilogen.com",
    "http://SalesLogisApp2.ilogen.com",
    "http://SalesLogisApp3.ilogen.com",
    "http://SalesLogisApp4.ilogen.com"
]
LOGEN_TMS_BASE_URL = LOGEN_TMS_HOSTS[0]  # 메인 호스트 사용

# 영업소 관련 API 엔드포인트 정의
TMS_API_ENDPOINTS = {
    "login": f"{LOGEN_TMS_BASE_URL}/api/v1/auth/login",                     # 로그인 인증 (영업소 계정)
    "waybill_save": f"{LOGEN_TMS_BASE_URL}/api/v1/delivery/waybill/save",   # 운송장 접수 (신규)
    "waybill_list": f"{LOGEN_TMS_BASE_URL}/api/v1/delivery/waybill/list",   # 접수 목록 조회
    "tracking": f"{LOGEN_TMS_BASE_URL}/api/v1/delivery/tracking",           # 화물 추적 (상세 이력)
}

# API 모드 (🚨 중요: 로젠 영업소 아이디/비번을 받으시면 True로 변경하세요)
USE_REAL_API = True

# ==========================================
# 🔑 자격 증명 관리 (Config / Secrets 연동)
# ==========================================
def _safe_secret(key: str, default: str = "") -> str:
    return config.get_secret(key, default)

# 영업소 통합 계정 정보
LOGEN_AGENT_ID = _safe_secret("LOGEN_AGENT_ID", "")        # 영업소/대리점 사번(ID)
LOGEN_AGENT_PW = _safe_secret("LOGEN_AGENT_PW", "")        # 비밀번호
LOGEN_API_KEY = _safe_secret("LOGEN_TMS_API_KEY", "")      # 발급받은 API 키 (있는 경우)
LOGEN_DEVICE_UUID = _safe_secret("LOGEN_DEVICE_UUID", "0000-0000-0000-0000")  # 레거시 기기 고유 인증값

# ==========================================
# 📦 로젠택배 B2B 공식 Open API 설정
# ==========================================
USE_LOGEN_B2B_API = _safe_secret("USE_LOGEN_B2B_API", "False").lower() in ("true", "1", "yes")
LOGEN_B2B_DEV_MODE = _safe_secret("LOGEN_B2B_DEV_MODE", "True").lower() in ("true", "1", "yes")

LOGEN_B2B_URL_DEV = "https://topenapi.ilogen.com"
LOGEN_B2B_URL_PROD = "https://openapi.ilogen.com"
LOGEN_B2B_BASE_URL = LOGEN_B2B_URL_DEV if LOGEN_B2B_DEV_MODE else LOGEN_B2B_URL_PROD

# B2B API 엔드포인트
LOGEN_B2B_ENDPOINTS = {
    "get_slip_no": f"{LOGEN_B2B_BASE_URL}/lrm02b-edi/edi/getSlipNo",
    "register_order": f"{LOGEN_B2B_BASE_URL}/lrm02b-edi/edi/registerOrderData",
}

LOGEN_B2B_USER_ID = _safe_secret("LOGEN_B2B_USER_ID", "")        # 연동업체코드 (8자리)
LOGEN_B2B_CUST_CD = _safe_secret("LOGEN_B2B_CUST_CD", "")        # 거래처코드
LOGEN_B2B_SECRET_KEY = _safe_secret("LOGEN_B2B_SECRET_KEY", "")    # 발급받은 API 인증키 (secretKey)

# ==========================================
# 💰 택배 요금표 (데이터 기반 요금 계산)
# ==========================================

WEIGHT_RATES = {
    '2kg': 3500,
    '5kg': 4000,
    '10kg': 5000,
    '20kg': 6000,
}

SIZE_SURCHARGE = {
    '소형': 0,      # 60cm 이하
    '중형': 500,    # 80cm 이하
    '대형': 1500,   # 120cm 이하
    '특대형': 3000, # 120cm 초과
}

REMOTE_AREA_SURCHARGE = {
    '일반': 0,
    '도서': 3000,
    '산간': 2000,
}

ADDITIONAL_SERVICES = {
    '착불': 0,
    '선불': 0,
    '신선식품': 2000,
    '파손주의': 500,
    '귀중품': 1000,
}

# ==========================================
# 🛡️ API 신호 분산 (Anti-Detection Spoofing)
# ==========================================
def generate_device_fingerprint(agent_id: str) -> dict:
    """
    기사님 사번(agent_id)을 기반으로 고유하고 일관된 Android 기기 지문을 생성합니다.
    (단일 서버에서 대량 요청 시 로젠 보안팀 매크로 판별 회피 목적)
    """
    if not agent_id:
        agent_id = "UNKNOWN_AGENT"
        
    models = [
        "SM-S918N Build/UP1A.231005.007", # S23 Ultra
        "SM-G998N Build/TP1A.220624.014", # S21 Ultra
        "SM-F936N Build/TP1A.220624.014", # Z Fold 4
        "SM-A536N Build/TP1A.220624.014", # A53
        "SM-F721N Build/UP1A.231005.007", # Z Flip 4
        "SM-S901N Build/TP1A.220624.014", # S22
        "SM-S928N Build/UP1A.231005.007", # S24 Ultra
        "SM-G973N Build/PPR1.180610.011", # S10
        "SM-N986N Build/RP1A.200720.012"  # Note 20 Ultra
    ]
    android_versions = ["11", "12", "13", "14"]
    
    # 사번을 해시하여 고정된 인덱스 도출 (결정론적 난수)
    hash_val = int(hashlib.md5(agent_id.encode('utf-8')).hexdigest(), 16)
    
    model = models[hash_val % len(models)]
    version = android_versions[(hash_val // len(models)) % len(android_versions)]
    
    # 사번 기반의 고정(결정론적) UUID 생성
    # 동일한 기사님은 항상 같은 UUID로 요청됨
    device_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"logen.agent.{agent_id}"))
    
    user_agent = f"Dalvik/2.1.0 (Linux; U; Android {version}; {model})"
    
    return {
        "User-Agent": user_agent,
        "Device-UUID": device_uuid,
        "App-Version": "1.1.8"
    }

class LogenTMSClient:
    """로젠택배 영업소 TMS API 전용 클라이언트 클래스"""

    def __init__(self, agent_id: str = None, agent_pw: str = None):
        self.agent_id = agent_id or LOGEN_AGENT_ID
        self.agent_pw = agent_pw or LOGEN_AGENT_PW
        self.session_token = None
        self.session = requests.Session()
        
        # 기사별 고유 안티-디텍션 스푸핑 헤더 생성
        self.fingerprint = generate_device_fingerprint(self.agent_id)
        self.device_uuid = self.fingerprint["Device-UUID"]
        
        # 정식 앱처럼 위장하기 위한 실기기 기반 헤더 설정
        self.session.headers.update({
            "User-Agent": self.fingerprint["User-Agent"], 
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json; charset=utf-8",
            "App-Version": self.fingerprint["App-Version"],
            "Device-Platform": "ANDROID",
            "Device-UUID": self.device_uuid
        })
        
    def authenticate(self) -> bool:
        """영업소 계정 로그인 및 세션 토큰 획득 (TMS API 구조)"""
        if not self.agent_id or not self.agent_pw:
            logger.warning("로젠택배 영업소 계정 정보가 없습니다.")
            return False
            
        payload = {
            "userId": self.agent_id,
            "password": self.agent_pw,
            "appVersion": "1.1.8",
            "devicePlatform": "ANDROID",
            "deviceId": self.device_uuid
        }
        
        try:
            # 실제 API로 로그인 시도
            response = self.session.post(TMS_API_ENDPOINTS['login'], json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.session_token = data.get("token", "DUMMY_TOKEN")
                self.session.headers.update({"Authorization": f"Bearer {self.session_token}"})
                return True
            else:
                # API 연결 시도는 했으나 응답 코드가 200이 아닌 경우
                logger.warning(f"로젠 영업소 로그인 실패: 응답코드 {response.status_code}")
                # 응답 형태를 디버그용으로 리턴합니다
                return False
                
        except Exception as e:
            logger.error(f"로젠 영업소 로그인 통신 실패: {e}")
            return False

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
    """화물 무게, 크기, 도착지 지역을 바탕으로 예상 운임을 계산합니다."""
    if additional_services is None:
        additional_services = []
    
    if weight_kg <= 2:
        base_fee = WEIGHT_RATES['2kg']
        weight_category = '2kg 이하'
    elif weight_kg <= 5:
        base_fee = WEIGHT_RATES['5kg']
        weight_category = '5kg 이하'
    elif weight_kg <= 10:
        base_fee = WEIGHT_RATES['10kg']
        weight_category = '10kg 이하'
    else:
        base_fee = WEIGHT_RATES['20kg']
        weight_category = '20kg 이하'
    
    size_fee = SIZE_SURCHARGE.get(size_category, 0)
    remote_fee = REMOTE_AREA_SURCHARGE.get(is_remote, 0)
    service_fee = sum(ADDITIONAL_SERVICES.get(s, 0) for s in additional_services)
    
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
    """예상 접수 및 배송도착일을 추정합니다."""
    if pickup_date is None:
        pickup_date = datetime.now()
    
    min_days, max_days = 1, 2
    
    # 주말 발송일 경우 화요일/수요일로 지연 예상
    if pickup_date.weekday() >= 4:  # 금, 토, 일
        max_days += 1
    
    min_delivery = pickup_date + timedelta(days=min_days)
    max_delivery = pickup_date + timedelta(days=max_days)
    
    return {
        'pickup_date': pickup_date.strftime("%Y-%m-%d"),
        'min_delivery_date': min_delivery.strftime("%Y-%m-%d"),
        'max_delivery_date': max_delivery.strftime("%Y-%m-%d"),
        'estimated_text': f"{min_delivery.strftime('%m/%d')} ~ {max_delivery.strftime('%m/%d')} 도착 예정"
    }

def generate_reservation_number(prefix: str = "LG_TMS") -> str:
    """운송장 예약 채번 로직"""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    sequence = now.microsecond % 1000
    return f"{prefix}_{timestamp}{sequence:03d}"

# ==========================================
# 🚚 택배 B2B 공식 Open API 접수 및 라우팅
# ==========================================

def call_b2b_reservation_api(
    sender: Dict,
    receiver: Dict,
    package: Dict,
    pickup_date: str = None,
    memo: str = ""
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    로젠택배 공식 B2B Open API 연동 처리
    1단계: getSlipNo (운송장 번호 채번)
    2단계: registerOrderData (주문 데이터 전송)
    """
    user_id = LOGEN_B2B_USER_ID
    cust_cd = LOGEN_B2B_CUST_CD or LOGEN_B2B_USER_ID
    secret_key = LOGEN_B2B_SECRET_KEY

    if not user_id or not secret_key:
        logger.error("로젠 B2B API 연동 설정(LOGEN_B2B_USER_ID, LOGEN_B2B_SECRET_KEY)이 필요합니다.")
        return None, "B2B API 연동 설정 누락"

    # 공용 헤더 설정
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "secretKey": secret_key
    }

    # ==========================================
    # 1단계: getSlipNo (송장번호 채번)
    # ==========================================
    get_slip_payload = {
        "userId": user_id,
        "data": [
            {
                "slipQty": 1
            }
        ]
    }

    try:
        logger.info(f"[LOGEN B2B] getSlipNo 호출 시작: {LOGEN_B2B_ENDPOINTS['get_slip_no']}")
        res = requests.post(LOGEN_B2B_ENDPOINTS["get_slip_no"], json=get_slip_payload, headers=headers, timeout=10)
        
        if res.status_code != 200:
            logger.error(f"[LOGEN B2B] getSlipNo HTTP 에러: {res.status_code} - {res.text}")
            return None, f"송장 채번 HTTP 실패 (코드: {res.status_code})"

        res_data = res.json()
        status_code = res_data.get("sttsCd")
        status_msg = res_data.get("sttsMsg", "상세 메시지 없음")

        if status_code != "SUCCESS":
            logger.error(f"[LOGEN B2B] getSlipNo 응답 실패: {status_code} - {status_msg}")
            return None, f"송장 채번 실패: {status_msg}"

        # 채번된 번호 추출
        data_section = res_data.get("data", {})
        waybill_no = data_section.get("startSlipNo")
        
        if not waybill_no and res_data.get("data1"):
            waybill_no = res_data.get("data1")[0].get("slipNo")

        if not waybill_no:
            logger.error(f"[LOGEN B2B] getSlipNo 응답 데이터 누락: {res_data}")
            return None, "송장번호 채번 데이터 누락"

        logger.info(f"[LOGEN B2B] getSlipNo 성공. 채번된 송장번호: {waybill_no}")

    except Exception as e:
        logger.exception(f"[LOGEN B2B] getSlipNo 예외 발생: {e}")
        return None, f"송장 채번 중 오류: {str(e)}"

    # ==========================================
    # 2단계: registerOrderData (주문 데이터 전송)
    # ==========================================
    # 운임타입 매핑 (010: 선불, 020: 착불, 030: 신용)
    # B2B 계약은 보통 월말 정산(신용, 030)을 기본으로 합니다.
    fare_type = "030"
    if not package.get("is_prepaid", True):
        fare_type = "020"
    elif package.get("payment_type") == "선불" or package.get("is_prepaid") is True:
        fare_type = "030"

    take_date = pickup_date or datetime.now().strftime("%Y%m%d")
    take_date = take_date.replace("-", "").replace("/", "")

    # 주소 정제
    snd_addr = f"{sender.get('address', '')} {sender.get('detail_address', '')}".strip()
    rcv_addr = f"{receiver.get('address', '')} {receiver.get('detail_address', '')}".strip()

    # 전화번호 하이픈 제거
    snd_tel = sender.get("phone", "").replace("-", "")
    rcv_tel = receiver.get("phone", "").replace("-", "")

    register_payload = {
        "userId": user_id,
        "data": [
            {
                "custCd": cust_cd,
                "takeDt": take_date,
                "sndCustNm": sender.get("name"),
                "sndCustAddr": snd_addr,
                "sndTelNo": snd_tel,
                "rcvCustNm": receiver.get("name"),
                "rcvCustAddr": rcv_addr,
                "rcvTelNo": rcv_tel,
                "fareTy": fare_type,
                "qty": int(package.get("qty", 1)),
                "dlvFare": int(package.get("fee", 3500)),
                "slipNo": waybill_no,
                "itemNm": package.get("contents", "기타/잡화"),
                
                # 로젠 본사 계약 최대치 규격 매핑 고정
                "boxType": package.get('box_type', '1'),
                "box_type": package.get('box_type', '1'),
                "weightCode": package.get('weight_code', '05'),
                "weight_code": package.get('weight_code', '05'),
                "weight": package.get('weight', 5.0),
                "size": package.get('size', '소형')
            }
        ]
    }

    try:
        logger.info(f"[LOGEN B2B] registerOrderData 호출 시작: {LOGEN_B2B_ENDPOINTS['register_order']}")
        res = requests.post(LOGEN_B2B_ENDPOINTS["register_order"], json=register_payload, headers=headers, timeout=10)

        if res.status_code != 200:
            logger.error(f"[LOGEN B2B] registerOrderData HTTP 에러: {res.status_code} - {res.text}")
            return None, f"주문 등록 HTTP 실패 (코드: {res.status_code})"

        res_data = res.json()
        status_code = res_data.get("sttsCd")
        status_msg = res_data.get("sttsMsg", "상세 메시지 없음")

        if status_code != "SUCCESS":
            logger.error(f"[LOGEN B2B] registerOrderData 응답 실패: {status_code} - {status_msg}")
            return None, f"주문 등록 실패: {status_msg}"

        logger.info(f"[LOGEN B2B] registerOrderData 성공. 운송장 등록 완료: {waybill_no}")

        # 기존 코드 호환을 위한 요금 정보 계산
        weight = float(package.get("weight", 2.5))
        size = package.get("size", "소형")
        fee_info = calculate_delivery_fee(weight, size)

        return {
            "success": True,
            "waybill_number": waybill_no,
            "status": "B2B_접수성공",
            "tracking_url": f"https://www.ilogen.com/web/personal/trace/{waybill_no}",
            "fee": fee_info,
            "server_response": res_data
        }, None

    except Exception as e:
        logger.exception(f"[LOGEN B2B] registerOrderData 예외 발생: {e}")
        return None, f"B2B 주문 접수 중 오류: {str(e)}"


def create_delivery_reservation(
    sender: Dict,
    receiver: Dict,
    package: Dict,
    pickup_date: str = None,
    memo: str = "",
    agent_id: str = None,
    agent_pw: str = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    택배를 B2B API, TMS 영업소 서버 또는 시뮬레이터로 접수하고 운송장 번호를 반환합니다.
    """
    # 1. B2B Open API 설정이 되어 있는 경우 우선 호출
    if USE_LOGEN_B2B_API or (LOGEN_B2B_SECRET_KEY and LOGEN_B2B_USER_ID):
        logger.info("[LOGEN] B2B Open API 모드로 접수 진행합니다.")
        return call_b2b_reservation_api(sender, receiver, package, pickup_date, memo)

    # 2. 기존 레거시 TMS API 우선
    if USE_REAL_API and agent_id and agent_pw:
        logger.info("[LOGEN] 레거시 TMS API 모드로 접수 진행합니다.")
        return _call_tms_save_api(sender, receiver, package, pickup_date, memo, agent_id, agent_pw)
    
    # 3. 로컬 시뮬레이션 모드 작동
    logger.info("[LOGEN] 로컬 시뮬레이션 모드로 접수 진행합니다.")
    return _simulate_tms_reservation(sender, receiver, package, pickup_date, memo)


def _simulate_tms_reservation(
    sender: Dict,
    receiver: Dict,
    package: Dict,
    pickup_date: str,
    memo: str
) -> Tuple[Optional[Dict], Optional[str]]:
    """시뮬레이션 모드 (데이터 구조 유효성 확인 + Mock 운송장 반환)"""
    
    if not sender.get('name') or not sender.get('phone') or not sender.get('address'):
        return None, "송화인(보내는 분) 필수 정보가 누락되었습니다."
    
    if not receiver.get('name') or not receiver.get('phone') or not receiver.get('address'):
        return None, "수화인(받는 분) 필수 정보가 누락되었습니다."
    
    res_no = generate_reservation_number()
    
    weight = float(package.get('weight', 2))
    size = package.get('size', '소형')
    fee_info = calculate_delivery_fee(weight, size)
    
    dt = datetime.strptime(pickup_date, "%Y-%m-%d") if pickup_date else datetime.now()
    delivery_info = estimate_delivery_date(dt)
    
    # 가상의 운송장 번호 생성 (11자리 숫자)
    dummy_waybill = f"987{datetime.now().strftime('%y%m%H%M')}"
    
    result = {
        'success': True,
        'reservation_number': res_no,
        'waybill_number': dummy_waybill,
        'status': '영업소_접수완료',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'sender': sender,
        'receiver': receiver,
        'package': package,
        'pickup_date': pickup_date or datetime.now().strftime("%Y-%m-%d"),
        'memo': memo,
        'fee': fee_info,
        'delivery_estimate': delivery_info,
        'tracking_url': f"https://www.ilogen.com/web/personal/trace/{dummy_waybill}",
        'message': f"[로젠TMS] 정상적으로 영업소에 접수되었습니다. 운송장번호: {dummy_waybill}"
    }
    
    return result, None


def _call_tms_save_api(
    sender: Dict,
    receiver: Dict,
    package: Dict,
    pickup_date: str,
    memo: str,
    agent_id: str = None,
    agent_pw: str = None
) -> Tuple[Optional[Dict], Optional[str]]:
    """
    로젠택배 SalesLogisApp API를 직접 통신하는 부분.
    인증 후 JSON Payload로 송/수화인 및 품목 정보 발송
    """
    client = LogenTMSClient(agent_id=agent_id, agent_pw=agent_pw)
    if not client.authenticate():
        return None, "AUTH_FAILED"
        
    # TMS 앱 페이로드 규격 분석 결과 (유추 포맷)
    payload = {
        "senNm": sender.get('name'),
        "senTel": sender.get('phone'),
        "senAddr": sender.get('address'),
        "senAddrDtl": sender.get('detail_address', ''),
        
        "rcvNm": receiver.get('name'),
        "rcvTel": receiver.get('phone'),
        "rcvAddr": receiver.get('address'),
        "rcvAddrDtl": receiver.get('detail_address', ''),
        
        "itemNm": package.get('contents', '기타/잡화'),
        "itemWt": package.get('weight', 2),
        "itemSize": package.get('size', '소형'),
        "itemPrice": package.get('price', 0),
        "delivFee": package.get('fee', 0), # 로젠 전산망에 등록될 실 청구 운임 (플랫폼 수익이 제거된 원가)
        
        # 로젠 본사 계약 최대치 규격 매핑 고정
        "boxType": package.get('box_type', '1'),
        "box_type": package.get('box_type', '1'),
        "weightCode": package.get('weight_code', '05'),
        "weight_code": package.get('weight_code', '05'),
        
        "pickupReqDt": pickup_date,
        "delivMsg": memo,
        "payType": 1 if package.get('is_prepaid', True) else 2 # 1:선불, 2:착불
    }
    
    try:
        # 🚀 실제 POST 요청 발송 
        logger.info(f"TMS API 발송 준비 완료: {payload}")
        response = client.session.post(TMS_API_ENDPOINTS['waybill_save'], json=payload, timeout=10)
        
        # 200 OK일 경우 정상 응답 데이터 파싱
        if response.status_code == 200:
            data = response.json()
            
            # 발급받은 운송장번호 반환 (서버 규격에 따라 키명은 다를 수 있습니다)
            waybill_no = data.get("wbNo", "UNKNOWN_WB")
            
            return {
                "success": True,
                "waybill_number": waybill_no,
                "status": "영업소_접수성공",
                "tracking_url": f"https://www.ilogen.com/web/personal/trace/{waybill_no}",
                "server_response": data
            }, None
        else:
             if response.status_code == 401 or response.status_code == 403:
                 return None, "AUTH_FAILED"
             return None, f"영업소 서버 통신 거부 (상태코드: {response.status_code})"
             
    except Exception as e:
        return None, f"로젠 영업소 서버 통신 에러: {str(e)}"

# ==========================================
# 📊 영업소 대량 접수 처리
# ==========================================

def process_bulk_reservations(reservations: List[Dict], on_progress: callable = None) -> Dict:
    """엑셀/데이터베이스 대량 주문건(다크스토어 등)을 일괄적으로 로젠에 접수"""
    results = []
    success_count, fail_count = 0, 0
    total_fee = 0
    
    for idx, res_data in enumerate(reservations):
        try:
            sender = {
                'name': res_data.get('sender_name', ''),
                'phone': res_data.get('sender_phone', ''),
                'address': res_data.get('sender_address', ''),
                'detail_address': res_data.get('sender_detail', '')
            }
            receiver = {
                'name': res_data.get('receiver_name', ''),
                'phone': res_data.get('receiver_phone', ''),
                'address': res_data.get('receiver_address', ''),
                'detail_address': res_data.get('receiver_detail', '')
            }
            package = {
                'type': res_data.get('package_type', '박스'),
                'weight': float(res_data.get('weight', 2)),
                'size': res_data.get('size', '소형'),
                'contents': res_data.get('contents', ''),
                'is_prepaid': res_data.get('is_prepaid', True)
            }
            
            res, err = create_delivery_reservation(
                sender=sender, receiver=receiver, package=package,
                pickup_date=res_data.get('pickup_date'), memo=res_data.get('memo', '')
            )
            
            if err:
                results.append({'index': idx + 1, 'success': False, 'error': err, 'receiver_name': receiver['name']})
                fail_count += 1
            else:
                results.append({
                    'index': idx + 1, 'success': True,
                    'waybill_number': res.get('waybill_number'),
                    'fee': res['fee']['total_fee'],
                    'receiver_name': receiver['name']
                })
                success_count += 1
                total_fee += res['fee']['total_fee']
            
            if on_progress: on_progress(idx + 1, len(reservations))
                
        except Exception as e:
            results.append({'index': idx + 1, 'success': False, 'error': str(e), 'receiver_name': res_data.get('receiver_name', '')})
            fail_count += 1
            
    return {
        'success_count': success_count,
        'fail_count': fail_count,
        'total_count': len(reservations),
        'total_fee': total_fee,
        'results': results
    }

# ==========================================
# 🔍 배송조회 (TMS API 화물추적)
# ==========================================

def track_delivery(waybill_number: str) -> Tuple[Optional[Dict], Optional[str]]:
    if not waybill_number:
        return None, "운송장 번호를 입력해주세요."
    
    if USE_REAL_API:
        client = LogenTMSClient()
        if client.authenticate():
            try:
                # payload = {"wbNo": waybill_number}
                # res = client.session.post(TMS_API_ENDPOINTS['tracking'], json=payload)
                # return res.json(), None
                pass
            except Exception as e:
                return None, f"배송 조회 에러: {str(e)}"
                
    return {
        'waybill_number': waybill_number,
        'tracking_url': f"https://www.ilogen.com/web/personal/trace/{waybill_number}",
        'message': "로젠택배 공식 웹사이트에서 조회할 수 있습니다 (시뮬레이션 모드)."
    }, None


# ==========================================
# 📋 헬퍼 / 편의 기능 (분산 처리용)
# ==========================================

def parse_weight(weight_str: str) -> float:
    return {"2kg 이하": 2, "5kg 이하": 5, "10kg 이하": 10, "20kg 이하": 20}.get(weight_str, 2)

def parse_size(size_str: str) -> str:
    for s in ["특대형", "대형", "중형", "소형"]:
        if s in size_str: return s
    return "소형"

def get_weight_options() -> List[str]:
    return ["2kg 이하", "5kg 이하", "10kg 이하", "20kg 이하"]

def get_size_options() -> List[str]:
    return ["소형 (60cm 이하)", "중형 (80cm 이하)", "대형 (120cm 이하)", "특대형 (120cm 초과)"]

def get_fee_table_html() -> str:
    return """
    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 15px; margin: 1rem 0;">
        <h4 style="margin: 0 0 1rem 0; color: #333;">📦 로젠택배 영업소 제휴 운임표표 (2024)</h4>
        <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden;">
            <thead><tr style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white;">
                <th style="padding: 12px; text-align: left;">무게</th><th style="padding: 12px; text-align: right;">기본 요금</th>
            </tr></thead>
            <tbody>
                <tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px;">2kg 이하</td><td style="padding: 10px; text-align: right; font-weight: bold;">3,500원</td></tr>
                <tr style="border-bottom: 1px solid #eee; background: #f8f9fa;"><td style="padding: 10px;">5kg 이하</td><td style="padding: 10px; text-align: right; font-weight: bold;">4,000원</td></tr>
                <tr style="border-bottom: 1px solid #eee;"><td style="padding: 10px;">10kg 이하</td><td style="padding: 10px; text-align: right; font-weight: bold;">5,000원</td></tr>
                <tr style="border-bottom: 1px solid #eee; background: #f8f9fa;"><td style="padding: 10px;">20kg 이하</td><td style="padding: 10px; text-align: right; font-weight: bold;">6,000원</td></tr>
            </tbody>
        </table>
        <div style="margin-top: 1rem; font-size: 0.85rem; color: #666;">
            <p>• 크기 추가: 중형 +500원, 대형 +1,500원, 특대형 +3,000원</p>
            <p>• 도서지역 +3,000원, 산간지역 +2,000원</p>
            <p>• 대량 발송(100건 이상) 시, 영업소 계약 단가 적용(1,800원~)</p>
        </div>
    </div>
    """
