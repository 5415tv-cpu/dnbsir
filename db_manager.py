"""
📊 Google Sheets 데이터베이스 관리 모듈
- 가게 정보 및 주문 내역을 Google Sheets에 저장/조회
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
import json
import bcrypt
import time
import random

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
    if not password or not isinstance(password, str):
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
INQUIRIES_SHEET = 'inquiries'  # 가맹 가입 문의 시트
PERFORMANCE_SHEET = 'performance'  # 동네비서 실적 시트
USER_MANAGEMENT_SHEET = '유저관리'
GENERAL_RESERVATION_SHEET = '매장예약'
DELIVERY_RECEIPT_SHEET = '택배접수'
FARMER_LEDGER_SHEET = '직거래장부'

USER_MANAGEMENT_HEADER = [
    '가입일시', '아이디', '비밀번호', '상호명', '유저 등급', '연락처',
    '총 결제금액', '사장님수수료', '정산예정일', '정산상태',
    '점주 정산액', '070번호', '요금제상태'
]
GENERAL_RESERVATION_HEADER = [
    '일시', '요일', '고객명', '연락처', '메뉴/인원', '인원', '예약시간', 'AI응대여부', '결제금액', '매출액'
]
DELIVERY_RECEIPT_HEADER = [
    '접수일시', '요일', '발송인명', '수령인명', '수령인 주소(AI추출)', '물품종류', '운송장번호(로젠발급)', '수수료(마진)', '수수료', '상태'
]
FARMER_LEDGER_HEADER = [
    '주문일시', '요일', '품목', '수량', '주문금액', '입금확인여부', '배송지주소', '결제주문번호', '고객문의사항'
]

# ==========================================
# 🏢 업종 카테고리 정의 (로고 삭제 버전)
# ==========================================
BUSINESS_CATEGORIES = {
    'restaurant': {'name': '식당/음식점', 'description': '테이블 예약 및 배달 주문'},
    'delivery': {'name': '택배/물류', 'description': '택배 접수 및 배송 추적'},
    'laundry': {'name': '세탁/클리닝', 'description': '세탁물 접수 및 수거 예약'},
    'retail': {'name': '일반판매', 'description': '상품 구매 및 배송'},
    'service': {'name': '서비스/수리', 'description': '방문 서비스 예약'},
    'beauty': {'name': '미용/뷰티', 'description': '시술 예약'},
    'farmer': {'name': '농어민', 'description': '농수산물 직거래 및 배송'},
    'other': {'name': '기타', 'description': '기타 업종'}
}

# ==========================================
# 식당 세부 카테고리
# ==========================================
RESTAURANT_SUBCATEGORIES = {
    'korean': {'name': '한식', 'icon': '', 'examples': '김치찌개, 불고기, 비빔밥'},
    'chinese': {'name': '중식', 'icon': '', 'examples': '짜장면, 짬뽕, 탕수육'},
    'japanese': {'name': '일식', 'icon': '', 'examples': '초밥, 라멘, 돈까스'},
    'western': {'name': '양식', 'icon': '', 'examples': '파스타, 스테이크, 피자'},
    'chicken': {'name': '치킨', 'icon': '', 'examples': '후라이드, 양념, 간장치킨'},
    'pizza': {'name': '피자', 'icon': '', 'examples': '페퍼로니, 콤비네이션'},
    'burger': {'name': '버거/패스트푸드', 'icon': '', 'examples': '햄버거, 감자튀김'},
    'cafe': {'name': '카페/디저트', 'icon': '', 'examples': '커피, 케이크, 음료'},
    'bakery': {'name': '베이커리', 'icon': '', 'examples': '빵, 샌드위치, 과자'},
    'snack': {'name': '분식', 'icon': '', 'examples': '떡볶이, 김밥, 라면'},
    'meat': {'name': '고기/구이', 'icon': '', 'examples': '삼겹살, 갈비, 소고기'},
    'seafood': {'name': '해산물', 'icon': '', 'examples': '회, 조개구이, 해물탕'},
    'asian': {'name': '아시안', 'icon': '', 'examples': '베트남쌀국수, 태국요리'},
    'other_food': {'name': '기타 음식', 'icon': '', 'examples': '기타 음식점'}
}

# ==========================================
# 택배 세부 카테고리
# ==========================================
DELIVERY_SUBCATEGORIES = {
    'parcel': {'name': '일반택배', 'icon': '', 'examples': '소형택배, 등기'},
    'quick': {'name': '퀵서비스', 'icon': '', 'examples': '오토바이퀵, 당일배송'},
    'freight': {'name': '화물/대형', 'icon': '', 'examples': '가구, 가전, 대형화물'},
    'food_delivery': {'name': '음식배달대행', 'icon': '', 'examples': '배달대행, 라이더'}
}

# ==========================================
# 세탁 세부 카테고리
# ==========================================
LAUNDRY_SUBCATEGORIES = {
    'general': {'name': '일반세탁', 'icon': '', 'examples': '셔츠, 바지, 정장'},
    'special': {'name': '특수세탁', 'icon': '', 'examples': '가죽, 모피, 웨딩드레스'},
    'shoes': {'name': '신발세탁', 'icon': '', 'examples': '운동화, 구두'},
    'bedding': {'name': '이불/침구', 'icon': '', 'examples': '이불, 베개, 매트리스'}
}

# ==========================================
# 판매 세부 카테고리
# ==========================================
RETAIL_SUBCATEGORIES = {
    'mart': {'name': '마트/편의점', 'icon': '', 'examples': '식료품, 생필품'},
    'flower': {'name': '꽃집', 'icon': '', 'examples': '꽃다발, 화분, 화환'},
    'pet': {'name': '반려동물', 'icon': '', 'examples': '사료, 용품, 간식'},
    'electronics': {'name': '전자제품', 'icon': '', 'examples': '휴대폰, 컴퓨터, 가전'},
    'fashion': {'name': '패션/의류', 'icon': '', 'examples': '옷, 신발, 액세서리'},
    'other_retail': {'name': '기타판매', 'icon': '', 'examples': '기타 상품'}
}

# ==========================================
# 농어민 세부 카테고리
# ==========================================
FARMER_SUBCATEGORIES = {
    'rice': {'name': '쌀/잡곡', 'icon': '', 'examples': '쌀, 현미, 잡곡, 콩'},
    'vegetables': {'name': '채소류', 'icon': '', 'examples': '배추, 무, 양파, 감자'},
    'fruits': {'name': '과일류', 'icon': '', 'examples': '사과, 배, 감귤, 포도'},
    'fish': {'name': '수산물', 'icon': '', 'examples': '생선, 조개, 해조류, 젓갈'},
    'meat': {'name': '축산물', 'icon': '', 'examples': '한우, 돼지고기, 닭고기, 계란'},
    'processed': {'name': '가공식품', 'icon': '', 'examples': '김치, 장류, 젓갈, 건어물'},
    'organic': {'name': '친환경/유기농', 'icon': '', 'examples': '유기농 채소, 무농약 과일'},
    'other_farm': {'name': '기타 농수산물', 'icon': '', 'examples': '기타 농수산물'}
}


@st.cache_resource(ttl=3600) # 1시간 동안 클라이언트 유지
def get_google_sheets_client():
    """Google Sheets 클라이언트 생성 (캐싱 적용)"""
    try:
        credentials_dict = st.secrets.get("gcp_service_account")
        if not credentials_dict:
            st.error("Google Sheets 서비스 계정 설정이 없습니다. secrets.toml을 확인해주세요.")
            return None
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Google Sheets 인증 실패: {e}")
        return None


def get_spreadsheet(retries=3):
    """스프레드시트 가져오기 (재시도 로직 포함)"""
    for i in range(retries):
        try:
            client = get_google_sheets_client()
            if client is None:
                continue
            
            spreadsheet_url = st.secrets.get("spreadsheet_url", "")
            if not spreadsheet_url:
                st.error("spreadsheet_url 설정이 없습니다. secrets.toml을 확인해주세요.")
                return None
            spreadsheet = client.open_by_url(spreadsheet_url)
            return spreadsheet
        except Exception as e:
            if "500" in str(e) or "Internal error" in str(e):
                if i < retries - 1:
                    wait_time = (i + 1) * 2 + random.random()
                    time.sleep(wait_time)
                    continue
            st.error(f"스프레드시트 접근 실패: {e}")
            return None


@st.cache_resource(ttl=300)
def get_spreadsheet_cached():
    """스프레드시트 객체 캐싱 (읽기 최적화용)"""
    spreadsheet = get_spreadsheet()
    if spreadsheet is None:
        raise RuntimeError("스프레드시트를 찾을 수 없습니다.")
    return spreadsheet


def _get_spreadsheet_for_read():
    """읽기용 스프레드시트 (캐시 우선)"""
    try:
        return get_spreadsheet_cached()
    except Exception:
        return get_spreadsheet()


def _clear_data_cache():
    """읽기 캐시 초기화"""
    try:
        st.cache_data.clear()
    except Exception:
        pass


def _get_or_create_worksheet(spreadsheet, title, headers, rows=1000, cols=30):
    """워크시트 존재 보장 및 헤더 세팅"""
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
        worksheet.update('A1:Z1', [headers])
        return worksheet

    try:
        existing = worksheet.get_all_values()
        if not existing or not existing[0]:
            worksheet.update('A1:Z1', [headers])
        else:
            current_header = existing[0]
            merged_header = current_header + [h for h in headers if h not in current_header]
            if merged_header != current_header:
                end_cell = gspread.utils.rowcol_to_a1(1, len(merged_header))
                worksheet.update(f"A1:{end_cell}", [merged_header])
    except Exception:
        worksheet.update('A1:Z1', [headers])

    return worksheet


def save_to_google_sheet(user_type, data):
    """
    사업자 유형에 맞는 워크시트에 데이터 저장
    - user_type: "일반사업자" | "택배사업자" | "농어민"
    - data: dict(헤더 기반) 또는 list(행 데이터)
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False, "스프레드시트를 찾을 수 없습니다."

        if user_type == "일반사업자":
            worksheet = _get_or_create_worksheet(spreadsheet, GENERAL_RESERVATION_SHEET, GENERAL_RESERVATION_HEADER)
            header = GENERAL_RESERVATION_HEADER
        elif user_type == "택배사업자":
            worksheet = _get_or_create_worksheet(spreadsheet, DELIVERY_RECEIPT_SHEET, DELIVERY_RECEIPT_HEADER)
            header = DELIVERY_RECEIPT_HEADER
        elif user_type == "농어민":
            worksheet = _get_or_create_worksheet(spreadsheet, FARMER_LEDGER_SHEET, FARMER_LEDGER_HEADER)
            header = FARMER_LEDGER_HEADER
        else:
            return False, "지원하지 않는 사업자 유형입니다."

        if isinstance(data, dict):
            row_data = dict(data)

            def _infer_weekday(value: str) -> str:
                if not value:
                    return ""
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y.%m.%d %H:%M:%S", "%Y.%m.%d"):
                    try:
                        dt = datetime.strptime(value, fmt)
                        return ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
                    except Exception:
                        continue
                return ""

            if "요일" in header and not row_data.get("요일"):
                if user_type == "일반사업자":
                    row_data["요일"] = _infer_weekday(row_data.get("일시"))
                elif user_type == "택배사업자":
                    row_data["요일"] = _infer_weekday(row_data.get("접수일시"))
                elif user_type == "농어민":
                    row_data["요일"] = _infer_weekday(row_data.get("주문일시"))

            if user_type == "일반사업자" and "매출액" in header:
                if not row_data.get("매출액"):
                    row_data["매출액"] = row_data.get("결제금액", "")

            if user_type == "택배사업자":
                if "수수료" in header and not row_data.get("수수료"):
                    row_data["수수료"] = row_data.get("수수료(마진)", "")
                if "상태" in header and not row_data.get("상태"):
                    row_data["상태"] = "접수완료"

            if user_type == "농어민" and "주문금액" in header:
                if not row_data.get("주문금액"):
                    row_data["주문금액"] = row_data.get("매출액") or row_data.get("결제금액", "")

            row = [row_data.get(col, '') for col in header]
        else:
            row = data

        worksheet.append_row(row)
        _clear_data_cache()
        return True, "저장 완료"
    except Exception as e:
        st.error(f"유형별 시트 저장 실패: {e}")
        return False, str(e)


