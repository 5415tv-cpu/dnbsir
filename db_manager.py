"""
📊 Google Sheets 데이터베이스 관리 모듈
- 가게 정보 및 주문 내역을 Google Sheets에 저장/조회
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json
import bcrypt

# ==========================================
# 🔐 비밀번호 암호화 유틸리티
# ==========================================

MIN_PASSWORD_LENGTH = 10  # 최소 비밀번호 길이


def validate_password_length(password: str) -> tuple[bool, str]:
    """비밀번호 길이 검증 (최소 10자)"""
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"비밀번호는 최소 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다."
    return True, "OK"


def hash_password(password: str) -> str:
    """비밀번호를 bcrypt로 암호화"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """입력된 비밀번호와 암호화된 비밀번호 비교"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def is_bcrypt_hash(password: str) -> bool:
    """저장된 값이 bcrypt 해시인지 확인 (평문과 구분)"""
    # bcrypt 해시는 '$2b$', '$2a$', '$2y$'로 시작하고 60자
    if not password:
        return False
    return password.startswith(('$2b$', '$2a$', '$2y$')) and len(password) == 60

# ==========================================
# 🔑 Google Sheets 설정
# ==========================================
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 시트 이름
STORES_SHEET = 'stores'
ORDERS_SHEET = 'orders'
SETTINGS_SHEET = 'settings'
CUSTOMERS_SHEET = 'customers'  # 고객 정보 시트

# ==========================================
# 🏢 업종 카테고리 정의
# ==========================================
BUSINESS_CATEGORIES = {
    'restaurant': {'name': '🍽️ 식당/음식점', 'description': '테이블 예약 및 배달 주문'},
    'delivery': {'name': '📦 택배/물류', 'description': '택배 접수 및 배송 추적'},
    'laundry': {'name': '👔 세탁/클리닝', 'description': '세탁물 접수 및 수거 예약'},
    'retail': {'name': '🛒 일반판매', 'description': '상품 구매 및 배송'},
    'service': {'name': '🔧 서비스/수리', 'description': '방문 서비스 예약'},
    'beauty': {'name': '💇 미용/뷰티', 'description': '시술 예약'},
    'farmer': {'name': '🌾 농어민', 'description': '농수산물 직거래 및 배송'},
    'other': {'name': '📋 기타', 'description': '기타 업종'}
}

# ==========================================
# 🍽️ 식당 세부 카테고리
# ==========================================
RESTAURANT_SUBCATEGORIES = {
    'korean': {'name': '🍚 한식', 'icon': '🍚', 'examples': '김치찌개, 불고기, 비빔밥'},
    'chinese': {'name': '🥡 중식', 'icon': '🥡', 'examples': '짜장면, 짬뽕, 탕수육'},
    'japanese': {'name': '🍣 일식', 'icon': '🍣', 'examples': '초밥, 라멘, 돈까스'},
    'western': {'name': '🍝 양식', 'icon': '🍝', 'examples': '파스타, 스테이크, 피자'},
    'chicken': {'name': '🍗 치킨', 'icon': '🍗', 'examples': '후라이드, 양념, 간장치킨'},
    'pizza': {'name': '🍕 피자', 'icon': '🍕', 'examples': '페퍼로니, 콤비네이션'},
    'burger': {'name': '🍔 버거/패스트푸드', 'icon': '🍔', 'examples': '햄버거, 감자튀김'},
    'cafe': {'name': '☕ 카페/디저트', 'icon': '☕', 'examples': '커피, 케이크, 음료'},
    'bakery': {'name': '🥐 베이커리', 'icon': '🥐', 'examples': '빵, 샌드위치, 과자'},
    'snack': {'name': '🍜 분식', 'icon': '🍜', 'examples': '떡볶이, 김밥, 라면'},
    'meat': {'name': '🥩 고기/구이', 'icon': '🥩', 'examples': '삼겹살, 갈비, 소고기'},
    'seafood': {'name': '🦐 해산물', 'icon': '🦐', 'examples': '회, 조개구이, 해물탕'},
    'asian': {'name': '🍜 아시안', 'icon': '🍜', 'examples': '베트남쌀국수, 태국요리'},
    'other_food': {'name': '🍴 기타 음식', 'icon': '🍴', 'examples': '기타 음식점'}
}

# ==========================================
# 📦 택배 세부 카테고리
# ==========================================
DELIVERY_SUBCATEGORIES = {
    'parcel': {'name': '📦 일반택배', 'icon': '📦', 'examples': '소형택배, 등기'},
    'quick': {'name': '🏃 퀵서비스', 'icon': '🏃', 'examples': '오토바이퀵, 당일배송'},
    'freight': {'name': '🚛 화물/대형', 'icon': '🚛', 'examples': '가구, 가전, 대형화물'},
    'food_delivery': {'name': '🛵 음식배달대행', 'icon': '🛵', 'examples': '배달대행, 라이더'}
}

# ==========================================
# 👔 세탁 세부 카테고리
# ==========================================
LAUNDRY_SUBCATEGORIES = {
    'general': {'name': '👔 일반세탁', 'icon': '👔', 'examples': '셔츠, 바지, 정장'},
    'special': {'name': '✨ 특수세탁', 'icon': '✨', 'examples': '가죽, 모피, 웨딩드레스'},
    'shoes': {'name': '👟 신발세탁', 'icon': '👟', 'examples': '운동화, 구두'},
    'bedding': {'name': '🛏️ 이불/침구', 'icon': '🛏️', 'examples': '이불, 베개, 매트리스'}
}

