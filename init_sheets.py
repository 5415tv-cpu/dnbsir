"""
🔧 구글 시트 초기화 스크립트 (CLI)
- stores, orders, settings, customers 시트의 헤더를 생성/업데이트합니다.

실행 방법:
    python init_sheets.py
"""

import sys

def print_msg(msg, msg_type="info"):
    """메시지 출력"""
    print(f"[{msg_type.upper()}] {msg}")

def show_sheet_structure():
    """시트 구조 표시"""
    
    structure = """
## 📋 시트 구조

### 1️⃣ stores (가맹점 정보)
... (See original docstring or code for details) ...
    """
    print(structure)

def initialize_all_sheets():
    """모든 시트 초기화"""
    
    print_msg("🔄 시트 초기화를 시작합니다...", "info")
    
    try:
        from db_manager import initialize_sheets
        
        result = initialize_sheets()
        
        if result:
            print_msg("✅ 모든 시트가 성공적으로 초기화되었습니다!", "success")
            return True
        else:
            print_msg("❌ 시트 초기화에 실패했습니다.", "error")
            return False
            
    except Exception as e:
        print_msg(f"❌ 오류 발생: {str(e)}", "error")
        print_msg("💡 secrets.toml 파일과 서비스 계정 설정을 확인해주세요.", "warning")
        return False

def main():
    """메인 함수"""
    print("\n" + "="*50)
    print("🔧 구글 시트 초기화 스크립트")
    print("="*50 + "\n")
    
    # show_sheet_structure() # Optional to suppress lengthy output
    
    print("\n" + "-"*50)
    # response = input("시트를 초기화하시겠습니까? (y/n): ") # Auto-run or ask? User likely runs this manually.
    # For automation safety, let's keep it manual or assume if run, it's intended.
    # The original script asked for input.
    response = input("All sheets will be initialized (headers updated). Continue? (y/n): ")
    
    if response.lower() == 'y':
        initialize_all_sheets()
    else:
        print("초기화가 취소되었습니다.")

if __name__ == "__main__":
    main()