def save_user_management(user_data):
    """유저 관리 탭 저장 (회원가입 정보 기록)"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False, "스프레드시트를 찾을 수 없습니다."

        worksheet = _get_or_create_worksheet(spreadsheet, USER_MANAGEMENT_SHEET, USER_MANAGEMENT_HEADER)
        if isinstance(user_data, dict):
            row = [user_data.get(col, '') for col in USER_MANAGEMENT_HEADER]
        else:
            row = user_data
        worksheet.append_row(row)
        _clear_data_cache()
        return True, "저장 완료"
    except Exception as e:
        st.error(f"유저 관리 저장 실패: {e}")
        return False, str(e)


def _migrate_user_management_columns(worksheet):
    """유저관리 헤더를 G~J에 정산 컬럼으로 확장/이동"""
    values = worksheet.get_all_values()
    if not values:
        worksheet.update('A1:M1', [USER_MANAGEMENT_HEADER])
        return

    header = values[0]
    if "총 결제금액" in header and "정산상태" in header and "점주 정산액" in header:
        return

    if "연락처" not in header:
        worksheet.update('A1:M1', [USER_MANAGEMENT_HEADER])
        return

    new_header = USER_MANAGEMENT_HEADER
    new_rows = [new_header]
    for row in values[1:]:
        row = row + [""] * (len(header) - len(row))
        row_map = {h: row[i] for i, h in enumerate(header)}
        if "유저 등급" not in row_map and "사업자유형" in row_map:
            row_map["유저 등급"] = row_map.get("사업자유형", "")
        new_row = [row_map.get(col, "") for col in new_header]
        new_rows.append(new_row)

    end_cell = gspread.utils.rowcol_to_a1(len(new_rows), len(new_header))
    worksheet.update(f"A1:{end_cell}", new_rows)


def _add_business_days(start_date, days=5):
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def update_user_plan_status(store_id=None, phone=None, plan_status="결제완료",
                            payment_amount=None, owner_fee=None,
                            settlement_date=None, settlement_status=None):
    """유저관리 시트의 요금제 상태 업데이트"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False, "스프레드시트를 찾을 수 없습니다."

        worksheet = _get_or_create_worksheet(spreadsheet, USER_MANAGEMENT_SHEET, USER_MANAGEMENT_HEADER)
        _migrate_user_management_columns(worksheet)
        header = worksheet.row_values(1)
        try:
            id_col = header.index("아이디") + 1
        except ValueError:
            id_col = None
        try:
            phone_col = header.index("연락처") + 1
        except ValueError:
            phone_col = None
        try:
            level_col = header.index("유저 등급") + 1
        except ValueError:
            level_col = None
        try:
            status_col = header.index("요금제상태") + 1
        except ValueError:
            status_col = None
        try:
            pay_col = header.index("총 결제금액") + 1
            fee_col = header.index("사장님수수료") + 1
            settle_date_col = header.index("정산예정일") + 1
            settle_status_col = header.index("정산상태") + 1
            net_col = header.index("점주 정산액") + 1
        except ValueError:
            pay_col = fee_col = net_col = settle_date_col = settle_status_col = None

        identifier = store_id or phone
        if not identifier or not status_col:
            return False, "아이디/연락처 또는 요금제 상태 컬럼이 없습니다."

        target_col = id_col if store_id and id_col else phone_col
        if not target_col:
            return False, "아이디/연락처 컬럼을 찾을 수 없습니다."

        cell = worksheet.find(str(identifier), in_column=target_col)
        if not cell:
            return False, "유저관리에서 대상 아이디를 찾을 수 없습니다."

        worksheet.update_cell(cell.row, status_col, plan_status)
        # 등급에 따라 수수료율 결정
        if level_col:
            level_val = worksheet.cell(cell.row, level_col).value or ""
        else:
            level_val = ""
        fee_rate = 0.04 if "프리미엄" in level_val else 0.05

        if pay_col and payment_amount is not None:
            worksheet.update_cell(cell.row, pay_col, str(payment_amount))

        computed_fee = None
        if payment_amount is not None:
            computed_fee = int(round(float(payment_amount) * fee_rate))

        if fee_col:
            worksheet.update_cell(cell.row, fee_col, str(computed_fee if computed_fee is not None else owner_fee or ""))

        if not settlement_date and settle_date_col:
            settlement_date = _add_business_days(datetime.now(), 5).strftime("%Y-%m-%d")
        if settle_date_col and settlement_date:
            worksheet.update_cell(cell.row, settle_date_col, str(settlement_date))

        if settle_status_col:
            worksheet.update_cell(cell.row, settle_status_col, str(settlement_status or "대기"))

        if net_col and payment_amount is not None and computed_fee is not None:
            net_amount = int(round(float(payment_amount) - computed_fee))
            worksheet.update_cell(cell.row, net_col, str(net_amount))
        _clear_data_cache()
        return True, "업데이트 완료"
    except Exception as e:
        st.error(f"요금제 상태 업데이트 실패: {e}")
        return False, str(e)