# ==========================================
# 🛒 판매 세부 카테고리
# ==========================================
RETAIL_SUBCATEGORIES = {
    'mart': {'name': '🏪 마트/편의점', 'icon': '🏪', 'examples': '식료품, 생필품'},
    'flower': {'name': '💐 꽃집', 'icon': '💐', 'examples': '꽃다발, 화분, 화환'},
    'pet': {'name': '🐕 반려동물', 'icon': '🐕', 'examples': '사료, 용품, 간식'},
    'electronics': {'name': '📱 전자제품', 'icon': '📱', 'examples': '휴대폰, 컴퓨터, 가전'},
    'fashion': {'name': '👗 패션/의류', 'icon': '👗', 'examples': '옷, 신발, 액세서리'},
    'other_retail': {'name': '🛍️ 기타판매', 'icon': '🛍️', 'examples': '기타 상품'}
}

# ==========================================
# 🌾 농어민 세부 카테고리
# ==========================================
FARMER_SUBCATEGORIES = {
    'rice': {'name': '🌾 쌀/잡곡', 'icon': '🌾', 'examples': '쌀, 현미, 잡곡, 콩'},
    'vegetables': {'name': '🥬 채소류', 'icon': '🥬', 'examples': '배추, 무, 양파, 감자'},
    'fruits': {'name': '🍎 과일류', 'icon': '🍎', 'examples': '사과, 배, 감귤, 포도'},
    'fish': {'name': '🐟 수산물', 'icon': '🐟', 'examples': '생선, 조개, 해조류, 젓갈'},
    'meat': {'name': '🥩 축산물', 'icon': '🥩', 'examples': '한우, 돼지고기, 닭고기, 계란'},
    'processed': {'name': '🫙 가공식품', 'icon': '🫙', 'examples': '김치, 장류, 젓갈, 건어물'},
    'organic': {'name': '🌱 친환경/유기농', 'icon': '🌱', 'examples': '유기농 채소, 무농약 과일'},
    'other_farm': {'name': '🧺 기타 농수산물', 'icon': '🧺', 'examples': '기타 농수산물'}
}


def get_google_sheets_client():
    """Google Sheets 클라이언트 생성"""
    try:
        # Streamlit secrets에서 서비스 계정 정보 가져오기
        credentials_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"❌ Google Sheets 연결 실패: {e}")
        return None


def get_spreadsheet():
    """스프레드시트 가져오기"""
    try:
        client = get_google_sheets_client()
        if client is None:
            return None
        
        spreadsheet_url = st.secrets["spreadsheet_url"]
        spreadsheet = client.open_by_url(spreadsheet_url)
        return spreadsheet
    except Exception as e:
        st.error(f"❌ 스프레드시트 접근 실패: {e}")
        return None


# ==========================================
# 🏪 가게 관리 함수
# ==========================================

def get_all_stores():
    """모든 가게 정보 조회"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return {}
        
        # stores 시트가 없으면 생성
        try:
            worksheet = spreadsheet.worksheet(STORES_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            # 시트가 없으면 자동 생성
            worksheet = spreadsheet.add_worksheet(title=STORES_SHEET, rows=1000, cols=16)
            stores_header = [
                'store_id', 'password', 'name', 'phone', 'info', 'menu_text', 
                'printer_ip', 'img_files', 'status', 'billing_key', 
                'expiry_date', 'payment_status', 'next_payment_date', 'category'
            ]
            worksheet.update('A1:N1', [stores_header])
            return {}  # 새로 만들었으니 빈 딕셔너리 반환
        
        # 데이터가 없는 경우 처리
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:  # 헤더만 있거나 빈 시트
            return {}
        
        records = worksheet.get_all_records()
        
        stores = {}
        for record in records:
            store_id = record.get('store_id', '')
            if store_id:
                stores[store_id] = {
                    'password': record.get('password', ''),
                    'name': record.get('name', ''),
                    'phone': record.get('phone', ''),
                    'info': record.get('info', ''),
                    'menu_text': record.get('menu_text', ''),
                    'printer_ip': record.get('printer_ip', ''),
                    'img_files': record.get('img_files', ''),
                    'status': record.get('status', '미납'),  # 가맹비납부여부
                    # 정기 결제 관련 컬럼 (없으면 기본값)
                    'billing_key': str(record.get('billing_key', '')),
                    'expiry_date': str(record.get('expiry_date', '')),
                    'payment_status': str(record.get('payment_status', '미등록')),
                    'next_payment_date': str(record.get('next_payment_date', '')),
                    # 업종 카테고리 (기본값: restaurant)
                    'category': str(record.get('category', 'restaurant')),
                    # 테이블 정보
                    'table_count': record.get('table_count', 0),
                    'seats_per_table': record.get('seats_per_table', 0)
                }
        return stores
    except Exception as e:
        st.error(f"❌ 가게 정보 조회 실패: {e}")
        st.info("💡 사이드바의 '🔧 시트 초기화' 버튼을 눌러 시트를 초기화해주세요.")
        return {}


def get_store(store_id):
    """특정 가게 정보 조회"""
    stores = get_all_stores()
    return stores.get(store_id)


def save_store(store_id, store_data, encrypt_password=True):
    """
    가게 정보 저장 (신규/수정)
    - encrypt_password: True면 새 비밀번호를 bcrypt로 암호화
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        worksheet = spreadsheet.worksheet(STORES_SHEET)
        
        # 기존 데이터 확인
        records = worksheet.get_all_records()
        row_index = None
        
        for idx, record in enumerate(records):
            if record.get('store_id') == store_id:
                row_index = idx + 2  # 헤더 + 1-based index
                break
        
        # 비밀번호 처리
        password = store_data.get('password', '')
        
        if encrypt_password and password:
            # 이미 bcrypt 해시가 아닌 경우에만 암호화
            if not is_bcrypt_hash(password):
                password = hash_password(password)
        
        row_data = [
            store_id,
            password,  # 암호화된 비밀번호
            store_data.get('name', ''),
            store_data.get('phone', ''),
            store_data.get('info', ''),
            store_data.get('menu_text', ''),
            store_data.get('printer_ip', ''),
            store_data.get('img_files', ''),
            store_data.get('status', '미납'),  # 가맹비납부여부
            # 정기 결제 관련 컬럼
            store_data.get('billing_key', ''),  # 빌링키
            store_data.get('expiry_date', ''),  # 만료일
            store_data.get('payment_status', '미등록'),  # 결제상태
            store_data.get('next_payment_date', ''),  # 다음결제일
            store_data.get('category', 'restaurant'),  # 업종 카테고리
            store_data.get('table_count', 0),  # 테이블 수
            store_data.get('seats_per_table', 0)  # 테이블당 최대 착석 인원
        ]
        
        if row_index:
            # 기존 데이터 수정
            worksheet.update(f'A{row_index}:P{row_index}', [row_data])
        else:
            # 신규 데이터 추가
            worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        st.error(f"❌ 가게 정보 저장 실패: {e}")
        return False


