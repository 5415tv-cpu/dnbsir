"""
📊 Database Manager (SQLite Adapter)
- 기존 Google Sheets 기반 코드와 호환성을 유지하면서
- 실제 데이터는 SQLite(db_sqlite.py)에 저장합니다.
"""
from db_backend import db
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

def get_user_by_id(user_id):
    """유저 ID(전화번호)로 정보 조회"""
    return db.get_user(user_id)

def delete_user_data(user_id):
    return db.delete_user(user_id)

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


def get_all_stores():
    return db.get_all_stores()


# ==========================================
# Wallet / Virtual Number
# ==========================================

def get_wallet_balance(store_id):
    return db.get_wallet_balance(store_id)


def update_wallet_balance(store_id, new_balance):
    return db.update_wallet_balance(store_id, new_balance)


def save_virtual_number(virtual_number, store_id, label="", status="active"):
    return db.save_virtual_number(virtual_number, store_id, label, status)


def get_store_id_by_virtual_number(virtual_number):
    return db.get_store_id_by_virtual_number(virtual_number)


def get_all_virtual_numbers():
    return db.get_all_virtual_numbers()


# ==========================================
# Courier / Rider (Normalized Entities)
# ==========================================

def save_courier(data):
    return db.save_courier(data)


def get_courier(courier_id):
    return db.get_courier(courier_id)


def get_all_couriers():
    return db.get_all_couriers()


def save_rider(data):
    return db.save_rider(data)


def get_rider(rider_id):
    return db.get_rider(rider_id)


def get_all_riders():
    return db.get_all_riders()

# ==========================================
# Wallet / Logs Interface
# ==========================================

def append_wallet_log(store_id, change_type, amount, balance_after, memo="", related_id=""):
    return db.log_wallet(store_id, change_type, amount, balance_after, memo)

def append_topup_request(store_id, amount, depositor):
    return db.request_topup(store_id, amount, depositor)


def get_wallet_logs(store_id=None, limit=200):
    return db.get_wallet_logs(store_id, limit)

def append_message_log(store_id, receiver, length, cost, status="성공", channel="biztalk"):
    # Legacy wrapper compatibility
    db.log_sms(store_id, receiver, channel, f"Length: {length}, Cost: {cost}", status, "")
    return True

def log_sms(store_id, phone, category, message, status, response=""):
    """SMS 로그 저장 Wrapper"""
    db.log_sms(store_id, phone, category, message, status, response)

def get_sms_logs(store_id=None, limit=50):
    """SMS 로그 조회 Wrapper"""
    return db.get_sms_logs(store_id, limit)

# ==========================================
# Product & Reservation Wrappers
# ==========================================

def save_product_info(store_id, data):
    data['store_id'] = store_id
    return db.save_product(data)

def get_store_products(store_id):
    return db.get_products(store_id)

def delete_store_product(product_id):
    return db.delete_product(product_id)

def save_reservation_record(store_id, data):
    data['store_id'] = store_id
    return db.save_reservation(data)

def get_store_reservations(store_id):
    return db.get_reservations(store_id)

def save_store_setting(store_id, key, value):
    return db.save_setting(store_id, key, value)

def get_store_settings(store_id):
    return db.get_all_settings(store_id)

def update_reservation_state(res_id, status):
    return db.update_reservation_status(res_id, status)

def save_unified_order(store_id, data):
    data['store_id'] = store_id
    return db.save_order(data)

def get_store_orders(store_id, days=30):
    return db.get_orders(store_id, days)

def get_platform_orders(days=30):
    return db.get_all_orders_admin(days)

def get_vip_stats(store_id, phone):
    return db.get_customer_stats(store_id, phone)

def get_store_tables(store_id):
    return db.get_store_tables(store_id)

def save_store_tables(store_id, tables_data):
    return db.save_store_tables(store_id, tables_data)

def save_store_ledger(data):
    return db.save_ledger_record(data)

def get_store_ledger(store_id, month=None):
    return db.get_ledger_records(store_id, month)

def delete_store_ledger(record_id):
    return db.delete_ledger_record(record_id)

def save_store_delivery(data):
    return db.save_delivery(data)

def get_store_deliveries(store_id):
    return db.get_store_deliveries(store_id)


# ==========================================
# Dashboard & Stats
# ==========================================

def get_today_stats(store_id):
    return db.get_today_stats(store_id)

# ==========================================
# Auto Reply Settings
# ==========================================

def update_store_auto_reply(store_id, msg, missed, end, refill_on=0, refill_amount=50000):
    return db.update_store_auto_reply(store_id, msg, missed, end, refill_on, refill_amount)

# ==========================================
# Wallet Charging
# ==========================================

def charge_wallet(store_id, amount, bonus, memo):
    return db.charge_wallet(store_id, amount, bonus, memo)

# ==========================================
# Product & Market (webhook_app.py signatures)
# ==========================================

def save_product(store_id, name, price, image_path):
    return db.save_product(store_id, name, price, image_path)

def get_all_products():
    return db.get_all_products()

def get_product_detail(product_id):
    return db.get_product_detail(product_id)

def decrease_product_inventory(product_id, quantity):
    return db.decrease_product_inventory(product_id, quantity)

# ==========================================
# Orders (webhook_app.py signatures)
# ==========================================

def save_order(store_id, product_id, product_name, price, quantity, buyer_name, buyer_phone, buyer_address):
    return db.save_order(store_id, product_id, product_name, price, quantity, buyer_name, buyer_phone, buyer_address)

def update_order_status(order_id, status):
    return db.update_order_status(order_id, status)

def update_payment_method(order_id, method):
    return db.update_order_payment_method(order_id, method)

# ==========================================
# Tax & Expenses
# ==========================================

def get_tax_report_data(store_id, start, end):
    return db.get_tax_report_data(store_id, start, end)

def get_tax_stats(store_id):
    return db.get_tax_stats(store_id)

def get_monthly_expenses(store_id, month=None):
    return db.get_monthly_expenses(store_id, month)

def save_expense(store_id, card_name, category, amount, date, approval_no=None):
    return db.save_expense(store_id, card_name, category, amount, date, approval_no)

# ==========================================
# Integrated Ledger
# ==========================================

def get_integrated_ledger(store_id):
    return db.get_integrated_ledger(store_id)

def lock_ledger(store_id, date):
    return db.lock_ledger(store_id, date)


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