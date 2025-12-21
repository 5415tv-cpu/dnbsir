"""
🔧 구글 시트 초기화 스크립트
- stores, orders, settings, customers 시트의 헤더를 생성/업데이트합니다.
- 기존 데이터는 유지되고 헤더만 업데이트됩니다.

실행 방법:
    streamlit run init_sheets.py
    또는
    python init_sheets.py (Streamlit 없이 실행 시)
"""

import sys

# Streamlit 환경 체크
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("⚠️ Streamlit이 설치되지 않았습니다. 기본 모드로 실행합니다.")

if STREAMLIT_AVAILABLE:
    st.set_page_config(page_title="시트 초기화", page_icon="🔧")
    st.title("🔧 구글 시트 초기화")
    st.markdown("---")

def print_msg(msg, msg_type="info"):
    """메시지 출력 (Streamlit/콘솔 양쪽 지원)"""
    if STREAMLIT_AVAILABLE:
        if msg_type == "success":
            st.success(msg)
        elif msg_type == "error":
            st.error(msg)
        elif msg_type == "warning":
            st.warning(msg)
        else:
            st.info(msg)
    else:
        print(msg)

def show_sheet_structure():
    """시트 구조 표시"""
    
    structure = """
## 📋 시트 구조

### 1️⃣ stores (가맹점 정보)
| 컬럼 | 설명 | 비고 |
|------|------|------|
| A: store_id | 가게 ID (로그인용) | 필수 |
| B: password | 비밀번호 | bcrypt 암호화 |
| C: name | 가게명 | |
| D: phone | 연락처 | |
| E: info | 영업정보 | |
| F: menu_text | 메뉴 텍스트 | |
| G: printer_ip | 프린터 IP | 선택 |
| H: img_files | 이미지 파일 | |
| I: status | 가맹비 납부여부 | 납부/미납 |
| J: billing_key | 정기결제 빌링키 | PG사 발급 |
| K: expiry_date | 서비스 만료일 | YYYY-MM-DD |
| L: payment_status | 결제상태 | 미등록/정상/만료/실패/무료체험 |
| M: next_payment_date | 다음결제일 | YYYY-MM-DD |
| N: category | 업종 카테고리 | restaurant/delivery/laundry/retail/service/beauty/other |
| O: table_count | 테이블 수 | 숫자 |
| P: seats_per_table | 테이블당 최대 착석 인원 | 숫자 |

### 2️⃣ orders (주문/예약 내역)
| 컬럼 | 설명 |
|------|------|
| A: order_id | 주문번호 (자동생성) |
| B: order_time | 주문시간 |
| C: store_id | 가게 ID |
| D: store_name | 가게명 |
| E: order_content | 주문내용 |
| F: address | 배달주소 |
| G: customer_phone | 고객연락처 |
| H: total_price | 결제금액 |
| I: request | 요청사항 |
| J: status | 주문상태 (접수대기/조리중/배달중/완료/취소) |

### 3️⃣ settings (설정)
| 컬럼 | 설명 |
|------|------|
| A: store_id | 가게 ID |
| B: printer_ip | 프린터 IP |
| C: printer_port | 프린터 포트 (기본: 9100) |
| D: auto_print | 자동출력 여부 (Y/N) |

### 4️⃣ customers (고객 정보 - AI 기억용)
| 컬럼 | 설명 |
|------|------|
| A: customer_id | 고객 ID (전화번호) |
| B: store_id | 가게 ID |
| C: name | 고객 이름 |
| D: phone | 전화번호 |
| E: address | 주소 |
| F: preferences | 취향/선호사항 |
| G: notes | 요청사항/메모 |
| H: total_orders | 총 주문 횟수 |
| I: last_visit | 마지막 이용일 |
| J: first_visit | 첫 이용일 |
| K: created_at | 생성일 |
| L: updated_at | 수정일 |
"""
    
    if STREAMLIT_AVAILABLE:
        st.markdown(structure)
    else:
        print(structure)

def initialize_all_sheets():
    """모든 시트 초기화"""
    
    print_msg("🔄 시트 초기화를 시작합니다...", "info")
    
    try:
        from db_manager import initialize_sheets
        
        result = initialize_sheets()
        
        if result:
            print_msg("✅ 모든 시트가 성공적으로 초기화되었습니다!", "success")
            print_msg("""
**초기화된 시트:**
- 📋 stores (가맹점 정보) - 16개 컬럼
- 📦 orders (주문 내역) - 10개 컬럼  
- ⚙️ settings (설정) - 4개 컬럼
- 👤 customers (고객 정보) - 12개 컬럼
            """, "success")
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
    
    if STREAMLIT_AVAILABLE:
        # Streamlit UI
        show_sheet_structure()
        
        st.markdown("---")
        st.markdown("### 🚀 시트 초기화 실행")
        
        st.warning("""
        ⚠️ **주의사항**
        - 기존 데이터는 유지되고 **헤더(제목줄)만 업데이트**됩니다.
        - 시트가 없으면 새로 생성됩니다.
        - 초기화 전 secrets.toml과 서비스 계정이 설정되어 있어야 합니다.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔧 시트 초기화 실행", use_container_width=True, type="primary"):
                with st.spinner("초기화 중..."):
                    success = initialize_all_sheets()
                    if success:
                        st.balloons()
        
        with col2:
            if st.button("📋 구조만 보기", use_container_width=True):
                st.info("위의 시트 구조를 확인하세요.")
        
        # 수동 초기화 코드 제공
        st.markdown("---")
        with st.expander("💻 Python 코드로 직접 초기화하기"):
            st.code("""
from db_manager import initialize_sheets

# 시트 초기화 실행
result = initialize_sheets()

if result:
    print("✅ 초기화 성공!")
else:
    print("❌ 초기화 실패")
            """, language="python")
    
    else:
        # 콘솔 모드
        print("\n" + "="*50)
        print("🔧 구글 시트 초기화 스크립트")
        print("="*50 + "\n")
        
        show_sheet_structure()
        
        print("\n" + "-"*50)
        response = input("시트를 초기화하시겠습니까? (y/n): ")
        
        if response.lower() == 'y':
            initialize_all_sheets()
        else:
            print("초기화가 취소되었습니다.")

if __name__ == "__main__":
    main()