def delete_store(store_id):
    """가게 삭제"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        worksheet = spreadsheet.worksheet(STORES_SHEET)
        records = worksheet.get_all_records()
        
        for idx, record in enumerate(records):
            if record.get('store_id') == store_id:
                worksheet.delete_rows(idx + 2)  # 헤더 + 1-based index
                return True
        
        return False
    except Exception as e:
        st.error(f"❌ 가게 삭제 실패: {e}")
        return False


def update_store_status(store_id, new_status):
    """가맹비 납부 상태 업데이트"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        worksheet = spreadsheet.worksheet(STORES_SHEET)
        records = worksheet.get_all_records()
        
        for idx, record in enumerate(records):
            if record.get('store_id') == store_id:
                worksheet.update_cell(idx + 2, 9, new_status)  # 9번째 열이 status
                return True
        
        return False
    except Exception as e:
        st.error(f"❌ 상태 업데이트 실패: {e}")
        return False


def verify_store_login(store_id, password):
    """
    가맹점 로그인 검증
    - bcrypt 해시된 비밀번호와 기존 평문 비밀번호 모두 지원
    """
    store = get_store(store_id)
    if not store:
        return None
    
    stored_password = store.get('password', '')
    
    # 저장된 비밀번호가 bcrypt 해시인 경우
    if is_bcrypt_hash(stored_password):
        if verify_password(password, stored_password):
            return store
    else:
        # 기존 평문 비밀번호 (하위 호환성)
        if stored_password == password:
            return store
    
    return None


# ==========================================
# 💳 정기 결제 관리 함수
# ==========================================

def update_billing_info(store_id, billing_key, expiry_date, payment_status, next_payment_date):
    """가맹점 정기 결제 정보 업데이트"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        worksheet = spreadsheet.worksheet(STORES_SHEET)
        records = worksheet.get_all_records()
        
        for idx, record in enumerate(records):
            if record.get('store_id') == store_id:
                row = idx + 2  # 헤더 + 1-based index
                # J~M 컬럼 업데이트 (billing_key, expiry_date, payment_status, next_payment_date)
                worksheet.update(f'J{row}:M{row}', [[billing_key, expiry_date, payment_status, next_payment_date]])
                return True
        
        return False
    except Exception as e:
        st.error(f"❌ 결제 정보 업데이트 실패: {e}")
        return False


def update_payment_status(store_id, payment_status):
    """결제 상태만 업데이트"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        worksheet = spreadsheet.worksheet(STORES_SHEET)
        records = worksheet.get_all_records()
        
        for idx, record in enumerate(records):
            if record.get('store_id') == store_id:
                worksheet.update_cell(idx + 2, 12, payment_status)  # 12번째 열이 payment_status
                return True
        
        return False
    except Exception as e:
        st.error(f"❌ 결제 상태 업데이트 실패: {e}")
        return False


def get_expiring_stores(days=7):
    """만료 예정인 가맹점 조회 (N일 이내)"""
    try:
        stores = get_all_stores()
        expiring = []
        today = datetime.now()
        
        for store_id, info in stores.items():
            expiry_str = info.get('expiry_date', '')
            if expiry_str:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
                    days_left = (expiry_date - today).days
                    if 0 <= days_left <= days:
                        expiring.append({
                            'store_id': store_id,
                            'name': info.get('name', ''),
                            'expiry_date': expiry_str,
                            'days_left': days_left,
                            'payment_status': info.get('payment_status', ''),
                            'phone': info.get('phone', '')
                        })
                except:
                    pass
        
        return sorted(expiring, key=lambda x: x['days_left'])
    except Exception as e:
        return []


