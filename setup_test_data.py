import config
secrets = config.load_secrets()
creds = Credentials.from_service_account_info(
    dict(secrets['gcp_service_account']), 
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(secrets['spreadsheet_url'])
stores_ws = spreadsheet.worksheet('stores')

# 빈 데이터 행 삭제 (2행)
print('[INFO] Deleting empty row...')
stores_ws.delete_rows(2)

# 테스트 가게 데이터 추가
print('[INFO] Adding test store...')
test_store = [
    'teststore',       # store_id
    '1234',            # password
    'Test Store',      # name (테스트 가게)
    '01012345678',     # phone
    'Open 10:00-22:00',# info
    'Menu Item 1 - 10000\nMenu Item 2 - 15000',  # menu_text
    '',                # printer_ip
    '',                # img_files
    'paid',            # status (납부)
    '',                # billing_key
    '',                # expiry_date
    'active',          # payment_status (미등록)
    ''                 # next_payment_date
]

stores_ws.append_row(test_store)
print('[OK] Test store added!')

# 확인
print('\n=== CURRENT DATA ===')
all_values = stores_ws.get_all_values()
for i, row in enumerate(all_values):
    print(f'Row {i}: {row[:5]}...')  # 처음 5개 컬럼만 표시

print('\n[DONE] Setup complete!')