def update_user_to_paid(user_id):
    """결제 성공 시 유저 요금제 상태를 '유료'로 변경"""
    return update_user_plan_status(store_id=user_id, plan_status="유료")




def update_farmer_payment_status(order_id, status="결제완료"):
    """직거래장부에서 결제 상태 업데이트"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False, "스프레드시트를 찾을 수 없습니다."

        worksheet = _get_or_create_worksheet(spreadsheet, FARMER_LEDGER_SHEET, FARMER_LEDGER_HEADER)
        header = worksheet.row_values(1)
        try:
            order_col = header.index("결제주문번호") + 1
            status_col = header.index("입금확인여부") + 1
        except ValueError:
            return False, "직거래장부 헤더가 올바르지 않습니다."

        cell = worksheet.find(str(order_id), in_column=order_col)
        if not cell:
            return False, "직거래장부에서 결제주문번호를 찾을 수 없습니다."

        worksheet.update_cell(cell.row, status_col, status)
        _clear_data_cache()
        return True, "업데이트 완료"
    except Exception as e:
        st.error(f"직거래장부 상태 업데이트 실패: {e}")
        return False, str(e)


@st.cache_data(ttl=30)
def get_business_data(user_type):
    """
    사업자 유형별 장부 데이터를 DataFrame으로 반환
    - user_type: "일반사업자" | "택배사업자" | "농어민"
    """
    try:
        spreadsheet = _get_spreadsheet_for_read()
        if spreadsheet is None:
            return pd.DataFrame()

        if user_type == "일반사업자":
            sheet_name = GENERAL_RESERVATION_SHEET
        elif user_type == "택배사업자":
            sheet_name = DELIVERY_RECEIPT_SHEET
        else:
            sheet_name = FARMER_LEDGER_SHEET

        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"장부 데이터 로드 실패: {e}")
        return pd.DataFrame()


def analyze_weekly_stats(df, user_type):
    """
    요일별 통계를 계산하여 dict 반환
    - 반환: {"매출": [..7개..], "증감": "▲ 12%"}
    """
    if df is None or df.empty:
        return {"매출": [85, 72, 98, 79, 125, 140, 60], "증감": "▲ 12%"}

    if user_type == "일반사업자":
        time_col = "일시"
        value_col = "결제금액"
    elif user_type == "택배사업자":
        time_col = "접수일시"
        value_col = "수수료(마진)"
    else:
        time_col = "주문일시"
        value_col = None

    if time_col not in df.columns:
        return {"매출": [85, 72, 98, 79, 125, 140, 60], "증감": "▲ 12%"}

    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    df = df.dropna(subset=[time_col])
    df["요일"] = df[time_col].dt.dayofweek  # 0=월 ... 6=일

    if value_col and value_col in df.columns:
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
        grouped = df.groupby("요일")[value_col].sum()
    else:
        grouped = df.groupby("요일").size()

    week_values = [int(grouped.get(i, 0)) for i in range(7)]
    return {"매출": week_values, "증감": "▲ 12%"}


# ==========================================
# 🏪 가게 관리 함수
# ==========================================

@st.cache_data(ttl=30)
def get_all_stores():
    """모든 가게 정보 조회"""
    try:
        spreadsheet = _get_spreadsheet_for_read()
        if spreadsheet is None:
            return {}
        
        # stores 시트가 없으면 생성
        try:
            worksheet = spreadsheet.worksheet(STORES_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            # 시트가 없으면 자동 생성 (26개 컬럼으로 확장)
            worksheet = spreadsheet.add_worksheet(title=STORES_SHEET, rows=1000, cols=30)
            stores_header = [
                'store_id', 'password', 'name', 'owner_name', 'phone', 'info', 'menu_text', 
                'printer_ip', 'img_files', 'unused_1', 'unused_2', 'unused_3', 
                'unused_4', 'unused_5', 'category', 'table_count', 'seats_per_table',
                'logen_id', 'logen_password', 'logen_sender_name', 'logen_sender_address', 
                'points', 'solapi_key', 'solapi_secret', 'printer_type', 'notification_mode',
                'membership'
            ]
            worksheet.update('A1:AA1', [stores_header])
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
                    'owner_name': record.get('owner_name', ''),
                    'phone': record.get('phone', ''),
                    'info': record.get('info', ''),
                    'menu_text': record.get('menu_text', ''),
                    'printer_ip': record.get('printer_ip', ''),
                    'img_files': record.get('img_files', ''),
                    'category': str(record.get('category', 'restaurant')),
                    'table_count': record.get('table_count', 0),
                    'seats_per_table': record.get('seats_per_table', 0),
                    'logen_id': record.get('logen_id', ''),
                    'logen_password': record.get('logen_password', ''),
                    'logen_sender_name': record.get('logen_sender_name', ''),
                    'logen_sender_address': record.get('logen_sender_address', ''),
                    'points': int(record.get('points', 0) or 0),
                    'solapi_key': record.get('solapi_key', ''),
                    'solapi_secret': record.get('solapi_secret', ''),
                    'printer_type': record.get('printer_type', ''),
                    'notification_mode': record.get('notification_mode', ''),
                    'membership': record.get('membership', '일반')
                }
        return stores
    except Exception as e:
        st.error(f"가게 정보 조회 실패: {e}")
        st.info("사이드바의 '시트 초기화' 버튼을 눌러 시트를 초기화해주세요.")
        return {}


@st.cache_data(ttl=30)
def get_store(store_id):
    """
    특정 가게 정보 조회 (대규모 데이터 최적화 버전)
    전체 시트를 읽지 않고 특정 아이디만 검색하여 성능 향상
    """
    try:
        spreadsheet = _get_spreadsheet_for_read()
        if spreadsheet is None: return None
        
        worksheet = spreadsheet.worksheet(STORES_SHEET)
        # 아이디가 있는 셀 찾기 (A열 고정 검색으로 속도 최적화)
        try:
            cell = worksheet.find(store_id, in_column=1)
            if not cell: return None
            
            # 해당 행의 모든 데이터 가져오기
            row_values = worksheet.row_values(cell.row)
            # 헤더와 매핑 (Z열까지 26개 컬럼)
            header = [
                'store_id', 'password', 'name', 'owner_name', 'phone', 'info', 'menu_text', 
                'printer_ip', 'img_files', 'unused_1', 'unused_2', 'unused_3', 
                'unused_4', 'unused_5', 'category', 'table_count', 'seats_per_table',
                'logen_id', 'logen_password', 'logen_sender_name', 'logen_sender_address', 
                'points', 'solapi_key', 'solapi_secret', 'printer_type', 'notification_mode',
                'membership'
            ]
            
            store_info = {}
            for i, h in enumerate(header):
                if i < len(row_values):
                    val = row_values[i]
                    if h == 'points':
                        store_info[h] = int(val or 0)
                    else:
                        store_info[h] = val
                else:
                    store_info[h] = '' if h != 'points' else 0
            
            return store_info
        except gspread.exceptions.CellNotFound:
            return None
    except Exception as e:
        st.error(f"가게 조회 실패: {e}")
        return None

@st.cache_data(ttl=60) # 1분간 결과 캐싱 (대규모 접속 대비)
def get_all_stores_cached():
    """모든 가게 정보 조회 (캐싱 적용)"""
    return get_all_stores()


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
            store_data.get('owner_name', ''), # 대표자명 추가
            store_data.get('phone', ''),
            store_data.get('info', ''),
            store_data.get('menu_text', ''),
            store_data.get('printer_ip', ''),
            store_data.get('img_files', ''),
            '정상',    # status (고정)
            '',        # billing_key (미사용)
            '',        # expiry_date (미사용)
            '정상',    # payment_status (고정)
            '',        # next_payment_date (미사용)
            store_data.get('category', 'restaurant'),  # 업종 카테고리
            store_data.get('table_count', 0),  # 테이블 수
            store_data.get('seats_per_table', 0),  # 테이블당 최대 착석 인원
            store_data.get('logen_id', ''),  # 로젠택배 아이디
            store_data.get('logen_password', ''),  # 로젠택배 비밀번호
            store_data.get('logen_sender_name', ''),  # 로젠택배 발송인명
            store_data.get('logen_sender_address', ''),  # 로젠택배 발송인 주소
            store_data.get('points', 0),  # 포인트 잔액
            store_data.get('solapi_key', ''), # 추가
            store_data.get('solapi_secret', ''), # 추가
            store_data.get('printer_type', ''), # 추가
            store_data.get('notification_mode', ''), # 추가
            store_data.get('membership', '일반') # 추가 (기본값 일반)
        ]
        
        if row_index:
            # 기존 데이터 수정
            worksheet.update(f'A{row_index}:AA{row_index}', [row_data])
        else:
            # 신규 데이터 추가
            worksheet.append_row(row_data)

        _clear_data_cache()
        return True
    except Exception as e:
        st.error(f"가게 정보 저장 실패: {e}")
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
                _clear_data_cache()
                return True
        
        return False
    except Exception as e:
        st.error(f"가게 삭제 실패: {e}")
        return False


def update_store_points(store_id, points_to_add):
    """
    가맹점 포인트 충전/차감 (최적화 버전)
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None: return False
        
        worksheet = spreadsheet.worksheet(STORES_SHEET)
        try:
            cell = worksheet.find(store_id, in_column=1)
            if not cell: return False
            
            # 현재 포인트 값 가져오기 (V열 = 22번째)
            current_points = int(worksheet.cell(cell.row, 22).value or 0)
            new_points = max(0, current_points + points_to_add)
            
            # 업데이트
            worksheet.update_cell(cell.row, 22, new_points)
            _clear_data_cache()
            return True
        except gspread.exceptions.CellNotFound:
            return False
    except Exception as e:
        st.error(f"포인트 업데이트 실패: {e}")
        return False