def get_failed_payment_stores():
    """결제 실패 가맹점 조회"""
    try:
        stores = get_all_stores()
        failed = []
        
        for store_id, info in stores.items():
            if info.get('payment_status') == '실패':
                failed.append({
                    'store_id': store_id,
                    'name': info.get('name', ''),
                    'phone': info.get('phone', ''),
                    'next_payment_date': info.get('next_payment_date', '')
                })
        
        return failed
    except Exception as e:
        return []


# ==========================================
# 📦 주문 관리 함수
# ==========================================

def generate_order_id():
    """주문번호 생성"""
    now = datetime.now()
    return now.strftime("%Y%m%d%H%M%S")


def save_order(order_data):
    """주문 저장"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        
        order_id = generate_order_id()
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row_data = [
            order_id,
            order_time,
            order_data.get('store_id', ''),
            order_data.get('store_name', ''),
            order_data.get('order_content', ''),
            order_data.get('address', ''),
            order_data.get('customer_phone', ''),
            order_data.get('total_price', ''),
            order_data.get('request', ''),
            '접수대기'  # 처리상태
        ]
        
        worksheet.append_row(row_data)
        
        return {
            'order_id': order_id,
            'order_time': order_time,
            **order_data
        }
    except Exception as e:
        st.error(f"❌ 주문 저장 실패: {e}")
        return None


def save_delivery_order(order_data):
    """택배 주문 저장"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        
        order_id = generate_order_id()
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 택배 주문 내용 구성
        delivery_content = f"""[택배 접수]
보내는 분: {order_data.get('sender_name', '')} ({order_data.get('sender_phone', '')})
보내는 주소: {order_data.get('sender_address', '')}
받는 분: {order_data.get('receiver_name', '')} ({order_data.get('receiver_phone', '')})
받는 주소: {order_data.get('receiver_address', '')}
물품: {order_data.get('item_name', '')} ({order_data.get('item_count', 1)}개)
"""
        
        row_data = [
            order_id,
            order_time,
            'delivery',  # 택배 주문
            '택배 접수',
            delivery_content,
            order_data.get('receiver_address', ''),
            order_data.get('sender_phone', ''),
            '',  # 가격
            order_data.get('memo', ''),
            '접수대기'  # 처리상태
        ]
        
        worksheet.append_row(row_data)
        
        return {
            'order_id': order_id,
            'order_time': order_time,
            **order_data
        }
    except Exception as e:
        st.error(f"❌ 택배 주문 저장 실패: {e}")
        return None


def save_logen_reservation(reservation_data):
    """
    로젠택배 예약 저장 (예약번호, 요금 포함)
    
    Args:
        reservation_data: {
            'reservation_number': 예약번호,
            'sender': {name, phone, address, detail_address},
            'receiver': {name, phone, address, detail_address},
            'package': {type, weight, size, contents},
            'fee': {total_fee, ...},
            'pickup_date': 수거일,
            'delivery_estimate': 배송 예상 정보,
            'memo': 메모,
            'status': 상태
        }
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        
        order_id = reservation_data.get('reservation_number', generate_order_id())
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sender = reservation_data.get('sender', {})
        receiver = reservation_data.get('receiver', {})
        package = reservation_data.get('package', {})
        fee = reservation_data.get('fee', {})
        delivery_est = reservation_data.get('delivery_estimate', {})
        
        # 택배 예약 내용 구성
        delivery_content = f"""[로젠택배 예약]
📦 예약번호: {order_id}
📤 보내는 분: {sender.get('name', '')} ({sender.get('phone', '')})
   주소: {sender.get('address', '')} {sender.get('detail_address', '')}
📥 받는 분: {receiver.get('name', '')} ({receiver.get('phone', '')})
   주소: {receiver.get('address', '')} {receiver.get('detail_address', '')}
📋 화물: {package.get('type', '')} / {package.get('weight', '')}kg / {package.get('size', '')}
   내용물: {package.get('contents', '')}
📅 수거일: {reservation_data.get('pickup_date', '')}
🚚 배송예정: {delivery_est.get('estimated_text', '')}
💰 요금: {fee.get('total_fee', 0):,}원 ({fee.get('payment_type', '선불')})
"""
        
        row_data = [
            order_id,
            order_time,
            'logen_delivery',  # 로젠택배
            '로젠택배 예약',
            delivery_content,
            receiver.get('address', ''),
            sender.get('phone', ''),
            str(fee.get('total_fee', '')),  # 요금
            reservation_data.get('memo', ''),
            reservation_data.get('status', '접수완료')  # 처리상태
        ]
        
        worksheet.append_row(row_data)
        
        return {
            'order_id': order_id,
            'order_time': order_time,
            'reservation_number': order_id,
            **reservation_data
        }
    except Exception as e:
        st.error(f"❌ 로젠택배 예약 저장 실패: {e}")
        return None


def save_bulk_logen_reservations(reservations_result):
    """
    대량 로젠택배 예약 저장
    
    Args:
        reservations_result: process_bulk_reservations 함수의 반환값
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        batch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        batch_id = f"BULK_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        saved_count = 0
        
        for result in reservations_result.get('results', []):
            if result.get('success'):
                row_data = [
                    result.get('reservation_number', ''),
                    batch_time,
                    'logen_bulk',  # 대량 택배
                    '로젠택배 대량접수',
                    f"[대량접수 #{result.get('index')}] 보내는분: {result.get('sender_name', '')} → 받는분: {result.get('receiver_name', '')}",
                    '',  # 주소
                    '',  # 연락처
                    str(result.get('fee', '')),  # 요금
                    f"배치ID: {batch_id}",
                    '접수완료'
                ]
                worksheet.append_row(row_data)
                saved_count += 1
        
        return {
            'batch_id': batch_id,
            'saved_count': saved_count,
            'batch_time': batch_time
        }
    except Exception as e:
        st.error(f"❌ 대량 예약 저장 실패: {e}")
        return None


