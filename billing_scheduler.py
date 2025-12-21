"""
🔄 정기 결제 자동 스케줄러
- 매일 실행하여 결제일이 된 가맹점 자동 결제
- 결제 성공 시 만료일 30일 연장
- 결제 실패 시 상태 업데이트 및 알림
"""

import schedule
import time
from datetime import datetime, timedelta
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('billing_scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==========================================
# 📊 Google Sheets 연결 (Streamlit 없이)
# ==========================================

import gspread
from google.oauth2.service_account import Credentials
import toml

def get_sheets_client():
    """Google Sheets 클라이언트 생성 (스케줄러용)"""
    try:
        secrets = toml.load('.streamlit/secrets.toml')
        creds_dict = dict(secrets['gcp_service_account'])
        
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_url(secrets['spreadsheet_url'])
        return spreadsheet
    except Exception as e:
        logger.error(f"Google Sheets 연결 실패: {e}")
        return None


def get_all_stores_for_billing():
    """결제 대상 가맹점 조회"""
    try:
        spreadsheet = get_sheets_client()
        if not spreadsheet:
            return []
        
        worksheet = spreadsheet.worksheet('stores')
        records = worksheet.get_all_records()
        
        stores = []
        for idx, record in enumerate(records):
            store_id = record.get('store_id', '')
            if store_id:
                stores.append({
                    'row_index': idx + 2,  # 헤더 제외
                    'store_id': store_id,
                    'name': record.get('name', ''),
                    'phone': record.get('phone', ''),
                    'billing_key': record.get('billing_key', ''),
                    'expiry_date': str(record.get('expiry_date', '')),
                    'payment_status': str(record.get('payment_status', '')),
                    'next_payment_date': str(record.get('next_payment_date', ''))
                })
        return stores
    except Exception as e:
        logger.error(f"가맹점 조회 실패: {e}")
        return []


def update_store_billing_status(store_id, expiry_date, payment_status, next_payment_date):
    """가맹점 결제 상태 업데이트"""
    try:
        spreadsheet = get_sheets_client()
        if not spreadsheet:
            return False
        
        worksheet = spreadsheet.worksheet('stores')
        records = worksheet.get_all_records()
        
        for idx, record in enumerate(records):
            if record.get('store_id') == store_id:
                row = idx + 2
                # K, L, M 컬럼 업데이트 (expiry_date, payment_status, next_payment_date)
                worksheet.update(f'K{row}:M{row}', [[expiry_date, payment_status, next_payment_date]])
                logger.info(f"[{store_id}] 상태 업데이트 완료: {payment_status}, 만료일: {expiry_date}")
                return True
        
        return False
    except Exception as e:
        logger.error(f"상태 업데이트 실패: {e}")
        return False


# ==========================================
# 💳 토스페이먼츠 결제 (스케줄러용)
# ==========================================

import requests
import base64

def get_toss_credentials_for_scheduler():
    """토스페이먼츠 API 키 가져오기"""
    try:
        secrets = toml.load('.streamlit/secrets.toml')
        return secrets.get('TOSS_SECRET_KEY', ''), secrets.get('TOSS_CLIENT_KEY', '')
    except:
        return '', ''


def execute_billing_payment_for_scheduler(billing_key, customer_key, amount, order_id, order_name):
    """빌링키로 자동 결제 실행"""
    secret_key, _ = get_toss_credentials_for_scheduler()
    
    if not secret_key:
        return None, "API 키 없음"
    
    credentials = f"{secret_key}:"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }
    
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
                "amount": data.get("totalAmount"),
                "status": data.get("status")
            }, None
        else:
            return None, data.get("message", "결제 실패")
            
    except Exception as e:
        return None, str(e)


# ==========================================
# 🔄 자동 결제 처리 함수
# ==========================================

MONTHLY_FEE = 50000  # 월 이용료