def find_store_id(owner_name, phone):
    """대표자 성함과 휴대폰 번호로 아이디 찾기"""
    try:
        stores = get_all_stores()
        # 전화번호에서 하이픈 제거 후 비교
        target_phone = phone.replace('-', '').strip()
        
        for sid, sdata in stores.items():
            store_phone = sdata.get('phone', '').replace('-', '').strip()
            if sdata.get('owner_name') == owner_name and store_phone == target_phone:
                return sid
        return None
    except Exception as e:
        st.error(f"아이디 찾기 실패: {e}")
        return None


def find_store_password(store_id, phone):
    """아이디와 휴대폰 번호로 비밀번호 찾기 (데모용)"""
    try:
        store = get_store(store_id)
        if not store:
            return None
            
        # 전화번호 비교
        target_phone = phone.replace('-', '').strip()
        store_phone = store.get('phone', '').replace('-', '').strip()
        
        if store_phone == target_phone:
            return store.get('password')
        return None
    except Exception as e:
        st.error(f"비밀번호 찾기 실패: {e}")
        return None


def verify_store_login(store_id, password):
    """
    가맹점 로그인 검증 (대규모 처리 최적화)
    """
    # get_all_stores 대신 핀포인트 get_store 사용
    store = get_store(store_id)
    if not store:
        return False, "존재하지 않는 아이디입니다. 신규 가입하여 1,000포인트 혜택을 받으세요!", None
    
    stored_password = str(store.get('password', ''))
    
    # 비밀번호 검증 (bcrypt 우선 처리)
    if is_bcrypt_hash(stored_password):
        if verify_password(password, stored_password):
            return True, "성공", store
    elif stored_password == password:
        return True, "성공", store
        
    return False, "비밀번호가 일치하지 않습니다.", None