def get_logen_reservations(limit=50):
    """로젠택배 예약 목록 조회"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return []
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        records = worksheet.get_all_records()
        
        # 로젠택배 예약만 필터링
        logen_orders = [
            r for r in records 
            if r.get('store_id') in ['logen_delivery', 'logen_bulk', 'delivery']
        ]
        
        # 최신순 정렬
        logen_orders = sorted(
            logen_orders, 
            key=lambda x: x.get('order_time', ''), 
            reverse=True
        )[:limit]
        
        return logen_orders
    except Exception as e:
        st.error(f"❌ 예약 조회 실패: {e}")
        return []


def save_table_reservation(store_id, reservation_data):
    """테이블 예약 저장"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        
        order_id = generate_order_id()
        order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 예약 내용 구성
        reservation_content = f"""[테이블 예약]
예약일시: {reservation_data.get('reservation_date', '')} {reservation_data.get('reservation_time', '')}
인원: {reservation_data.get('party_size', '')}명
예약자: {reservation_data.get('customer_name', '')}
연락처: {reservation_data.get('customer_phone', '')}
"""
        
        row_data = [
            order_id,
            order_time,
            store_id,
            reservation_data.get('store_name', ''),
            reservation_content,
            '',  # 주소 (예약이므로 없음)
            reservation_data.get('customer_phone', ''),
            '',  # 가격
            reservation_data.get('request', ''),
            '예약대기'  # 처리상태
        ]
        
        worksheet.append_row(row_data)
        
        return {
            'order_id': order_id,
            'order_time': order_time,
            **reservation_data
        }
    except Exception as e:
        st.error(f"❌ 예약 저장 실패: {e}")
        return None


def check_table_availability(store_id, reservation_date, reservation_time, party_size):
    """테이블 가용성 확인"""
    try:
        # 가게 정보 조회
        store = get_store(store_id)
        if not store:
            return {'available': False, 'message': '가게 정보를 찾을 수 없습니다.'}
        
        table_count = int(store.get('table_count', 0) or 0)
        seats_per_table = int(store.get('seats_per_table', 0) or 0)
        
        if table_count == 0 or seats_per_table == 0:
            return {'available': True, 'message': '테이블 정보가 설정되지 않아 예약 가능합니다.'}
        
        # 해당 시간대 예약 현황 조회
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return {'available': False, 'message': '시스템 오류'}
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        records = worksheet.get_all_records()
        
        # 같은 날짜, 비슷한 시간대의 예약 확인
        reserved_tables = 0
        for record in records:
            if record.get('store_id') == store_id:
                content = record.get('order_content', '')
                status = record.get('status', '')
                
                # 취소된 예약 제외
                if '취소' in status:
                    continue
                
                # 테이블 예약인지 확인
                if '[테이블 예약]' in content:
                    # 날짜와 시간 추출
                    if reservation_date in content:
                        reserved_tables += 1
        
        # 필요한 테이블 수 계산
        tables_needed = (int(party_size) + seats_per_table - 1) // seats_per_table
        available_tables = table_count - reserved_tables
        
        if available_tables >= tables_needed:
            return {
                'available': True,
                'message': f'예약 가능합니다! (남은 테이블: {available_tables}개)',
                'available_tables': available_tables,
                'tables_needed': tables_needed
            }
        else:
            return {
                'available': False,
                'message': f'죄송합니다. 해당 시간대에 예약 가능한 테이블이 부족합니다. (남은 테이블: {available_tables}개, 필요 테이블: {tables_needed}개)',
                'available_tables': available_tables,
                'tables_needed': tables_needed
            }
    except Exception as e:
        return {'available': False, 'message': f'가용성 확인 중 오류: {e}'}


def get_orders_by_store(store_id):
    """특정 가게의 주문 내역 조회"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return []
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        records = worksheet.get_all_records()
        
        orders = [r for r in records if r.get('store_id') == store_id]
        return orders
    except Exception as e:
        st.error(f"❌ 주문 조회 실패: {e}")
        return []


def get_all_orders():
    """모든 주문 내역 조회"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return []
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        records = worksheet.get_all_records()
        return records
    except Exception as e:
        st.error(f"❌ 주문 조회 실패: {e}")
        return []


