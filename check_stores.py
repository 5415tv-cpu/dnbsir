"""가게 정보 직접 조회 테스트"""
import toml
import gspread
from google.oauth2.service_account import Credentials

secrets = toml.load('.streamlit/secrets.toml')
creds = Credentials.from_service_account_info(
    dict(secrets['gcp_service_account']), 
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(secrets['spreadsheet_url'])
stores_ws = spreadsheet.worksheet('stores')

records = stores_ws.get_all_records()

print('=' * 50)
print('STORES DATA')
print('=' * 50)

for r in records:
    store_id = r.get('store_id', '')
    name = r.get('name', '')
    status = r.get('status', '')
    phone = r.get('phone', '')
    payment_status = r.get('payment_status', '')
    
    print(f"ID: {store_id}")
    print(f"  Name: {name}")
    print(f"  Phone: {phone}")
    print(f"  Status: {status}")
    print(f"  Payment: {payment_status}")
    print('-' * 30)

print(f'Total: {len(records)} store(s)')