# ==========================================
# 💳 정기 결제 관리 함수
# ==========================================

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
        _clear_data_cache()
        return {
            'order_id': order_id,
            'order_time': order_time,
            **order_data
        }
    except Exception as e:
        st.error(f"주문 저장 실패: {e}")
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
            order_data.get('store_id', 'delivery'), # 제공된 store_id 사용
            order_data.get('store_name', '택배 접수'), # 제공된 store_name 사용
            delivery_content,
            order_data.get('receiver_address', ''),
            order_data.get('sender_phone', ''),
            '',  # 가격
            order_data.get('memo', ''),
            '접수대기'  # 처리상태
        ]
        
        worksheet.append_row(row_data)
        _clear_data_cache()
        return {
            'order_id': order_id,
            'order_time': order_time,
            **order_data
        }
    except Exception as e:
        st.error(f"택배 주문 저장 실패: {e}")
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
예약번호: {order_id}
보내는 분: {sender.get('name', '')} ({sender.get('phone', '')})
주소: {sender.get('address', '')} {sender.get('detail_address', '')}
받는 분: {receiver.get('name', '')} ({receiver.get('phone', '')})
주소: {receiver.get('address', '')} {receiver.get('detail_address', '')}
화물: {package.get('type', '')} / {package.get('weight', '')}kg / {package.get('size', '')}
내용물: {package.get('contents', '')}
수거일: {reservation_data.get('pickup_date', '')}
배송예정: {delivery_est.get('estimated_text', '')}
요금: {fee.get('total_fee', 0):,}원 ({fee.get('payment_type', '선불')})
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
            '접수완료'  # 처리상태
        ]
        
        worksheet.append_row(row_data)
        _clear_data_cache()
        return {
            'order_id': order_id,
            'order_time': order_time,
            'reservation_number': order_id,
            **reservation_data
        }
    except Exception as e:
        st.error(f"로젠택배 예약 저장 실패: {e}")
        return None