def update_order_status(order_id, new_status):
    """주문 상태 업데이트"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        records = worksheet.get_all_records()
        
        for idx, record in enumerate(records):
            if record.get('order_id') == order_id:
                worksheet.update_cell(idx + 2, 10, new_status)  # 10번째 열이 상태
                return True
        
        return False
    except Exception as e:
        st.error(f"❌ 주문 상태 업데이트 실패: {e}")
        return False


# ==========================================
# ⚙️ 설정 관리 함수
# ==========================================

def get_settings(store_id):
    """가게별 설정 조회"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return {}
        
        worksheet = spreadsheet.worksheet(SETTINGS_SHEET)
        records = worksheet.get_all_records()
        
        for record in records:
            if record.get('store_id') == store_id:
                return record
        
        return {}
    except Exception as e:
        return {}


def save_settings(store_id, settings_data):
    """가게별 설정 저장"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        worksheet = spreadsheet.worksheet(SETTINGS_SHEET)
        records = worksheet.get_all_records()
        
        row_index = None
        for idx, record in enumerate(records):
            if record.get('store_id') == store_id:
                row_index = idx + 2
                break
        
        row_data = [
            store_id,
            settings_data.get('printer_ip', ''),
            settings_data.get('printer_port', '9100'),
            settings_data.get('auto_print', 'Y')
        ]
        
        if row_index:
            worksheet.update(f'A{row_index}:D{row_index}', [row_data])
        else:
            worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        st.error(f"❌ 설정 저장 실패: {e}")
        return False


# ==========================================
# 🔐 마스터 비밀번호 관리
# ==========================================

MASTER_SETTINGS_KEY = "_MASTER_ADMIN_"


def get_master_password():
    """마스터 비밀번호 조회 (암호화된 해시값 반환)"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        
        # settings 시트 가져오기
        try:
            worksheet = spreadsheet.worksheet(SETTINGS_SHEET)
        except:
            return None  # 시트가 없으면 저장된 비밀번호 없음
        
        # 직접 값 조회 (get_all_records 대신)
        try:
            all_values = worksheet.get_all_values()
            
            for idx, row in enumerate(all_values):
                if idx == 0:  # 헤더 건너뛰기
                    continue
                if len(row) > 0 and row[0] == MASTER_SETTINGS_KEY:
                    # printer_ip 컬럼 (B열, index 1)을 비밀번호 저장용으로 사용
                    return row[1] if len(row) > 1 else None
        except:
            return None
        
        return None
    except Exception:
        return None


def save_master_password(new_password: str) -> bool:
    """마스터 비밀번호 저장 (bcrypt 암호화)"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            st.error("❌ 스프레드시트 연결 실패")
            return False
        
        # settings 시트 가져오기 (없으면 생성)
        try:
            worksheet = spreadsheet.worksheet(SETTINGS_SHEET)
        except:
            worksheet = spreadsheet.add_worksheet(title=SETTINGS_SHEET, rows=100, cols=6)
            # 헤더 추가
            worksheet.update('A1:D1', [['store_id', 'printer_ip', 'printer_port', 'auto_print']])
        
        # 비밀번호 암호화
        hashed_password = hash_password(new_password)
        
        # 기존 데이터 확인
        try:
            all_values = worksheet.get_all_values()
            row_index = None
            
            for idx, row in enumerate(all_values):
                if idx == 0:  # 헤더 건너뛰기
                    continue
                if len(row) > 0 and row[0] == MASTER_SETTINGS_KEY:
                    row_index = idx + 1  # 1-based index
                    break
        except:
            row_index = None
            all_values = []
        
        row_data = [MASTER_SETTINGS_KEY, hashed_password, '', '']
        
        if row_index:
            worksheet.update(f'A{row_index}:D{row_index}', [row_data])
        else:
            worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        st.error(f"❌ 마스터 비밀번호 저장 실패: {e}")
        return False


def verify_master_password(password: str) -> bool:
    """마스터 비밀번호 검증"""
    stored_hash = get_master_password()
    
    if stored_hash is None or stored_hash == '':
        # 저장된 비밀번호가 없으면 기본값과 비교
        try:
            default_pw = st.secrets.get("ADMIN_PASSWORD", "admin1234")
        except:
            default_pw = "admin1234"
        return password == default_pw
    
    # bcrypt 해시인 경우
    if is_bcrypt_hash(stored_hash):
        return verify_password(password, stored_hash)
    else:
        # 평문인 경우 (하위 호환성)
        return password == stored_hash


# ==========================================
# 🔧 초기화 함수
# ==========================================

def initialize_sheets():
    """스프레드시트 초기화 (헤더 생성)"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        # stores 시트 헤더 (정기 결제 컬럼 + 업종 컬럼 + 로젠택배 컬럼 포함)
        try:
            stores_ws = spreadsheet.worksheet(STORES_SHEET)
        except:
            stores_ws = spreadsheet.add_worksheet(title=STORES_SHEET, rows=1000, cols=20)
        
        stores_header = [
            'store_id',        # A: 가게 ID
            'password',        # B: 비밀번호
            'name',            # C: 가게명
            'phone',           # D: 연락처
            'info',            # E: 영업정보
            'menu_text',       # F: 메뉴
            'printer_ip',      # G: 프린터 IP
            'img_files',       # H: 이미지 파일
            'status',          # I: 가맹비납부여부
            'billing_key',     # J: 빌링키 (PG사 발급)
            'expiry_date',     # K: 만료일
            'payment_status',  # L: 결제상태 (미등록/정상/만료/실패)
            'next_payment_date',  # M: 다음결제일
            'category',        # N: 업종 카테고리
            'table_count',     # O: 테이블 수
            'seats_per_table', # P: 테이블당 최대 착석 인원
            'logen_id',        # Q: 로젠택배 아이디
            'logen_password',  # R: 로젠택배 비밀번호
            'logen_sender_name',    # S: 로젠택배 발송인명
            'logen_sender_address'  # T: 로젠택배 발송인 주소
        ]
        stores_ws.update('A1:T1', [stores_header])
        
        # orders 시트 헤더
        try:
            orders_ws = spreadsheet.worksheet(ORDERS_SHEET)
        except:
            orders_ws = spreadsheet.add_worksheet(title=ORDERS_SHEET, rows=10000, cols=12)
        
        orders_header = ['order_id', 'order_time', 'store_id', 'store_name', 'order_content', 
                        'address', 'customer_phone', 'total_price', 'request', 'status']
        orders_ws.update('A1:J1', [orders_header])
        
        # settings 시트 헤더
        try:
            settings_ws = spreadsheet.worksheet(SETTINGS_SHEET)
        except:
            settings_ws = spreadsheet.add_worksheet(title=SETTINGS_SHEET, rows=100, cols=6)
        
        settings_header = ['store_id', 'printer_ip', 'printer_port', 'auto_print']
        settings_ws.update('A1:D1', [settings_header])
        
        # customers 시트 헤더 (고객 정보)
        try:
            customers_ws = spreadsheet.worksheet(CUSTOMERS_SHEET)
        except:
            customers_ws = spreadsheet.add_worksheet(title=CUSTOMERS_SHEET, rows=10000, cols=12)
        
        customers_header = [
            'customer_id',      # A: 고객 ID (전화번호)
            'store_id',         # B: 가게 ID
            'name',             # C: 고객 이름
            'phone',            # D: 전화번호
            'address',          # E: 주소
            'preferences',      # F: 취향/선호사항
            'notes',            # G: 요청사항/메모
            'total_orders',     # H: 총 주문 횟수
            'last_visit',       # I: 마지막 이용일
            'first_visit',      # J: 첫 이용일
            'created_at',       # K: 생성일
            'updated_at'        # L: 수정일
        ]
        customers_ws.update('A1:L1', [customers_header])
        
        return True
    except Exception as e:
        st.error(f"❌ 시트 초기화 실패: {e}")
        return False