def process_billing():
    """결제일이 된 가맹점들 자동 결제 처리"""
    logger.info("=" * 50)
    logger.info("정기 결제 처리 시작")
    logger.info("=" * 50)
    
    stores = get_all_stores_for_billing()
    today = datetime.now().strftime("%Y-%m-%d")
    
    processed = 0
    success = 0
    failed = 0
    
    for store in stores:
        store_id = store['store_id']
        billing_key = store['billing_key']
        next_payment_date = store['next_payment_date']
        payment_status = store['payment_status']
        
        # 빌링키가 없으면 스킵
        if not billing_key:
            continue
        
        # 결제일이 아직 안 됐으면 스킵
        if next_payment_date and next_payment_date > today:
            continue
        
        # 이미 실패 상태면 스킵 (수동 처리 필요)
        if payment_status == '실패':
            continue
        
        logger.info(f"[{store_id}] 결제 시도 중...")
        processed += 1
        
        # 주문 ID 생성
        order_id = f"AUTO_{store_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 결제 실행
        result, error = execute_billing_payment_for_scheduler(
            billing_key=billing_key,
            customer_key=store_id,
            amount=MONTHLY_FEE,
            order_id=order_id,
            order_name="AI스토어 월 이용료 (자동결제)"
        )
        
        if error:
            # 결제 실패
            logger.error(f"[{store_id}] 결제 실패: {error}")
            update_store_billing_status(
                store_id=store_id,
                expiry_date=store['expiry_date'],  # 만료일 유지
                payment_status='실패',
                next_payment_date=next_payment_date  # 다음 결제일 유지
            )
            failed += 1
        else:
            # 결제 성공 - 만료일 30일 연장
            new_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            new_next_payment = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            
            logger.info(f"[{store_id}] 결제 성공! 금액: {result['amount']}원, 새 만료일: {new_expiry}")
            
            update_store_billing_status(
                store_id=store_id,
                expiry_date=new_expiry,
                payment_status='정상',
                next_payment_date=new_next_payment
            )
            success += 1
    
    logger.info("-" * 50)
    logger.info(f"처리 완료: 총 {processed}건 (성공: {success}, 실패: {failed})")
    logger.info("=" * 50)
    
    return processed, success, failed


def check_expiring_stores():
    """만료 예정 가맹점 체크 (7일 이내)"""
    logger.info("만료 예정 가맹점 체크 중...")
    
    stores = get_all_stores_for_billing()
    today = datetime.now()
    
    expiring_soon = []
    
    for store in stores:
        expiry_str = store['expiry_date']
        if expiry_str:
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
                days_left = (expiry_date - today).days
                
                if 0 <= days_left <= 7:
                    expiring_soon.append({
                        'store_id': store['store_id'],
                        'name': store['name'],
                        'expiry_date': expiry_str,
                        'days_left': days_left
                    })
            except:
                pass
    
    if expiring_soon:
        logger.warning(f"만료 예정 가맹점 {len(expiring_soon)}개:")
        for s in expiring_soon:
            logger.warning(f"  - {s['name']} ({s['store_id']}): {s['days_left']}일 남음")
    else:
        logger.info("만료 예정 가맹점 없음")
    
    return expiring_soon


# ==========================================
# 📅 스케줄 설정
# ==========================================

def run_scheduler():
    """스케줄러 실행"""
    logger.info("🔄 정기 결제 스케줄러 시작")
    
    # 매일 오전 9시에 결제 처리
    schedule.every().day.at("09:00").do(process_billing)
    
    # 매일 오전 10시에 만료 예정 체크
    schedule.every().day.at("10:00").do(check_expiring_stores)
    
    logger.info("스케줄 등록 완료:")
    logger.info("  - 09:00 - 정기 결제 처리")
    logger.info("  - 10:00 - 만료 예정 체크")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1분마다 체크


# ==========================================
# 🔧 수동 실행 함수
# ==========================================

def manual_process_billing():
    """수동으로 결제 처리 실행"""
    print("수동 결제 처리 시작...")
    processed, success, failed = process_billing()
    print(f"완료: 총 {processed}건 (성공: {success}, 실패: {failed})")
    return processed, success, failed


def manual_check_expiring():
    """수동으로 만료 예정 체크"""
    print("만료 예정 체크 시작...")
    expiring = check_expiring_stores()
    print(f"만료 예정: {len(expiring)}개")
    return expiring


# ==========================================
# 메인 실행
# ==========================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "billing":
            manual_process_billing()
        elif command == "check":
            manual_check_expiring()
        elif command == "run":
            run_scheduler()
        else:
            print("사용법:")
            print("  python billing_scheduler.py billing  - 수동 결제 처리")
            print("  python billing_scheduler.py check    - 만료 예정 체크")
            print("  python billing_scheduler.py run      - 스케줄러 실행")
    else:
        print("🔄 정기 결제 스케줄러")
        print("사용법:")
        print("  python billing_scheduler.py billing  - 수동 결제 처리")
        print("  python billing_scheduler.py check    - 만료 예정 체크")
        print("  python billing_scheduler.py run      - 스케줄러 실행 (백그라운드)")