def save_bulk_logen_reservations(reservations_result):
    """
    대량 로젠택배 예약 저장 (Batch 처리를 통한 성능 최적화)
    
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
        
        rows_to_append = []
        
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
                rows_to_append.append(row_data)
        
        if rows_to_append:
            # append_rows를 사용하여 한 번의 API 호출로 대량 데이터 저장 (속도 향상)
            worksheet.append_rows(rows_to_append)
            _clear_data_cache()
        
        return {
            'batch_id': batch_id,
            'saved_count': len(rows_to_append),
            'batch_time': batch_time
        }
    except Exception as e:
        st.error(f"본사 서버(DB) 전송 실패: {e}")
        return None


@st.cache_data(ttl=30)
def get_logen_reservations(limit=50):
    """로젠택배 예약 목록 조회"""
    try:
        spreadsheet = _get_spreadsheet_for_read()
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
        st.error(f"예약 조회 실패: {e}")
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
        _clear_data_cache()
        return {
            'order_id': order_id,
            'order_time': order_time,
            **reservation_data
        }
    except Exception as e:
        st.error(f"예약 저장 실패: {e}")
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


@st.cache_data(ttl=30)
def get_orders_by_store(store_id):
    """특정 가게의 주문 내역 조회"""
    try:
        spreadsheet = _get_spreadsheet_for_read()
        if spreadsheet is None:
            return []
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        records = worksheet.get_all_records()
        
        orders = [r for r in records if r.get('store_id') == store_id]
        return orders
    except Exception as e:
        st.error(f"주문 조회 실패: {e}")
        return []


@st.cache_data(ttl=30)
def get_all_orders():
    """모든 주문 내역 조회"""
    try:
        spreadsheet = _get_spreadsheet_for_read()
        if spreadsheet is None:
            return []
        
        worksheet = spreadsheet.worksheet(ORDERS_SHEET)
        records = worksheet.get_all_records()
        return records
    except Exception as e:
        st.error(f"주문 조회 실패: {e}")
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
                _clear_data_cache()
                return True
        
        return False
    except Exception as e:
        st.error(f"주문 상태 업데이트 실패: {e}")
        return False


# ==========================================
# ⚙️ 설정 관리 함수
# ==========================================

@st.cache_data(ttl=30)
def get_settings(store_id):
    """가게별 설정 조회"""
    try:
        spreadsheet = _get_spreadsheet_for_read()
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

        _clear_data_cache()
        return True
    except Exception as e:
        st.error(f"설정 저장 실패: {e}")
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
        st.error(f"마스터 비밀번호 저장 실패: {e}")
        return False


def verify_master_password(password: str) -> bool:
    """마스터 비밀번호 검증 (사용자 지정 마스터 계정 반영)"""
    stored_hash = get_master_password()
    
    # 1단계: 저장된 시트의 해시값과 비교
    if stored_hash and is_bcrypt_hash(stored_hash):
        if verify_password(password, stored_hash):
            return True
            
    # 2단계: secrets.toml에 설정된 마스터 비밀번호와 비교
    try:
        master_pw = st.secrets.get("admin", {}).get("password", "Qqss12!!0")
        if password == master_pw:
            return True
    except:
        pass
        
    return False


def save_performance(perf_data):
    """동네비서 실적(성과) 및 수수료 저장"""
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None: return False
        
        ws = spreadsheet.worksheet(PERFORMANCE_SHEET)
        
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            perf_data.get('type', ''),
            perf_data.get('store_name', ''),
            perf_data.get('customer_name', ''),
            perf_data.get('amount', 0),
            perf_data.get('commission', 0), # 수수료 추가
            perf_data.get('status', '완료'),
            perf_data.get('details', '')
        ]
        
        ws.append_row(row)
        _clear_data_cache()
        return True
    except Exception as e:
        print(f"실적 저장 실패: {e}")
        return False


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
            stores_ws = spreadsheet.add_worksheet(title=STORES_SHEET, rows=1000, cols=30)
        
        stores_header = [
            'store_id',        # A: 가게 ID
            'password',        # B: 비밀번호
            'name',            # C: 가게명
            'owner_name',      # D: 대표자명 (추가)
            'phone',           # E: 연락처
            'info',            # F: 영업정보
            'menu_text',       # G: 메뉴
            'printer_ip',      # H: 프린터 IP
            'img_files',       # I: 이미지 파일
            'unused_1',        # J: (이전 가맹비납부여부)
            'unused_2',        # K: (이전 빌링키)
            'unused_3',        # L: (이전 만료일)
            'unused_4',        # M: (이전 결제상태)
            'unused_5',        # N: (이전 다음결제일)
            'category',        # O: 업종 카테고리
            'table_count',     # P: 테이블 수
            'seats_per_table', # Q: 테이블당 최대 착석 인원
            'logen_id',        # R: 로젠택배 아이디
            'logen_password',  # S: 로젠택배 비밀번호
            'logen_sender_name',    # T: 로젠택배 발송인명
            'logen_sender_address', # U: 로젠택배 발송인 주소
            'points',          # V: 포인트 잔액
            'solapi_key',      # W: 솔라피 API 키
            'solapi_secret',   # X: 솔라피 시크릿
            'printer_type',    # Y: 프린터 타입
            'notification_mode',# Z: 알림 모드
            'membership'       # AA: 멤버십 등급 (일반/프리미엄)
        ]
        stores_ws.update('A1:AA1', [stores_header])
        
        # orders 시트 헤더
        try:
            orders_ws = spreadsheet.worksheet(ORDERS_SHEET)
        except:
            orders_ws = spreadsheet.add_worksheet(title=ORDERS_SHEET, rows=10000, cols=15)
        
        orders_header = ['order_id', 'order_time', 'store_id', 'store_name', 'order_content', 
                        'address', 'customer_phone', 'total_price', 'request', 'status']
        orders_ws.update('A1:J1', [orders_header])
        
        # settings 시트 헤더
        try:
            settings_ws = spreadsheet.worksheet(SETTINGS_SHEET)
        except:
            settings_ws = spreadsheet.add_worksheet(title=SETTINGS_SHEET, rows=100, cols=10)
        
        settings_header = ['store_id', 'printer_ip', 'printer_port', 'auto_print']
        settings_ws.update('A1:D1', [settings_header])
        
        # customers 시트 헤더 (고객 정보)
        try:
            customers_ws = spreadsheet.worksheet(CUSTOMERS_SHEET)
        except:
            customers_ws = spreadsheet.add_worksheet(title=CUSTOMERS_SHEET, rows=10000, cols=15)
        
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
            'updated_at',       # L: 수정일
            'points'            # M: 포인트 (추가)
        ]
        customers_ws.update('A1:M1', [customers_header])
        
        # inquiries 시트 헤더 (가맹 문의)
        try:
            inquiries_ws = spreadsheet.worksheet(INQUIRIES_SHEET)
        except:
            inquiries_ws = spreadsheet.add_worksheet(title=INQUIRIES_SHEET, rows=1000, cols=15)
        
        inquiries_header = [
            'created_at',       # A: 신청일시
            'name',             # B: 사장님 성함
            'phone',            # C: 연락처
            'kakao_id',         # D: 카톡 아이디
            'business_type',    # E: 업종
            'region',           # F: 희망 지역
            'memo',             # G: 문의내용
            'status',           # H: 처리상태 (대기/상담중/완료)
            'notes',            # I: 본사 메모
            'store_id',         # J: 희망 아이디
            'password',         # K: 임시 비밀번호
            'notification_type',# L: 알림 방식 선택
            'detail_data'       # M: 상세 설정 데이터 (JSON)
        ]
        inquiries_ws.update('A1:M1', [inquiries_header])
        
        # performance 시트 헤더 (동네비서 실적)
        try:
            perf_ws = spreadsheet.worksheet(PERFORMANCE_SHEET)
        except:
            perf_ws = spreadsheet.add_worksheet(title=PERFORMANCE_SHEET, rows=10000, cols=10)
        
        perf_header = [
            'timestamp',        # A: 발생 일시
            'type',             # B: 유형 (택배/예약/기타)
            'store_name',       # C: 가맹점명
            'customer_name',    # D: 고객명
            'amount',           # E: 매출 금액
            'commission',       # F: 수수료 수익 (추가)
            'status',           # G: 상태
            'details'           # H: 상세 내용
        ]
        perf_ws.update('A1:H1', [perf_header])
        
        _clear_data_cache()
        return True
    except Exception as e:
        st.error(f"시트 초기화 실패: {e}")
        return False


# ==========================================
# 🤝 가맹 가입 문의 관리
# ==========================================

def save_inquiry(inquiry_data):
    """
    가맹 가입 문의 정보 저장
    
    Args:
        inquiry_data: {
            'name': '홍길동',
            'phone': '010-1234-5678',
            'business_type': 'restaurant',
            'region': '서울 강남구',
            'memo': '가맹비 문의드립니다.',
            'store_id': 'hong123',
            'password': 'password123'
        }
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False
            
        ws = spreadsheet.worksheet(INQUIRIES_SHEET)
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 비밀번호 해싱 처리 (보안)
        hashed_pw = hash_password(inquiry_data.get('password', ''))
        
        row = [
            now,
            inquiry_data.get('name', ''),
            inquiry_data.get('phone', ''),
            inquiry_data.get('kakao_id', ''),
            inquiry_data.get('business_type', ''),
            inquiry_data.get('region', ''),
            inquiry_data.get('memo', ''),
            '대기',  # status
            '',      # notes
            inquiry_data.get('store_id', ''),
            hashed_pw,
            inquiry_data.get('notification_type', '알림톡'),
            inquiry_data.get('detail_data', '{}')
        ]
        
        ws.append_row(row)
        _clear_data_cache()
        return True
    except Exception as e:
        print(f"가맹 문의 저장 실패: {e}")
        return False


