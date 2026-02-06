"""Google Sheets 연결 테스트"""
import gspread
from google.oauth2.service_account import Credentials
import json

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# secrets.toml에서 읽기
import config
secrets = config.load_secrets()

creds_dict = dict(secrets['gcp_service_account'])

try:
    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(credentials)
    print('[OK] Google Auth Success')
    
    spreadsheet = client.open_by_url(secrets['spreadsheet_url'])
    print('[OK] Spreadsheet Access Success')
    
    # 시트 목록 확인
    worksheets = spreadsheet.worksheets()
    print(f'[INFO] Sheets: {[ws.title for ws in worksheets]}')
    
    # stores 시트 확인
    try:
        stores_ws = spreadsheet.worksheet('stores')
        print('[OK] stores sheet exists')
        
        # 헤더 확인
        headers = stores_ws.row_values(1)
        print(f'[INFO] Headers: {headers}')
        
        # 데이터 개수
        all_data = stores_ws.get_all_values()
        print(f'[INFO] Total rows: {len(all_data)}')
        
        if len(all_data) > 1:
            print(f'[INFO] Data rows: {len(all_data) - 1}')
            try:
                records = stores_ws.get_all_records()
                print(f'[OK] Records: {len(records)}')
                if records:
                    print(f'[INFO] First record keys: {list(records[0].keys())}')
            except Exception as e:
                print(f'[ERROR] get_all_records failed: {e}')
        else:
            print('[WARN] No data (header only)')
            
    except gspread.exceptions.WorksheetNotFound:
        print('[ERROR] stores sheet NOT FOUND')
    except Exception as e:
        print(f'[ERROR] stores sheet error: {e}')
        
except Exception as e:
    print(f'[ERROR] Main error: {e}')

