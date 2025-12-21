"""원본 데이터 확인"""
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

# 원본 데이터 확인
all_values = stores_ws.get_all_values()

print('=== RAW DATA ===')
for i, row in enumerate(all_values):
    print(f'Row {i}: {row}')