def verify_inquiry_login(store_id, password):
    """
    가맹 신청자의 임시 로그인 검증 (최적화 버전)
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None:
            return False, "데이터베이스 연결 실패", None
            
        ws = spreadsheet.worksheet(INQUIRIES_SHEET)
        
        # 아이디가 있는 셀 찾기 (J열 = 10번째)
        try:
            cell = ws.find(store_id, in_column=10)
            if not cell:
                return False, "등록되지 않은 아이디입니다.", None
            
            # 해당 행 데이터 가져오기
            row_values = ws.row_values(cell.row)
            header = [
                'created_at', 'name', 'phone', 'kakao_id', 'business_type', 'region',
                'memo', 'status', 'notes', 'store_id', 'password',
                'notification_type', 'detail_data'
            ]
            
            row = {h: row_values[i] if i < len(row_values) else '' for i, h in enumerate(header)}
            
            hashed_pw = row.get('password')
            if verify_password(password, hashed_pw):
                return True, "성공", row
            else:
                return False, "비밀번호가 일치하지 않습니다.", None
                
        except gspread.exceptions.CellNotFound:
            return False, "등록되지 않은 아이디입니다.", None
            
    except Exception as e:
        return False, f"로그인 중 오류 발생: {e}", None


def verify_master_login(master_id, password):
    """
    마스터 계정 로그인 검증
    """
    master_id = (master_id or "").strip()
    password = (password or "").strip()
    # 🛡️ 슈퍼관리자 임시 계정 정의
    TEMP_ADMIN_ID = "admin777"
    TEMP_ADMIN_PW = "pass777"

    # 1. 임시 슈퍼관리자 먼저 체크 (secrets.toml 의존성 없음)
    if master_id == TEMP_ADMIN_ID:
        if password == TEMP_ADMIN_PW:
            return True, "성공", {
                'store_id': master_id,
                'name': '동네비서 본사 (슈퍼관리자)',
                'owner_name': '관리자',
                'phone': "010-3069-5810",
                'points': 999999999,
                'solapi_key': st.secrets.get("SOLAPI_API_KEY", ""),
                'solapi_secret': st.secrets.get("SOLAPI_API_SECRET", ""),
                'membership': '프리미엄',
                'status': '정상'
            }
        else:
            return False, "비밀번호가 일치하지 않습니다.", None

    # 2. 기존 마스터 계정 체크 (secrets.toml 필요)
    if master_id == "5415tv":
        try:
            master_pw = st.secrets.get("admin", {}).get("password", "Qqss12!!0")
            if password == master_pw:
                return True, "성공", {
                    'store_id': master_id,
                    'name': '동네비서 본사 (마스터)',
                    'owner_name': '관리자',
                    'phone': st.secrets.get("SENDER_PHONE", "010-3069-5810"),
                    'points': 999999999,
                    'solapi_key': st.secrets.get("SOLAPI_API_KEY", ""),
                    'solapi_secret': st.secrets.get("SOLAPI_API_SECRET", ""),
                    'membership': '프리미엄',
                    'status': '정상'
                }
            else:
                return False, "비밀번호가 일치하지 않습니다.", None
        except:
            return False, "마스터 비밀번호 설정 오류", None

    return False, "마스터 아이디가 아닙니다.", None


# ==========================================
# 👤 고객 정보 관리 (Customer Memory)
# ==========================================

@st.cache_data(ttl=30)
def get_customer(customer_id, store_id=None):
    """
    고객 정보 조회 (최적화 버전)
    """
    try:
        spreadsheet = _get_spreadsheet_for_read()
        if spreadsheet is None: return None
        
        worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        try:
            # 고객 ID(전화번호)가 있는 셀 찾기 (A열)
            cell = worksheet.find(customer_id, in_column=1)
            if not cell: return None
            
            # 해당 행의 모든 데이터 가져오기
            row_values = worksheet.row_values(cell.row)
            header = [
                'customer_id', 'store_id', 'name', 'phone', 'address',
                'preferences', 'notes', 'total_orders', 'last_visit',
                'first_visit', 'created_at', 'updated_at', 'points'
            ]
            
            customer = {}
            for i, h in enumerate(header):
                if i < len(row_values):
                    val = row_values[i]
                    if h == 'total_orders' or h == 'points':
                        try:
                            customer[h] = int(val or 0)
                        except:
                            customer[h] = 0
                    else:
                        customer[h] = val
                else:
                    customer[h] = '' if h not in ['total_orders', 'points'] else 0
            
            # store_id 필터링 (선택 사항)
            if store_id and customer.get('store_id') != store_id:
                return None
                
            return customer
        except gspread.exceptions.CellNotFound:
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
    고객 정보 저장 (최적화 버전)
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None: return False
        
        worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        
        customer_id = customer_data.get('customer_id', '')
        if not customer_id:
            customer_id = customer_data.get('phone', '').replace('-', '').replace(' ', '')
        
        store_id = customer_data.get('store_id', '')
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 기존 데이터 확인 (find 사용)
        row_index = None
        existing_data = None
        
        try:
            cell = worksheet.find(customer_id, in_column=1)
            if cell:
                row_index = cell.row
                # 기존 데이터 읽기
                row_values = worksheet.row_values(row_index)
                header = [
                    'customer_id', 'store_id', 'name', 'phone', 'address',
                    'preferences', 'notes', 'total_orders', 'last_visit',
                    'first_visit', 'created_at', 'updated_at', 'points'
                ]
                existing_data = {h: row_values[i] if i < len(row_values) else '' for i, h in enumerate(header)}
        except gspread.exceptions.CellNotFound:
            pass
        
        if existing_data:
            # 기존 데이터 수정
            row_data = [
                customer_id,
                store_id or existing_data.get('store_id', ''),
                customer_data.get('name') or existing_data.get('name', ''),
                customer_data.get('phone') or existing_data.get('phone', ''),
                customer_data.get('address') or existing_data.get('address', ''),
                customer_data.get('preferences') or existing_data.get('preferences', ''),
                customer_data.get('notes') or existing_data.get('notes', ''),
                existing_data.get('total_orders', 0),
                existing_data.get('last_visit', ''),
                existing_data.get('first_visit', ''),
                existing_data.get('created_at', ''),
                now,  # updated_at
                existing_data.get('points', 0)  # points
            ]
            worksheet.update(f'A{row_index}:M{row_index}', [row_data])
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
                now,    # updated_at
                customer_data.get('points', 0)  # points
            ]
            worksheet.append_row(row_data)

        _clear_data_cache()
        return True
    except Exception as e:
        return False


def update_customer_field(customer_id, field_name, field_value, store_id=None):
    """
    고객의 특정 필드만 업데이트 (최적화 버전)
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None: return False
        
        worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        try:
            cell = worksheet.find(customer_id, in_column=1)
            if not cell: return False
            
            row_index = cell.row
            
            # 필드 인덱스 매핑 (A=1, B=2, ...)
            field_map = {
                'name': 3, 'phone': 4, 'address': 5, 'preferences': 6,
                'notes': 7, 'total_orders': 8, 'last_visit': 9
            }
            
            col_index = field_map.get(field_name)
            if not col_index: return False
            
            # 업데이트
            worksheet.update_cell(row_index, col_index, field_value)
            # updated_at (L열=12) 업데이트
            worksheet.update_cell(row_index, 12, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            _clear_data_cache()
            return True
        except gspread.exceptions.CellNotFound:
            return False
    except Exception as e:
        return False


def increment_customer_order(customer_id, store_id=None):
    """
    고객 주문 횟수 증가 및 마지막 방문일 업데이트 (최적화 버전)
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None: return 0
        
        worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        try:
            cell = worksheet.find(customer_id, in_column=1)
            if not cell: return 0
            
            row_index = cell.row
            
            # 현재 주문 횟수 가져오기 (H열=8)
            current_orders = int(worksheet.cell(row_index, 8).value or 0)
            new_orders = current_orders + 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 업데이트 (H: total_orders, I: last_visit, L: updated_at)
            worksheet.update_cell(row_index, 8, new_orders)
            worksheet.update_cell(row_index, 9, now)
            worksheet.update_cell(row_index, 12, now)

            _clear_data_cache()
            return new_orders
        except gspread.exceptions.CellNotFound:
            return 0
    except Exception as e:
        return 0


def update_customer_points(customer_id, points_to_add, store_id=None):
    """
    고객 포인트 적립/차감 (최적화 버전)
    """
    try:
        spreadsheet = get_spreadsheet()
        if spreadsheet is None: return 0
        
        worksheet = spreadsheet.worksheet(CUSTOMERS_SHEET)
        try:
            cell = worksheet.find(customer_id, in_column=1)
            if not cell: return 0
            
            row_index = cell.row
            
            # 현재 포인트 가져오기 (M열=13)
            current_points = 0
            try:
                val = worksheet.cell(row_index, 13).value
                current_points = int(val or 0)
            except:
                current_points = 0
                
            new_points = max(0, current_points + points_to_add)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 업데이트 (M: points, L: updated_at)
            worksheet.update_cell(row_index, 13, new_points)
            worksheet.update_cell(row_index, 12, now)

            _clear_data_cache()
            return new_points
        except gspread.exceptions.CellNotFound:
            return 0
    except Exception as e:
        return 0


@st.cache_data(ttl=30)
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
        spreadsheet = _get_spreadsheet_for_read()
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


@st.cache_data(ttl=30)
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

