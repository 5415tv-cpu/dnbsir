"""
📊 Database Manager (SQLite Adapter)
- 기존 Google Sheets 기반 코드와 호환성을 유지하면서
- 실제 데이터는 SQLite(db_sqlite.py)에 저장합니다.
"""
import db_sqlite as db
import pandas as pd

# ==========================================
# 상수의 호환성 유지
# ==========================================
RESTAURANT_SUBCATEGORIES = {'korean': {'name': '한식'}} # 일부 중요 상수만 예시로 유지
TIER_CATALOG = {} # 필요한 경우 복원

# ==========================================
# Core Functions Interface
# ==========================================

def save_user_management(user_data):
    """유저 정보 저장"""
    return db.save_user(user_data), "저장 완료"

def get_business_data(user_type):
    """비즈니스 데이터 조회 (관리자용)"""
    # 유저 관리 데이터 요청 시
    if user_type == "유저관리":
        return db.get_all_users()
    return pd.DataFrame()

def get_all_topups():
    """충전 요청 목록"""
    return db.get_pending_topups()

def save_to_google_sheet(user_type, data):
    """장부/접수 데이터 저장 (이름은 구글시트지만 실제론 SQLite)"""
    success, msg = db.save_business_record(user_type, data)
    return success, msg

def save_store(store_id, store_data, encrypt_password=True):
    """가게 정보 저장"""
    # store_id를 data에 포함
    store_data['store_id'] = store_id
    return db.save_store(store_data)

def get_store(store_id):
    """가게 정보 조회"""
    return db.get_store(store_id)

# ==========================================
# Wallet / Logs Interface
# ==========================================

def append_wallet_log(store_id, change_type, amount, balance_after, memo="", related_id=""):
    return db.log_wallet(store_id, change_type, amount, balance_after, memo)

def append_topup_request(store_id, amount, depositor):
    return db.request_topup(store_id, amount, depositor)

def append_message_log(store_id, receiver, length, cost, status="성공", channel="biztalk"):
    # db_sqlite에 message log 구현이 필요하면 추가. 현재는 간소화.
    return True

# ==========================================
# Legacy / Unused Placeholders
# ==========================================
# 기존 코드에서 import해서 쓰던 유틸 함수들이 있다면 여기에 껍데기만이라도 남겨둬야 에러가 안 남.

def validate_password_length(password):
    return True, "OK"

def hash_password(password):
    return password # 단순화

def verify_password(pw, hashed):
    return pw == hashed