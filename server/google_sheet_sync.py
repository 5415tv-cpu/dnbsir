import gspread
from google.oauth2.service_account import Credentials
import os

# 1. 구글 시트 비서 연결 설정
def sync_to_google_sheet(data_list):
    """
    새로운 회원 정보를 구글 시트에 추가합니다.
    data_list: [store_id, password, name, phone, joined_at, etc...]
    """
    try:
        # 인증 정보 로드 (service_account.json 사용)
        # 1. 현재 디렉토리 확인
        creds_file = "service_account.json"
        
        # 2. 없으면 상위 디렉토리 확인 (서버 폴더 내에서 실행 시)
        if not os.path.exists(creds_file):
            creds_file = "../service_account.json"
            
        if not os.path.exists(creds_file):
            print(f"⚠️ [Sync Warning] '{creds_file}' 파일을 찾을 수 없습니다. 동기화를 건너뜁니다.")
            return False

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 사장님의 구글 시트 열기 (내 손안의 동네비서 장부)
        # 주의: 서비스 계정이 이 시트에 접근 권한이 있어야 함 (공유 설정 필요)
        sheet_name = "내 손안의 동네비서_장부"
        try:
            sheet = client.open(sheet_name).sheet1
        except gspread.SpreadsheetNotFound:
            print(f"⚠️ [Sync Warning] 구글 시트 '{sheet_name}'를 찾을 수 없습니다. 공유 설정을 확인해주세요.")
            return False
        
        # 데이터 추가 (SQL 내용을 시트 마지막 줄에 붙여넣기)
        sheet.append_row(data_list)
        print(f"✅ [Sync Success] 구글 시트 동기화 완료: {data_list[0]}")
        return True
        
    except Exception as e:
        # 동기화 실패가 메인 로직(로그인/가입)을 방해하면 안 됨 -> 에러 로그만 남김
        print(f"🚨 [Sync Error] 동기화 중 에러 발생: {e}")
        return False