# ==========================================
# 👤 고객 정보 관리 (Customer Memory)
# ==========================================

def get_customer(customer_id, store_id=None):
    """
    고객 정보 조회
    
    Args:
        customer_id: 고객 ID (전화번호)
        store_id: 가게 ID (선택, 특정 가게의 고객만 조회)
    
    Returns:
        고객 정보 딕셔너리 또는 None
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return None
        
        # customers 시트 가져오기 (없으면 생성)
        try:
            worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        except:
            return None
        
        records = worksheet.get_all_records()
        
        for record in records:
            if record.get('customer_id') == customer_id:
                if store_id is None or record.get('store_id') == store_id:
                    return {
                        'customer_id': record.get('customer_id', ''),
                        'store_id': record.get('store_id', ''),
                        'name': record.get('name', ''),
                        'phone': record.get('phone', ''),
                        'address': record.get('address', ''),
                        'preferences': record.get('preferences', ''),
                        'notes': record.get('notes', ''),
                        'total_orders': int(record.get('total_orders', 0) or 0),
                        'last_visit': record.get('last_visit', ''),
                        'first_visit': record.get('first_visit', ''),
                        'created_at': record.get('created_at', ''),
                        'updated_at': record.get('updated_at', '')
                    }
        
        return None
    except Exception as e:
        return None


def get_customer_by_phone(phone, store_id=None):
    """전화번호로 고객 조회"""
    # 전화번호 정규화 (하이픈 제거)
    normalized_phone = phone.replace('-', '').replace(' ', '')
    return get_customer(normalized_phone, store_id)


def save_customer(customer_data):
    """
    고객 정보 저장 (신규/수정)
    
    Args:
        customer_data: {
            'customer_id': 고객 ID (전화번호),
            'store_id': 가게 ID,
            'name': 이름,
            'phone': 전화번호,
            'address': 주소,
            'preferences': 취향/선호사항,
            'notes': 요청사항/메모
        }
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        # customers 시트 가져오기 (없으면 생성)
        try:
            worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        except:
            worksheet = spreadsheet.add_worksheet(title=CUSTOMERS_SHEET, rows=10000, cols=12)
            customers_header = [
                'customer_id', 'store_id', 'name', 'phone', 'address',
                'preferences', 'notes', 'total_orders', 'last_visit',
                'first_visit', 'created_at', 'updated_at'
            ]
            worksheet.update('A1:L1', [customers_header])
        
        customer_id = customer_data.get('customer_id', '')
        if not customer_id:
            # 전화번호를 customer_id로 사용
            customer_id = customer_data.get('phone', '').replace('-', '').replace(' ', '')
        
        store_id = customer_data.get('store_id', '')
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 기존 데이터 확인
        records = worksheet.get_all_records()
        row_index = None
        existing_data = None
        
        for idx, record in enumerate(records):
            if record.get('customer_id') == customer_id:
                if store_id == '' or record.get('store_id') == store_id:
                    row_index = idx + 2  # 헤더 + 1-based index
                    existing_data = record
                    break
        
        if existing_data:
            # 기존 데이터 수정 (기존 값 유지하면서 새 값으로 업데이트)
            row_data = [
                customer_id,
                store_id or existing_data.get('store_id', ''),
                customer_data.get('name') or existing_data.get('name', ''),
                customer_data.get('phone') or existing_data.get('phone', ''),
                customer_data.get('address') or existing_data.get('address', ''),
                customer_data.get('preferences') or existing_data.get('preferences', ''),
                customer_data.get('notes') or existing_data.get('notes', ''),
                existing_data.get('total_orders', 0),  # 주문 횟수는 별도 함수로 증가
                existing_data.get('last_visit', ''),   # 마지막 방문은 별도 함수로 업데이트
                existing_data.get('first_visit', ''),
                existing_data.get('created_at', ''),
                now  # updated_at
            ]
            worksheet.update(f'A{row_index}:L{row_index}', [row_data])
        else:
            # 신규 데이터 추가
            row_data = [
                customer_id,
                store_id,
                customer_data.get('name', ''),
                customer_data.get('phone', ''),
                customer_data.get('address', ''),
                customer_data.get('preferences', ''),
                customer_data.get('notes', ''),
                0,      # total_orders
                '',     # last_visit
                now,    # first_visit
                now,    # created_at
                now     # updated_at
            ]
            worksheet.append_row(row_data)
        
        return True
    except Exception as e:
        return False


def update_customer_field(customer_id, field_name, field_value, store_id=None):
    """
    고객의 특정 필드만 업데이트
    
    Args:
        customer_id: 고객 ID
        field_name: 필드명 ('name', 'address', 'preferences', 'notes' 등)
        field_value: 새 값
        store_id: 가게 ID (선택)
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
        
        worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        records = worksheet.get_all_records()
        
        # 필드 인덱스 매핑
        field_map = {
            'name': 3,           # C열
            'phone': 4,          # D열
            'address': 5,        # E열
            'preferences': 6,    # F열
            'notes': 7,          # G열
            'total_orders': 8,   # H열
            'last_visit': 9,     # I열
        }
        
        col_index = field_map.get(field_name)
        if not col_index:
            return False
        
        for idx, record in enumerate(records):
            if record.get('customer_id') == customer_id:
                if store_id is None or record.get('store_id') == store_id:
                    row_index = idx + 2
                    worksheet.update_cell(row_index, col_index, field_value)
                    # updated_at 업데이트
                    worksheet.update_cell(row_index, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    return True
        
        return False
    except Exception as e:
        return False


def increment_customer_order(customer_id, store_id=None):
    """
    고객 주문 횟수 증가 및 마지막 방문일 업데이트
    
    Args:
        customer_id: 고객 ID
        store_id: 가게 ID
    
    Returns:
        업데이트된 주문 횟수
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return 0
        
        worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        records = worksheet.get_all_records()
        
        for idx, record in enumerate(records):
            if record.get('customer_id') == customer_id:
                if store_id is None or record.get('store_id') == store_id:
                    row_index = idx + 2
                    current_orders = int(record.get('total_orders', 0) or 0)
                    new_orders = current_orders + 1
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # total_orders, last_visit, updated_at 업데이트
                    worksheet.update_cell(row_index, 8, new_orders)      # H열: total_orders
                    worksheet.update_cell(row_index, 9, now)             # I열: last_visit
                    worksheet.update_cell(row_index, 12, now)            # L열: updated_at
                    
                    return new_orders
        
        return 0
    except Exception as e:
        return 0


def get_all_customers(store_id=None, limit=100):
    """
    고객 목록 조회
    
    Args:
        store_id: 가게 ID (선택, 특정 가게의 고객만)
        limit: 최대 조회 수
    
    Returns:
        고객 목록
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return []
        
        worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        records = worksheet.get_all_records()
        
        customers = []
        for record in records:
            if store_id is None or record.get('store_id') == store_id:
                customers.append({
                    'customer_id': record.get('customer_id', ''),
                    'store_id': record.get('store_id', ''),
                    'name': record.get('name', ''),
                    'phone': record.get('phone', ''),
                    'address': record.get('address', ''),
                    'preferences': record.get('preferences', ''),
                    'notes': record.get('notes', ''),
                    'total_orders': int(record.get('total_orders', 0) or 0),
                    'last_visit': record.get('last_visit', ''),
                    'first_visit': record.get('first_visit', '')
                })
        
        # 최신 방문 순으로 정렬
        customers = sorted(customers, key=lambda x: x.get('last_visit', ''), reverse=True)
        
        return customers[:limit]
    except Exception as e:
        return []


def search_customers(query, store_id=None):
    """
    고객 검색 (이름, 전화번호, 주소로)
    
    Args:
        query: 검색어
        store_id: 가게 ID (선택)
    
    Returns:
        검색 결과 목록
    """
    try:
        customers = get_all_customers(store_id, limit=1000)
        
        results = []
        query_lower = query.lower()
        
        for customer in customers:
            if (query_lower in customer.get('name', '').lower() or
                query_lower in customer.get('phone', '').replace('-', '') or
                query_lower in customer.get('address', '').lower()):
                results.append(customer)
        
        return results
    except Exception as e:
        return []

