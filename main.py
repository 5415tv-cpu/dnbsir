"""
🏘️ 동네비서 - 똑똑한 AI 이웃
고객 주문 페이지
"""

import streamlit as st
import google.generativeai as genai
from datetime import datetime
import os

# 커스텀 모듈 임포트
from db_manager import (
    get_all_stores, get_store, save_order, save_store,
    validate_password_length, MIN_PASSWORD_LENGTH, BUSINESS_CATEGORIES,
    RESTAURANT_SUBCATEGORIES, DELIVERY_SUBCATEGORIES, 
    LAUNDRY_SUBCATEGORIES, RETAIL_SUBCATEGORIES,
    save_delivery_order, save_table_reservation, check_table_availability
)
from sms_manager import send_order_notification, send_order_confirmation
from printer_manager import print_order_receipt, format_order_for_print
from pwa_helper import inject_pwa_tags, show_install_prompt, get_pwa_css

# ==========================================
# 🔑 API 설정
# ==========================================
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    model = None

# ==========================================
# 🎨 페이지 설정
# ==========================================
st.set_page_config(
    page_title="동네비서",
    page_icon="🏘️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS 스타일 - 모바일 앱 스타일
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* 전체 배경색 */
body {
    background-color: #f0f2f6;
}

/* 메인 콘텐츠 영역 (중앙) 스타일 */
.main .block-container {
    max-width: 480px;
    padding-top: 2rem;
    padding-right: 1rem;
    padding-left: 1rem;
    padding-bottom: 2rem;
    background-color: white;
    border-radius: 10px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

/* 스트림릿 기본 헤더/푸터 숨기기 */
#MainMenu { visibility: hidden; }
header { visibility: hidden; }
footer { visibility: hidden; }

/* 전체 폰트 */
html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif !important;
    font-size: 14px !important;
    color: #333 !important;
}

/* 카드 스타일 */
.app-card {
    background-color: #ffffff;
    border: 2px solid #333333;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
    cursor: pointer;
    transition: all 0.2s ease;
}
.app-card:hover {
    transform: translateY(-5px);
    border-color: #007bff;
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
}
.app-card h3 {
    color: #333333;
    font-size: 1.1em;
    margin-bottom: 5px;
}
.app-card p {
    color: #666666;
    font-size: 0.9em;
}

/* 상단/하단 고정바 스타일 */
.fixed-header, .fixed-footer {
    position: fixed;
    left: 0;
    width: 100%;
    background-color: #262730;
    color: white;
    padding: 12px 1rem;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    z-index: 1000;
}
.fixed-header { top: 0; }
.fixed-footer { bottom: 0; }
.fixed-header a, .fixed-footer a {
    color: white;
    text-decoration: none;
    margin: 0 10px;
}

/* 버튼 스타일 */
.stButton > button {
    width: 100% !important;
    height: 56px !important;
    min-height: 56px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    padding: 0 16px !important;
    margin: 0 !important;
    background: #ffffff !important;
    border: 1px solid #ddd !important;
    color: #333 !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.2s ease !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.stButton > button:hover {
    background: #f8f9fa !important;
    border-color: #333 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
}

.stButton > button:active {
    background: #f0f0f0 !important;
    transform: translateY(0) !important;
}

/* 입력 필드 스타일 */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div,
.stNumberInput > div > div > input {
    font-size: 14px !important;
    padding: 12px !important;
    min-height: 44px !important;
    border-radius: 8px !important;
    background: #fff !important;
    border: 1px solid #ddd !important;
    color: #333 !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #333 !important;
    box-shadow: 0 0 0 2px rgba(51, 51, 51, 0.1) !important;
}

.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stNumberInput label {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #555 !important;
}

/* 탭 스타일 */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    background: transparent !important;
    border-bottom: 1px solid #ddd !important;
    padding: 0 !important;
    border-radius: 0 !important;
}

.stTabs [data-baseweb="tab"] {
    min-height: 40px !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    padding: 10px 16px !important;
    border-radius: 0 !important;
    color: #999 !important;
    border-bottom: 2px solid transparent !important;
}

.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #333 !important;
    border-bottom: 2px solid #333 !important;
}

/* 익스팬더 스타일 */
.stExpander {
    background: #fff !important;
    border: 1px solid #eee !important;
    border-radius: 8px !important;
}

.stExpander > div:first-child {
    background: transparent !important;
}
    
    .stExpander summary {
        font-size: 14px !important;
        font-weight: 400 !important;
        color: #666 !important;
        padding: 12px !important;
    }
    
    .stExpander summary:hover {
        color: #333 !important;
    }
    
    .stExpander [data-testid="stExpanderDetails"] {
        font-size: 14px !important;
        color: #666 !important;
        padding: 0 12px 12px 12px !important;
        line-height: 1.6 !important;
    }
    
    /* 마크다운 */
    .stMarkdown p, .stMarkdown li {
        font-size: 14px !important;
        line-height: 1.6 !important;
        color: #333 !important;
    }
    
    .stMarkdown h1 {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #000 !important;
    }
    
    .stMarkdown h2, .stMarkdown h3 {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: #333 !important;
    }
    
    /* Divider */
    hr {
        border: none !important;
        height: 1px !important;
        background: #eee !important;
        margin: 24px 0 !important;
    }
    
    /* Alert */
    .stAlert {
        border-radius: 0 !important;
        border: 1px solid #eee !important;
        background: #fafafa !important;
    }
    
    /* 스크롤바 숨김 */
    ::-webkit-scrollbar {
        width: 4px;
    }
    ::-webkit-scrollbar-track {
        background: #fff;
    }
    ::-webkit-scrollbar-thumb {
        background: #ddd;
    }
    
    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: #fafafa !important;
        border-right: 1px solid #eee !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #333 !important;
    }
    
    /* 라디오 버튼 */
    .stRadio > div {
        gap: 0 !important;
    }
    
    .stRadio label {
        font-size: 14px !important;
        padding: 10px 0 !important;
        border-bottom: 1px solid #eee !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🎁 홍보 배너 (가맹점 모집)
# ==========================================
PROMO_TITLE = "🚀 동네비서에 가입하세요!"
PROMO_SUBTITLE = "🎁 지금 가입하면 한 달 무료 체험 혜택 제공!"

# ==========================================
# 📱 PWA 설정 적용
# ==========================================
inject_pwa_tags()  # PWA 메타 태그 주입
st.markdown(get_pwa_css(), unsafe_allow_html=True)  # PWA 최적화 CSS

# ==========================================
# 🔗 URL 파라미터 처리 (직접 링크 접속)
# ==========================================
query_params = st.query_params

# store 파라미터가 있으면 해당 가게로 바로 이동
if "store" in query_params and not st.session_state.get("direct_store_loaded"):
    direct_store_id = query_params.get("store")
    if direct_store_id:
        # 해당 가게 정보 확인
        direct_store = get_store(direct_store_id)
        if direct_store:
            st.session_state.direct_store_id = direct_store_id
            st.session_state.direct_store_info = direct_store
            st.session_state.direct_store_loaded = True
            st.session_state.show_direct_store = True
        else:
            st.warning(f"⚠️ '{direct_store_id}' 가게를 찾을 수 없습니다.")
            st.session_state.direct_store_loaded = True

# (기존 AI 배지 및 프로모 배너는 HERO 섹션으로 대체됨)

# ==========================================
# 🎁 사장님 전용혜택 표시 함수
# ==========================================
def show_benefits_section():
    """사장님 전용혜택 섹션 표시"""
    
    # 세션 상태 초기화
    if "show_benefits" not in st.session_state:
        st.session_state.show_benefits = False
    
    # 토글 버튼
    if st.session_state.show_benefits:
        btn_text = "🎁 사장님 전용혜택 접기 ▲"
    else:
        btn_text = "🎁 사장님 전용혜택 보기 ▼"
    
    if st.button(btn_text, key="btn_toggle_benefits", use_container_width=True):
        st.session_state.show_benefits = not st.session_state.show_benefits
        st.rerun()
    
    # 혜택 내용 표시
    if st.session_state.show_benefits:
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 20px;
            color: white;
            margin: 15px 0;
        ">
            <h2 style="color: white; margin-bottom: 20px; font-size: 1.8rem;">
                🏘️ 동네비서 사장님 전용 혜택
            </h2>
            <p style="font-size: 1.1rem; opacity: 0.95;">
                동네비서와 함께하면 이런 점이 좋아요!
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 장점 리스트
        benefits = [
            ("🤖", "AI 직원 24시간 근무", "밤낮없이 주문/예약 접수! 사장님은 편히 쉬세요."),
            ("📱", "무료 앱 설치 불필요", "카카오톡, 문자로 링크만 보내면 끝! 손님이 쉽게 주문해요."),
            ("💰", "배달앱 수수료 0원", "배달의민족, 요기요 수수료 없이 직접 주문 받으세요."),
            ("📊", "실시간 주문 관리", "주문 현황을 실시간으로 확인하고 관리할 수 있어요."),
            ("🖨️", "자동 영수증 출력", "Wi-Fi 프린터 연결하면 주문이 자동으로 출력돼요."),
            ("📦", "로젠택배 연동", "택배 접수도 한 번에! 손님이 직접 택배 신청해요."),
            ("👥", "단골 고객 관리", "AI가 손님 정보를 기억하고 맞춤 인사를 해요."),
            ("📈", "매출 분석 리포트", "일별/월별 매출 현황을 한눈에 확인하세요."),
            ("🔗", "QR코드 생성", "매장에 QR코드 붙이면 손님이 바로 주문 가능!"),
            ("💬", "문자 알림 자동 발송", "주문 접수 시 사장님에게 즉시 문자 알림!")
        ]
        
        for icon, title, desc in benefits:
            st.markdown(f"""
            <div style="
                background: white;
                border-radius: 15px;
                padding: 18px 20px;
                margin-bottom: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                display: flex;
                align-items: center;
                border-left: 5px solid #667eea;
            ">
                <div style="font-size: 2.2rem; margin-right: 18px;">{icon}</div>
                <div>
                    <div style="font-weight: 700; font-size: 1.15rem; color: #333; margin-bottom: 4px;">{title}</div>
                    <div style="color: #666; font-size: 0.95rem;">{desc}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 가입 유도
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            padding: 25px;
            border-radius: 20px;
            text-align: center;
            color: white;
        ">
            <h3 style="color: white; margin-bottom: 10px;">🚀 지금 바로 시작하세요!</h3>
            <p style="font-size: 1.1rem; opacity: 0.95; margin-bottom: 15px;">
                가입비 무료, 설치비 무료!<br>
                사이드바에서 <strong>'🆕 사장님 가입'</strong>을 클릭하세요.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 📦 주문 처리 공통 함수
# ==========================================
def process_order(store, store_id, order_content, customer_phone, address, total_price, request, order_type="주문"):
    """주문/예약 공통 처리 함수"""
    from db_manager import increment_customer_order, save_customer, get_customer
    
    order_data = {
        'store_id': store_id,
        'store_name': store.get('name', ''),
        'order_content': order_content,
        'address': address,
        'customer_phone': customer_phone,
        'total_price': total_price,
        'request': request
    }
    
    with st.spinner(f"🔄 {order_type} 처리 중..."):
        saved_order = save_order(order_data)
        
        if saved_order:
            st.success(f"✅ {order_type}이 접수되었습니다!")
            
            # 👤 고객 정보 업데이트 (주문 횟수 증가, 마지막 이용일 갱신)
            if customer_phone:
                normalized_phone = customer_phone.replace('-', '').replace(' ', '')
                existing_customer = get_customer(normalized_phone, store_id)
                
                if existing_customer:
                    # 기존 고객 - 주문 횟수 증가
                    new_count = increment_customer_order(normalized_phone, store_id)
                    if new_count > 0:
                        st.caption(f"🎉 {new_count}번째 주문 감사합니다!")
                else:
                    # 신규 고객 - 자동 등록
                    save_customer({
                        'customer_id': normalized_phone,
                        'store_id': store_id,
                        'phone': customer_phone,
                        'address': address  # 주소 저장
                    })
                    # 주문 횟수 1로 설정
                    increment_customer_order(normalized_phone, store_id)
            
            store_phone = store.get('phone', '')
            if store_phone:
                sms_success, sms_msg = send_order_notification(store_phone, saved_order)
                if sms_success:
                    st.info("📱 사장님에게 알림이 전송되었습니다.")
                else:
                    st.warning(f"⚠️ 문자 발송 실패: {sms_msg}")
            
            printer_ip = store.get('printer_ip', '')
            if printer_ip:
                print_data = format_order_for_print(
                    order_id=saved_order.get('order_id'),
                    order_time=saved_order.get('order_time'),
                    store_name=store.get('name', ''),
                    order_content=order_content,
                    address=address,
                    customer_phone=customer_phone,
                    total_price=total_price,
                    request=request
                )
                print_success, print_msg = print_order_receipt(print_data, printer_ip)
                if print_success:
                    st.info(f"🖨️ {print_msg}")
            
            st.session_state.order_complete = True
            st.session_state.last_order = {
                **saved_order,
                'store_name': store.get('name', ''),
                'store_phone': store_phone
            }
            st.balloons()
            st.rerun()
        else:
            st.error(f"❌ {order_type} 저장에 실패했습니다. 다시 시도해주세요.")


# ==========================================
# 🪑 테이블 예약 폼 (가용성 확인 포함)
# ==========================================
def render_table_reservation_form(store_id, store):
    """테이블 예약 폼 - 가용성 확인 로직 포함"""
    st.markdown("### 🪑 테이블 예약")
    
    # 테이블 정보 표시
    table_count = int(store.get('table_count', 0) or 0)
    seats_per_table = int(store.get('seats_per_table', 0) or 0)
    
    if table_count > 0 and seats_per_table > 0:
        st.info(f"🪑 테이블: {table_count}개 | 👥 테이블당 최대 {seats_per_table}명")
    
    with st.form("table_reservation_form"):
        st.markdown("#### 📅 예약 정보")
        
        col1, col2 = st.columns(2)
        with col1:
            reservation_date = st.date_input("예약 날짜")
        with col2:
            reservation_time = st.time_input("예약 시간")
        
        party_size = st.number_input(
            "인원 수", 
            min_value=1, 
            max_value=50 if seats_per_table == 0 else table_count * seats_per_table,
            value=2
        )
        
        st.markdown("---")
        st.markdown("#### 👤 예약자 정보")
        
        col3, col4 = st.columns(2)
        with col3:
            customer_name = st.text_input("예약자 이름")
        with col4:
            customer_phone = st.text_input("연락처", placeholder="010-0000-0000")
        
        request = st.text_area("요청사항 (선택)", placeholder="창가 자리 부탁드립니다...")
        
        submitted = st.form_submit_button("🪑 예약 확인하기", use_container_width=True)
        
        if submitted:
            if customer_name and customer_phone:
                # 테이블 가용성 확인
                date_str = reservation_date.strftime("%Y-%m-%d")
                time_str = reservation_time.strftime("%H:%M")
                
                availability = check_table_availability(
                    store_id, date_str, time_str, party_size
                )
                
                if availability['available']:
                    # 예약 저장
                    reservation_data = {
                        'store_name': store.get('name', ''),
                        'reservation_date': date_str,
                        'reservation_time': time_str,
                        'party_size': party_size,
                        'customer_name': customer_name,
                        'customer_phone': customer_phone,
                        'request': request
                    }
                    
                    result = save_table_reservation(store_id, reservation_data)
                    
                    if result:
                        st.success(f"""
                        ✅ **예약이 완료되었습니다!**
                        
                        📋 예약번호: {result.get('order_id', 'N/A')}
                        📅 일시: {date_str} {time_str}
                        👥 인원: {party_size}명
                        🏪 매장: {store.get('name', '')}
                        
                        예약 확인 문자가 발송됩니다.
                        """)
                        st.balloons()
                    else:
                        st.error("예약 저장 중 오류가 발생했습니다.")
                else:
                    st.error(availability['message'])
            else:
                st.warning("예약자 이름과 연락처를 입력해주세요.")


# ==========================================
# 📋 일반 주문 폼
# ==========================================
def render_order_form(store_id, store):
    """일반 업종용 주문 폼"""
    st.markdown("### 📋 주문하기")
    
    with st.form("general_order_form"):
        order_content = st.text_area(
            "주문 내용",
            placeholder="원하시는 서비스나 상품을 입력해주세요...",
            height=150
        )
        
        st.markdown("---")
        st.markdown("#### 👤 고객 정보")
        
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("이름")
        with col2:
            customer_phone = st.text_input("연락처", placeholder="010-0000-0000")
        
        address = st.text_input("주소 (배달/방문 시)", placeholder="서울시 강남구...")
        request = st.text_area("요청사항 (선택)", placeholder="추가 요청사항...")
        
        submitted = st.form_submit_button("📋 주문하기", use_container_width=True)
        
        if submitted:
            if order_content and customer_phone:
                order_data = {
                    'store_id': store_id,
                    'store_name': store.get('name', ''),
                    'order_content': order_content,
                    'address': address,
                    'customer_phone': customer_phone,
                    'request': request
                }
                
                result = save_order(order_data)
                if result:
                    st.success(f"""
                    ✅ **주문이 접수되었습니다!**
                    
                    📋 주문번호: {result.get('order_id', 'N/A')}
                    🏪 매장: {store.get('name', '')}
                    
                    주문 확인 문자가 발송됩니다.
                    """)
                    st.balloons()
                else:
                    st.error("주문 저장 중 오류가 발생했습니다.")
            else:
                st.warning("주문 내용과 연락처를 입력해주세요.")


# ==========================================
# 🍽️ 식당 - 테이블 예약/배달 주문 폼
# ==========================================
def render_restaurant_form(store, store_id):
    """식당/음식점용 주문 폼"""
    st.markdown("### 🍽️ 주문/예약하기")
    
    # 테이블 정보 표시
    table_count = int(store.get('table_count', 0) or 0)
    seats_per_table = int(store.get('seats_per_table', 0) or 0)
    
    if table_count > 0 and seats_per_table > 0:
        st.info(f"🪑 테이블: {table_count}개 | 👥 테이블당 최대 {seats_per_table}명 | 📊 총 수용: {table_count * seats_per_table}명")
    
    order_type = st.radio(
        "주문 유형을 선택하세요",
        ["🛵 배달 주문", "🪑 테이블 예약"],
        horizontal=True
    )
    
    if "배달" in order_type:
        with st.form("restaurant_delivery_form"):
            order_content = st.text_area(
                "주문 내용",
                placeholder="예: 짜장면 1개, 짬뽕 1개",
                height=100
            )
            
            col1, col2 = st.columns(2)
            with col1:
                customer_phone = st.text_input("연락처", placeholder="01012345678")
                total_price = st.text_input("결제 금액", placeholder="15000")
            with col2:
                address = st.text_input("배달 주소", placeholder="서울시 강남구...")
                request = st.text_input("요청사항", placeholder="문앞에 놔주세요")
            
            if st.form_submit_button("🛵 배달 주문하기", use_container_width=True, type="primary"):
                if not order_content:
                    st.error("❌ 주문 내용을 입력해주세요!")
                elif not customer_phone:
                    st.error("❌ 연락처를 입력해주세요!")
                elif not address:
                    st.error("❌ 배달 주소를 입력해주세요!")
                else:
                    process_order(store, store_id, order_content, customer_phone, address, total_price, request, "주문")
    
    else:  # 테이블 예약
        with st.form("restaurant_reservation_form"):
            st.markdown("#### 🪑 테이블 예약 정보")
            
            # 테이블 정보가 있으면 최대 인원 제한
            max_guests = table_count * seats_per_table if (table_count > 0 and seats_per_table > 0) else 50
            
            col1, col2 = st.columns(2)
            with col1:
                reservation_date = st.date_input("예약 날짜")
                reservation_time = st.time_input("예약 시간")
                num_guests = st.number_input("인원 수", min_value=1, max_value=max_guests, value=2)
            with col2:
                customer_phone = st.text_input("연락처", placeholder="01012345678")
                customer_name = st.text_input("예약자 이름", placeholder="홍길동")
            
            request = st.text_area("요청사항", placeholder="창가 자리 부탁드립니다", height=80)
            
            if st.form_submit_button("🪑 예약하기", use_container_width=True, type="primary"):
                if not customer_phone:
                    st.error("❌ 연락처를 입력해주세요!")
                elif not customer_name:
                    st.error("❌ 예약자 이름을 입력해주세요!")
                else:
                    # 테이블 가용성 확인
                    date_str = reservation_date.strftime("%Y-%m-%d")
                    time_str = reservation_time.strftime("%H:%M")
                    
                    availability = check_table_availability(
                        store_id, date_str, time_str, num_guests
                    )
                    
                    if availability['available']:
                        # 예약 저장
                        reservation_data = {
                            'store_name': store.get('name', ''),
                            'reservation_date': date_str,
                            'reservation_time': time_str,
                            'party_size': num_guests,
                            'customer_name': customer_name,
                            'customer_phone': customer_phone,
                            'request': request
                        }
                        
                        result = save_table_reservation(store_id, reservation_data)
                        
                        if result:
                            st.success(f"""
                            ✅ **예약이 완료되었습니다!**
                            
                            📋 예약번호: {result.get('order_id', 'N/A')}
                            📅 일시: {date_str} {time_str}
                            👥 인원: {num_guests}명
                            🏪 매장: {store.get('name', '')}
                            
                            예약 확인 문자가 발송됩니다.
                            """)
                            st.balloons()
                        else:
                            st.error("예약 저장 중 오류가 발생했습니다.")
                    else:
                        st.error(f"❌ {availability['message']}")


# ==========================================
# 📦 택배 - 로젠택배 접수 폼 (엑셀 대량 업로드 지원)
# ==========================================
def render_delivery_form(store, store_id):
    """택배/물류용 접수 폼 - 로젠택배 연동"""
    import pandas as pd
    import io
    
    st.markdown("### 📦 택배 접수 - 로젠택배 연동")
    
    # 로젠택배 바로가기 링크
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="color: white; font-size: 1.2rem; font-weight: bold;">🚚 로젠택배 공식 연동</span>
                <p style="color: #ddd; margin: 0.5rem 0 0 0; font-size: 0.9rem;">실시간 운송장 발급 및 배송 추적</p>
            </div>
            <a href="https://www.ilogen.com/m/personal/tkPersonalWaybillSave.dev" target="_blank" 
               style="background: #ff6b35; color: white; padding: 0.7rem 1.5rem; border-radius: 25px; text-decoration: none; font-weight: bold;">
                로젠택배 바로가기 →
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 탭으로 단건/대량 분리
    delivery_tab1, delivery_tab2 = st.tabs(["📦 단건 접수", "📊 대량 접수 (엑셀)"])
    
    # ==========================================
    # 단건 접수 탭
    # ==========================================
    with delivery_tab1:
        with st.form("delivery_form"):
            st.markdown("#### 📤 보내는 분")
            col1, col2 = st.columns(2)
            with col1:
                sender_name = st.text_input("이름", placeholder="홍길동", key="sender_name")
                sender_phone = st.text_input("연락처", placeholder="01012345678", key="sender_phone")
            with col2:
                sender_address = st.text_input("주소", placeholder="서울시 강남구...", key="sender_address")
                sender_detail = st.text_input("상세주소", placeholder="101동 1001호", key="sender_detail")
            
            st.markdown("---")
            st.markdown("#### 📥 받는 분")
            col3, col4 = st.columns(2)
            with col3:
                receiver_name = st.text_input("이름", placeholder="김철수", key="receiver_name")
                receiver_phone = st.text_input("연락처", placeholder="01087654321", key="receiver_phone")
            with col4:
                receiver_address = st.text_input("주소", placeholder="부산시 해운대구...", key="receiver_address")
                receiver_detail = st.text_input("상세주소", placeholder="201동 2001호", key="receiver_detail")
            
            st.markdown("---")
            st.markdown("#### 📋 화물 정보")
            col5, col6 = st.columns(2)
            with col5:
                package_type = st.selectbox("포장 유형", ["📦 박스", "📄 서류", "🎁 선물", "🔧 기타"])
                package_weight = st.selectbox("무게", ["5kg 이하", "5~10kg", "10~20kg", "20kg 이상"])
            with col6:
                package_size = st.selectbox("크기", ["소형 (60cm 이하)", "중형 (80cm 이하)", "대형 (120cm 이하)", "특대형"])
                pickup_date = st.date_input("수거 희망일")
            
            package_contents = st.text_input("내용물", placeholder="의류, 도서, 전자제품 등")
            request = st.text_area("요청사항", placeholder="파손 주의 / 경비실 맡기기 / 부재시 문앞", height=60)
            
            col_submit, col_logen = st.columns(2)
            
            with col_submit:
                if st.form_submit_button("📦 접수하기", use_container_width=True, type="primary"):
                    if not sender_name or not sender_phone or not sender_address:
                        st.error("❌ 보내는 분 정보를 입력해주세요!")
                    elif not receiver_name or not receiver_phone or not receiver_address:
                        st.error("❌ 받는 분 정보를 입력해주세요!")
                    else:
                        order_content = f"""[택배 접수]
📤 보내는 분: {sender_name} ({sender_phone})
   주소: {sender_address} {sender_detail}
📥 받는 분: {receiver_name} ({receiver_phone})
   주소: {receiver_address} {receiver_detail}
📋 화물: {package_type} / {package_weight} / {package_size}
   내용물: {package_contents}
📅 수거 희망일: {pickup_date}"""
                        process_order(store, store_id, order_content, sender_phone, receiver_address, "", request, "접수")
    
    # ==========================================
    # 대량 접수 탭 (엑셀 업로드)
    # ==========================================
    with delivery_tab2:
        st.markdown("#### 📊 엑셀 파일로 대량 택배 접수")
        st.info("💡 엑셀 파일을 업로드하면 한 번에 여러 건의 택배를 접수할 수 있습니다.")
        
        # 샘플 엑셀 다운로드
        sample_data = {
            '보내는분_이름': ['홍길동', '김영희'],
            '보내는분_연락처': ['01012345678', '01087654321'],
            '보내는분_주소': ['서울시 강남구 테헤란로 123', '서울시 서초구 반포대로 456'],
            '보내는분_상세주소': ['101동 1001호', '202동 2002호'],
            '받는분_이름': ['이철수', '박민수'],
            '받는분_연락처': ['01011112222', '01033334444'],
            '받는분_주소': ['부산시 해운대구 해운대로 789', '대구시 수성구 달구벌대로 321'],
            '받는분_상세주소': ['301동 3001호', '402동 4002호'],
            '포장유형': ['박스', '서류'],
            '무게': ['5kg 이하', '5~10kg'],
            '크기': ['소형', '중형'],
            '내용물': ['의류', '도서'],
            '요청사항': ['파손주의', '경비실 맡기기']
        }
        sample_df = pd.DataFrame(sample_data)
        
        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sample_df.to_excel(writer, index=False, sheet_name='택배접수')
        excel_data = output.getvalue()
        
        col_download, col_upload = st.columns(2)
        
        with col_download:
            st.download_button(
                label="📥 샘플 양식 다운로드",
                data=excel_data,
                file_name="택배접수_양식.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        st.markdown("---")
        
        # 엑셀 업로드
        uploaded_file = st.file_uploader(
            "📁 엑셀 파일 업로드 (.xlsx, .xls)",
            type=['xlsx', 'xls'],
            key="bulk_delivery_upload"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ 파일 업로드 완료! 총 **{len(df)}건**의 택배 정보가 확인되었습니다.")
                
                # 데이터 미리보기
                with st.expander("📋 업로드된 데이터 미리보기", expanded=True):
                    st.dataframe(df, use_container_width=True, height=300)
                
                # 데이터 검증
                required_cols = ['보내는분_이름', '보내는분_연락처', '보내는분_주소', 
                                '받는분_이름', '받는분_연락처', '받는분_주소']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"❌ 필수 컬럼이 누락되었습니다: {', '.join(missing_cols)}")
                else:
                    # 유효성 검사
                    errors = []
                    for idx, row in df.iterrows():
                        row_errors = []
                        if pd.isna(row.get('보내는분_이름')) or str(row.get('보내는분_이름', '')).strip() == '':
                            row_errors.append('보내는분 이름 누락')
                        if pd.isna(row.get('받는분_이름')) or str(row.get('받는분_이름', '')).strip() == '':
                            row_errors.append('받는분 이름 누락')
                        if row_errors:
                            errors.append(f"행 {idx+2}: {', '.join(row_errors)}")
                    
                    if errors:
                        st.warning(f"⚠️ {len(errors)}건의 오류가 발견되었습니다:")
                        for err in errors[:5]:
                            st.caption(f"  • {err}")
                        if len(errors) > 5:
                            st.caption(f"  ... 외 {len(errors)-5}건")
                    
                    # 접수 진행
                    st.markdown("---")
                    
                    if st.button("🚀 대량 접수 시작", use_container_width=True, type="primary"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        results = []
                        success_count = 0
                        fail_count = 0
                        
                        for idx, row in df.iterrows():
                            try:
                                # 진행률 업데이트
                                progress = (idx + 1) / len(df)
                                progress_bar.progress(progress)
                                status_text.text(f"처리 중... {idx+1}/{len(df)}")
                                
                                # 데이터 추출
                                sender_name = str(row.get('보내는분_이름', '')).strip()
                                sender_phone = str(row.get('보내는분_연락처', '')).strip()
                                sender_addr = str(row.get('보내는분_주소', '')).strip()
                                sender_detail = str(row.get('보내는분_상세주소', '')).strip()
                                receiver_name = str(row.get('받는분_이름', '')).strip()
                                receiver_phone = str(row.get('받는분_연락처', '')).strip()
                                receiver_addr = str(row.get('받는분_주소', '')).strip()
                                receiver_detail = str(row.get('받는분_상세주소', '')).strip()
                                pkg_type = str(row.get('포장유형', '박스')).strip()
                                pkg_weight = str(row.get('무게', '5kg 이하')).strip()
                                pkg_size = str(row.get('크기', '소형')).strip()
                                contents = str(row.get('내용물', '')).strip()
                                req_msg = str(row.get('요청사항', '')).strip()
                                
                                if not sender_name or not receiver_name:
                                    raise ValueError("필수 정보 누락")
                                
                                # 주문 저장
                                order_content = f"""[대량 택배 접수 #{idx+1}]
📤 보내는 분: {sender_name} ({sender_phone})
   주소: {sender_addr} {sender_detail}
📥 받는 분: {receiver_name} ({receiver_phone})
   주소: {receiver_addr} {receiver_detail}
📋 화물: {pkg_type} / {pkg_weight} / {pkg_size}
   내용물: {contents}"""
                                
                                # DB 저장
                                from datetime import datetime
                                order_data = {
                                    'store_id': store_id,
                                    'store_name': store.get('name', ''),
                                    'order_content': order_content,
                                    'address': receiver_addr,
                                    'phone': sender_phone,
                                    'total_price': '',
                                    'request': req_msg,
                                    'status': '접수완료',
                                    'order_type': '대량택배'
                                }
                                save_order(order_data)
                                
                                results.append({
                                    '순번': idx + 1,
                                    '보내는분': sender_name,
                                    '받는분': receiver_name,
                                    '받는주소': receiver_addr,
                                    '상태': '✅ 접수완료',
                                    '비고': ''
                                })
                                success_count += 1
                                
                            except Exception as e:
                                results.append({
                                    '순번': idx + 1,
                                    '보내는분': str(row.get('보내는분_이름', '')),
                                    '받는분': str(row.get('받는분_이름', '')),
                                    '받는주소': str(row.get('받는분_주소', '')),
                                    '상태': '❌ 실패',
                                    '비고': str(e)
                                })
                                fail_count += 1
                        
                        progress_bar.progress(1.0)
                        status_text.empty()
                        
                        # 결과 표시
                        st.balloons()
                        st.success(f"🎉 대량 접수 완료! 성공: **{success_count}건** / 실패: **{fail_count}건**")
                        
                        # 결과 DataFrame
                        result_df = pd.DataFrame(results)
                        
                        st.markdown("### 📊 접수 결과")
                        st.dataframe(result_df, use_container_width=True)
                        
                        # 결과 엑셀 다운로드
                        result_output = io.BytesIO()
                        with pd.ExcelWriter(result_output, engine='openpyxl') as writer:
                            result_df.to_excel(writer, index=False, sheet_name='접수결과')
                        result_excel = result_output.getvalue()
                        
                        st.download_button(
                            label="📥 접수 결과 다운로드 (Excel)",
                            data=result_excel,
                            file_name=f"택배접수_결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        
                        # 로젠택배 연동 안내
                        st.markdown("---")
                        st.info("""
                        ### 🚚 로젠택배 운송장 발급 안내
                        
                        대량 접수가 완료되었습니다! 실제 운송장 발급을 위해:
                        
                        1. 아래 버튼을 클릭하여 **로젠택배 사이트**로 이동
                        2. 사업자 계정으로 로그인
                        3. **일괄 접수** 메뉴에서 위 결과 파일을 업로드
                        4. 운송장 번호 발급 완료!
                        """)
                        
                        st.link_button(
                            "🚚 로젠택배 일괄접수 바로가기",
                            "https://www.ilogen.com/m/personal/tkPersonalWaybillList.dev",
                            use_container_width=True
                        )
                        
            except Exception as e:
                st.error(f"❌ 파일 처리 중 오류가 발생했습니다: {str(e)}")


# ==========================================
# 👔 세탁 - 세탁물 접수 폼
# ==========================================
def render_laundry_form(store, store_id):
    """세탁/클리닝용 접수 폼"""
    st.markdown("### 👔 세탁물 접수/수거 예약")
    
    service_type = st.radio(
        "서비스 유형",
        ["🚗 수거 요청", "🏪 직접 방문"],
        horizontal=True
    )
    
    with st.form("laundry_form"):
        st.markdown("#### 👤 고객 정보")
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("이름", placeholder="홍길동")
            customer_phone = st.text_input("연락처", placeholder="01012345678")
        with col2:
            if "수거" in service_type:
                address = st.text_input("수거 주소", placeholder="서울시 강남구...")
                pickup_date = st.date_input("수거 희망일")
            else:
                address = ""
                pickup_date = st.date_input("방문 예정일")
        
        st.markdown("---")
        st.markdown("#### 👕 세탁물 정보")
        
        laundry_items = []
        col3, col4 = st.columns(2)
        with col3:
            shirt_cnt = st.number_input("셔츠/블라우스", min_value=0, value=0)
            pants_cnt = st.number_input("바지/치마", min_value=0, value=0)
            suit_cnt = st.number_input("정장 (상의/하의)", min_value=0, value=0)
        with col4:
            coat_cnt = st.number_input("코트/점퍼", min_value=0, value=0)
            dress_cnt = st.number_input("원피스/드레스", min_value=0, value=0)
            other_cnt = st.number_input("기타", min_value=0, value=0)
        
        special_care = st.multiselect(
            "특수 처리",
            ["드라이클리닝", "다림질", "얼룩 제거", "수선", "급행 세탁"]
        )
        
        request = st.text_area("요청사항", placeholder="얼룩 위치, 특별 주의사항 등", height=60)
        
        if st.form_submit_button("👔 세탁물 접수하기", use_container_width=True, type="primary"):
            if not customer_name or not customer_phone:
                st.error("❌ 고객 정보를 입력해주세요!")
            else:
                items_str = []
                if shirt_cnt > 0: items_str.append(f"셔츠/블라우스 {shirt_cnt}개")
                if pants_cnt > 0: items_str.append(f"바지/치마 {pants_cnt}개")
                if suit_cnt > 0: items_str.append(f"정장 {suit_cnt}벌")
                if coat_cnt > 0: items_str.append(f"코트/점퍼 {coat_cnt}개")
                if dress_cnt > 0: items_str.append(f"원피스/드레스 {dress_cnt}개")
                if other_cnt > 0: items_str.append(f"기타 {other_cnt}개")
                
                order_content = f"""[세탁물 접수]
👤 고객: {customer_name} ({customer_phone})
🚗 서비스: {service_type}
📅 일자: {pickup_date}
👕 세탁물: {', '.join(items_str) if items_str else '상담 필요'}
✨ 특수 처리: {', '.join(special_care) if special_care else '없음'}"""
                process_order(store, store_id, order_content, customer_phone, address, "", request, "접수")


# ==========================================
# 🛒 일반판매 - 상품 구매 폼
# ==========================================
def render_retail_form(store, store_id):
    """일반판매용 상품 구매 폼"""
    st.markdown("### 🛒 상품 구매")
    
    with st.form("retail_form"):
        order_content = st.text_area(
            "주문 상품",
            placeholder="상품명 - 수량\n예: 스마트워치 1개, 충전케이블 2개",
            height=120
        )
        
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("주문자 이름", placeholder="홍길동")
            customer_phone = st.text_input("연락처", placeholder="01012345678")
            total_price = st.text_input("결제 금액", placeholder="50000")
        with col2:
            delivery_method = st.selectbox(
                "배송 방법",
                ["🚗 일반 배송 (2-3일)", "⚡ 빠른 배송 (당일/익일)", "🏪 매장 직접 수령"]
            )
            
            if "매장" not in delivery_method:
                address = st.text_input("배송지 주소", placeholder="서울시 강남구...")
            else:
                address = "매장 수령"
        
        payment_method = st.radio(
            "결제 방법",
            ["💳 카드 결제", "🏦 무통장 입금", "💵 현금/현장 결제"],
            horizontal=True
        )
        
        request = st.text_area("요청사항", placeholder="선물 포장 요청, 배송 메모 등", height=60)
        
        if st.form_submit_button("🛒 주문하기", use_container_width=True, type="primary"):
            if not order_content:
                st.error("❌ 주문 상품을 입력해주세요!")
            elif not customer_name or not customer_phone:
                st.error("❌ 주문자 정보를 입력해주세요!")
            elif "매장" not in delivery_method and not address:
                st.error("❌ 배송지 주소를 입력해주세요!")
            else:
                full_order = f"""[상품 주문]
👤 주문자: {customer_name} ({customer_phone})
📦 상품: {order_content}
🚗 배송: {delivery_method}
💳 결제: {payment_method}"""
                process_order(store, store_id, full_order, customer_phone, address, total_price, request, "주문")


# ==========================================
# 📋 기타/서비스 - 일반 예약 폼
# ==========================================
def render_general_form(store, store_id):
    """기타 업종용 일반 예약/주문 폼"""
    category_name = BUSINESS_CATEGORIES.get(store.get('category', 'other'), {}).get('name', '서비스')
    st.markdown(f"### {category_name} 예약/문의")
    
    with st.form("general_form"):
        service_content = st.text_area(
            "서비스/상품 내용",
            placeholder="원하시는 서비스나 상품을 자세히 적어주세요",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("이름", placeholder="홍길동")
            customer_phone = st.text_input("연락처", placeholder="01012345678")
        with col2:
            preferred_date = st.date_input("희망 일자")
            preferred_time = st.time_input("희망 시간")
        
        address = st.text_input("주소 (필요시)", placeholder="방문 서비스인 경우 주소 입력")
        request = st.text_area("추가 요청사항", placeholder="기타 문의사항", height=60)
        
        if st.form_submit_button("📋 예약/문의하기", use_container_width=True, type="primary"):
            if not service_content:
                st.error("❌ 서비스/상품 내용을 입력해주세요!")
            elif not customer_name or not customer_phone:
                st.error("❌ 고객 정보를 입력해주세요!")
            else:
                order_content = f"""[서비스 예약/문의]
👤 고객: {customer_name} ({customer_phone})
📅 희망 일시: {preferred_date} {preferred_time}
📋 내용: {service_content}"""
                process_order(store, store_id, order_content, customer_phone, address, "", request, "예약")


# ==========================================
# 📱 사이드바 메뉴
# ==========================================
with st.sidebar:
    st.markdown("**동네비서**")
    
    menu = st.radio(
        "메뉴", 
        ["서비스 선택", "사용요금", "사장님 가입", "이용 안내"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 회사소개 (수정 가능)
    if "company_intro" not in st.session_state:
        st.session_state.company_intro = "회사 소개를 입력하세요."
    
    st.markdown("**회사소개**")
    company_text = st.text_area(
        "회사소개",
        value=st.session_state.company_intro,
        height=100,
        label_visibility="collapsed",
        key="company_intro_input"
    )
    st.session_state.company_intro = company_text
    
    st.markdown("---")
    st.caption("관리자: admin.py")

# ==========================================
# 🏠 서비스 선택 페이지 (첫 화면)
# ==========================================
if menu == "서비스 선택":
    
    # ==========================================
    # 🔗 직접 링크로 접속한 경우 (특정 가게로 바로 이동)
    # ==========================================
    if st.session_state.get("show_direct_store"):
        direct_store_id = st.session_state.get("direct_store_id")
        direct_store = st.session_state.get("direct_store_info", {})
        store_name = direct_store.get('name', direct_store_id)
        
        # 가게 헤더 (라인 스타일)
        st.markdown(f"""
        <div style="text-align: center; padding: 32px 16px; margin-bottom: 24px;">
            <p style="font-size: 14px; color: #888; margin: 0 0 8px 0;">{store_name}</p>
            <p style="font-size: 16px; font-weight: 600; color: #000; margin: 0;">서비스를 선택해주세요</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 매장 예약 버튼
        if st.button("매장 예약", key="btn_direct_store", use_container_width=True):
            st.session_state.selected_store_id = direct_store_id
            st.session_state.show_store_page = True
            st.session_state.show_direct_store = False
            st.rerun()
        
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        
        # 택배 접수 버튼
        if st.button("택배 접수", key="btn_direct_delivery", use_container_width=True):
            st.session_state.service_type = "delivery"
            st.session_state.show_delivery_form = True
            st.session_state.show_direct_store = False
            st.rerun()
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        # 다른 가게 보기
        if st.button("다른 매장 보기", key="btn_browse_other", use_container_width=True):
            st.session_state.show_direct_store = False
            st.session_state.direct_store_loaded = False
            st.query_params.clear()
            st.rerun()
        
        st.stop()
    
    # ==========================================
    # 🏠 일반 서비스 선택 화면
    # ==========================================
    
    # 다른 화면이 활성화되지 않은 경우에만 서비스 선택 화면 표시
    show_service_selection = not (
        st.session_state.get("show_store_list") or 
        st.session_state.get("show_delivery_form") or 
        st.session_state.get("show_store_page")
    )
    
    if show_service_selection:
        # --- 상단 로그인 바 ---
        st.markdown("""
        <div class="fixed-header">
            <div style="display:flex; justify-content:space-between; align-items:center; max-width:480px; margin:0 auto;">
                <span style="font-weight:bold; font-size:1.2em;">동네비서</span>
                <a href="#" style="color:white; text-decoration:none;">로그인</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 상단바 때문에 콘텐츠가 가려지지 않도록 빈 공간 추가
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # --- 중앙 주요 메뉴 (카드형 디자인) ---
        st.markdown("<h3 style='text-align:center; margin-bottom:20px;'>무엇을 도와드릴까요?</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="app-card">
                <h3>🏠 매장 예약</h3>
                <p>예약, 주문 접수</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("매장 예약", key="btn_store", use_container_width=True):
                st.session_state.service_type = "store"
                st.session_state.show_store_list = True
                st.rerun()
        
        with col2:
            st.markdown("""
            <div class="app-card">
                <h3>📦 택배 접수</h3>
                <p>로젠택배 연동</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("택배 접수", key="btn_delivery", use_container_width=True):
                st.session_state.service_type = "delivery"
                st.session_state.show_delivery_form = True
                st.rerun()
        
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        # 사장님 혜택
        with st.expander("🎁 사장님 혜택"):
            st.markdown("""
✅ 수수료 0원  
✅ AI 24시간 응대  
✅ 자동 정산  
✅ 단골 관리
            """)
        
        # 최신 소식
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("<h4>최신 소식</h4>", unsafe_allow_html=True)
        st.info("🎉 동네비서 앱이 새롭게 출시되었습니다!")
        
        # 하단바 공간 확보
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        
        # --- 하단 내비게이션 바 ---
        st.markdown("""
        <div class="fixed-footer">
            <div style="display:flex; justify-content:space-around; align-items:center; max-width:480px; margin:0 auto;">
                <a href="#" style="color:white; text-decoration:none;">🏠 홈</a>
                <a href="#" style="color:white; text-decoration:none;">📞 고객센터</a>
                <a href="#" style="color:white; text-decoration:none;">👤 마이</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 서비스 타입에 따른 화면 표시
    if st.session_state.get("show_store_list"):
        st.markdown("""
        <div style="text-align: center; padding: 24px 16px; margin-bottom: 16px;">
            <p style="font-size: 16px; font-weight: 600; color: #000; margin: 0 0 4px 0;">매장 선택</p>
            <p style="font-size: 14px; color: #888; margin: 0;">방문하실 매장을 선택해주세요</p>
        </div>
        """, unsafe_allow_html=True)
        
        stores = get_all_stores()
        if stores:
            # 식당/카페 등 매장형 업종만 필터링
            store_categories = ['restaurant', 'cafe', 'salon', 'other']
            filtered_stores = {k: v for k, v in stores.items() 
                             if v.get('category', 'other') in store_categories}
            
            if filtered_stores:
                store_names = [f"{v.get('name', k)} ({k})" for k, v in filtered_stores.items()]
                store_ids = list(filtered_stores.keys())
                
                selected_idx = st.selectbox(
                    "매장",
                    range(len(store_names)),
                    format_func=lambda x: store_names[x]
                )
                
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                
                if st.button("매장 입장", key="btn_enter_store", use_container_width=True):
                    st.session_state.selected_store_id = store_ids[selected_idx]
                    st.session_state.show_store_page = True
                    st.rerun()
            else:
                st.info("등록된 매장이 없습니다.")
        else:
            st.info("등록된 매장이 없습니다.")
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        if st.button("돌아가기", key="back_from_store_list", use_container_width=True):
            st.session_state.show_store_list = False
            st.rerun()
    
    elif st.session_state.get("show_delivery_form"):
        st.markdown("""
        <div style="text-align: center; padding: 24px 16px; margin-bottom: 16px;">
            <p style="font-size: 16px; font-weight: 600; color: #000; margin: 0 0 4px 0;">택배 접수</p>
            <p style="font-size: 14px; color: #888; margin: 0;">간편하게 택배를 보내세요</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 로젠택배 모듈 임포트
        from logen_delivery import (
            calculate_delivery_fee, estimate_delivery_date, 
            create_delivery_reservation, process_bulk_reservations,
            get_fee_table_html, get_weight_options, get_size_options,
            parse_weight, parse_size, LOGEN_PERSONAL_URL
        )
        from db_manager import save_logen_reservation, save_bulk_logen_reservations
        
        # 탭으로 단건/대량 분리
        tab_single, tab_bulk, tab_fee = st.tabs(["단건 접수", "대량 접수", "요금표"])
        
        # ==========================================
        # 📦 단건 접수 탭
        # ==========================================
        with tab_single:
            st.markdown("예상 요금 확인 후 접수를 진행합니다.")
            
            # 세션 상태 초기화
            if 'delivery_step' not in st.session_state:
                st.session_state.delivery_step = 1  # 1: 입력, 2: 요금확인, 3: 완료
            if 'delivery_data' not in st.session_state:
                st.session_state.delivery_data = {}
            
            # STEP 1: 배송 정보 입력
            if st.session_state.delivery_step == 1:
                st.markdown("**보내는 분**")
                sender_col1, sender_col2 = st.columns(2)
                with sender_col1:
                    sender_name = st.text_input("이름 *", key="logen_sender_name")
                    sender_phone = st.text_input("연락처 *", key="logen_sender_phone", placeholder="010-0000-0000")
                with sender_col2:
                    sender_address = st.text_input("주소 *", key="logen_sender_address", placeholder="서울시 강남구...")
                    sender_detail = st.text_input("상세주소", key="logen_sender_detail", placeholder="101동 1001호")
                
                st.markdown("---")
                st.markdown("##### 📥 받는 분")
                recv_col1, recv_col2 = st.columns(2)
                with recv_col1:
                    receiver_name = st.text_input("이름 *", key="logen_receiver_name")
                    receiver_phone = st.text_input("연락처 *", key="logen_receiver_phone", placeholder="010-0000-0000")
                with recv_col2:
                    receiver_address = st.text_input("주소 *", key="logen_receiver_address", placeholder="서울시 강남구...")
                    receiver_detail = st.text_input("상세주소", key="logen_receiver_detail", placeholder="201동 2001호")
                
                st.markdown("---")
                st.markdown("##### 📦 화물 정보")
                pkg_col1, pkg_col2, pkg_col3 = st.columns(3)
                with pkg_col1:
                    package_type = st.selectbox("포장 유형", ["📦 박스", "📄 서류", "🎁 선물", "🔧 기타"], key="logen_pkg_type")
                    package_weight = st.selectbox("무게", get_weight_options(), key="logen_pkg_weight")
                with pkg_col2:
                    package_size = st.selectbox("크기", get_size_options(), key="logen_pkg_size")
                    region_type = st.selectbox("지역", ["일반", "도서지역 (+3,000원)", "산간지역 (+2,000원)"], key="logen_region")
                with pkg_col3:
                    pickup_date = st.date_input("수거 희망일", key="logen_pickup_date")
                    payment_type = st.radio("결제 방식", ["선불", "착불"], horizontal=True, key="logen_payment")
                
                package_contents = st.text_input("내용물", key="logen_contents", placeholder="의류, 도서, 전자제품 등")
                memo = st.text_area("요청사항 (선택)", key="logen_memo", placeholder="파손 주의 / 경비실 맡기기 / 부재시 문앞", height=60)
                
                if st.button("💰 예상 요금 확인하기", use_container_width=True, type="primary"):
                    # 필수 입력 확인
                    if not all([sender_name, sender_phone, sender_address, receiver_name, receiver_phone, receiver_address]):
                        st.error("❌ 보내는 분과 받는 분의 필수 정보를 모두 입력해주세요.")
                    else:
                        # 요금 계산
                        weight_kg = parse_weight(package_weight)
                        size_cat = parse_size(package_size)
                        region = "일반"
                        if "도서" in region_type:
                            region = "도서"
                        elif "산간" in region_type:
                            region = "산간"
                        
                        fee_info = calculate_delivery_fee(
                            weight_kg=weight_kg,
                            size_category=size_cat,
                            is_remote=region,
                            is_prepaid=(payment_type == "선불")
                        )
                        
                        delivery_est = estimate_delivery_date(datetime.combine(pickup_date, datetime.min.time()))
                        
                        # 데이터 저장
                        st.session_state.delivery_data = {
                            'sender': {
                                'name': sender_name,
                                'phone': sender_phone,
                                'address': sender_address,
                                'detail_address': sender_detail
                            },
                            'receiver': {
                                'name': receiver_name,
                                'phone': receiver_phone,
                                'address': receiver_address,
                                'detail_address': receiver_detail
                            },
                            'package': {
                                'type': package_type.split()[1] if ' ' in package_type else package_type,
                                'weight': weight_kg,
                                'size': size_cat,
                                'contents': package_contents
                            },
                            'pickup_date': pickup_date.strftime("%Y-%m-%d"),
                            'memo': memo,
                            'fee': fee_info,
                            'delivery_estimate': delivery_est
                        }
                        
                        st.session_state.delivery_step = 2
                        st.rerun()
            
            # STEP 2: 요금 확인 및 승인
            elif st.session_state.delivery_step == 2:
                st.markdown("#### 💰 STEP 2: 예상 요금 확인")
                
                data = st.session_state.delivery_data
                fee = data.get('fee', {})
                delivery_est = data.get('delivery_estimate', {})
                
                # 요금 정보 표시
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                            padding: 2rem; border-radius: 20px; color: white; margin-bottom: 1rem;">
                    <div style="text-align: center;">
                        <div style="font-size: 1.2rem; opacity: 0.9;">예상 배송 요금</div>
                        <div style="font-size: 3rem; font-weight: bold; margin: 0.5rem 0;">{fee.get('total_fee', 0):,}원</div>
                        <div style="font-size: 1rem; opacity: 0.9;">{fee.get('payment_type', '선불')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 요금 상세
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**📋 요금 상세**")
                    st.markdown(f"""
                    - 기본 요금 ({fee.get('weight_category', '')}): **{fee.get('base_fee', 0):,}원**
                    - 크기 추가 ({fee.get('size_category', '')}): **+{fee.get('size_fee', 0):,}원**
                    - 지역 추가 ({fee.get('remote_category', '')}): **+{fee.get('remote_fee', 0):,}원**
                    """)
                
                with col2:
                    st.markdown("**🚚 배송 예정**")
                    st.markdown(f"""
                    - 수거일: **{data.get('pickup_date', '')}**
                    - 배송 예정: **{delivery_est.get('estimated_text', '')}**
                    """)
                
                st.markdown("---")
                
                # 배송 정보 요약
                with st.expander("📦 배송 정보 확인", expanded=True):
                    sender = data.get('sender', {})
                    receiver = data.get('receiver', {})
                    package = data.get('package', {})
                    
                    col_s, col_r = st.columns(2)
                    with col_s:
                        st.markdown(f"""
                        **📤 보내는 분**
                        - {sender.get('name', '')} ({sender.get('phone', '')})
                        - {sender.get('address', '')} {sender.get('detail_address', '')}
                        """)
                    with col_r:
                        st.markdown(f"""
                        **📥 받는 분**
                        - {receiver.get('name', '')} ({receiver.get('phone', '')})
                        - {receiver.get('address', '')} {receiver.get('detail_address', '')}
                        """)
                    
                    st.markdown(f"**📦 화물:** {package.get('type', '')} / {package.get('weight', '')}kg / {package.get('size', '')} / 내용물: {package.get('contents', '-')}")
                    if data.get('memo'):
                        st.markdown(f"**💬 요청사항:** {data.get('memo', '')}")
                
                st.markdown("---")
                
                # 승인/취소 버튼
                col_approve, col_cancel = st.columns(2)
                with col_approve:
                    if st.button("✅ 접수 확정하기", use_container_width=True, type="primary"):
                        with st.spinner("택배 접수 중..."):
                            # 예약 생성
                            result, error = create_delivery_reservation(
                                sender=data['sender'],
                                receiver=data['receiver'],
                                package=data['package'],
                                pickup_date=data.get('pickup_date'),
                                memo=data.get('memo', '')
                            )
                            
                            if error:
                                st.error(f"❌ 접수 실패: {error}")
                            else:
                                # 구글 시트에 저장
                                save_result = save_logen_reservation({
                                    'reservation_number': result.get('reservation_number'),
                                    'sender': data['sender'],
                                    'receiver': data['receiver'],
                                    'package': data['package'],
                                    'fee': data['fee'],
                                    'pickup_date': data.get('pickup_date'),
                                    'delivery_estimate': data.get('delivery_estimate'),
                                    'memo': data.get('memo', ''),
                                    'status': '접수완료'
                                })
                                
                                st.session_state.delivery_data['result'] = result
                                st.session_state.delivery_step = 3
                                st.rerun()
                
                with col_cancel:
                    if st.button("⬅️ 정보 수정하기", use_container_width=True):
                        st.session_state.delivery_step = 1
                        st.rerun()
            
            # STEP 3: 접수 완료
            elif st.session_state.delivery_step == 3:
                st.markdown("#### 🎉 STEP 3: 접수 완료!")
                
                result = st.session_state.delivery_data.get('result', {})
                fee = st.session_state.delivery_data.get('fee', {})
                delivery_est = st.session_state.delivery_data.get('delivery_estimate', {})
                
                st.balloons()
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            padding: 2rem; border-radius: 20px; color: white; text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
                    <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">택배 접수가 완료되었습니다!</div>
                    <div style="font-size: 1.2rem; opacity: 0.95;">
                        예약번호: <strong>{result.get('reservation_number', 'N/A')}</strong>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💰 결제 금액", f"{fee.get('total_fee', 0):,}원")
                with col2:
                    st.metric("📅 수거 예정일", st.session_state.delivery_data.get('pickup_date', '-'))
                with col3:
                    st.metric("🚚 배송 예정", delivery_est.get('estimated_text', '-'))
                
                st.markdown("---")
                st.info("""
                📌 **안내사항**
                - 예약번호를 메모해두세요
                - 수거 기사님이 예정일에 방문합니다
                - 배송 조회: 로젠택배 사이트에서 예약번호로 조회 가능
                """)
                
                col_new, col_home = st.columns(2)
                with col_new:
                    if st.button("📦 새로운 택배 접수", use_container_width=True, type="primary"):
                        st.session_state.delivery_step = 1
                        st.session_state.delivery_data = {}
                        st.rerun()
                with col_home:
                    if st.button("🏠 홈으로", use_container_width=True):
                        st.session_state.delivery_step = 1
                        st.session_state.delivery_data = {}
                        st.session_state.show_delivery_form = False
                        st.rerun()
                
                st.link_button("🔗 로젠택배 배송조회", "https://www.ilogen.com/web/personal/trace", use_container_width=True)
        
        # ==========================================
        # 📊 대량 접수 탭 (엑셀)
        # ==========================================
        with tab_bulk:
            import pandas as pd
            import io
            
            st.markdown("#### 📊 엑셀 파일로 대량 택배 접수")
            st.info("💡 엑셀 파일을 업로드하면 예상 요금을 확인하고 한 번에 여러 건의 택배를 접수할 수 있습니다.")
            
            # 샘플 엑셀 다운로드
            sample_data = {
                '보내는분_이름': ['홍길동', '김영희'],
                '보내는분_연락처': ['01012345678', '01087654321'],
                '보내는분_주소': ['서울시 강남구 테헤란로 123', '서울시 서초구 반포대로 456'],
                '보내는분_상세주소': ['101동 1001호', '202동 2002호'],
                '받는분_이름': ['이철수', '박민수'],
                '받는분_연락처': ['01011112222', '01033334444'],
                '받는분_주소': ['부산시 해운대구 해운대로 789', '대구시 수성구 달구벌대로 321'],
                '받는분_상세주소': ['301동 3001호', '402동 4002호'],
                '포장유형': ['박스', '서류'],
                '무게': ['2kg 이하', '5kg 이하'],
                '크기': ['소형', '중형'],
                '내용물': ['의류', '도서'],
                '요청사항': ['파손주의', '경비실 맡기기']
            }
            sample_df = pd.DataFrame(sample_data)
            
            # 엑셀 파일 생성
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                sample_df.to_excel(writer, index=False, sheet_name='택배접수')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 샘플 양식 다운로드",
                data=excel_data,
                file_name="로젠택배_대량접수_양식.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            st.markdown("---")
            
            # 엑셀 업로드
            uploaded_file = st.file_uploader(
                "📁 엑셀 파일 업로드 (.xlsx, .xls)",
                type=['xlsx', 'xls'],
                key="logen_bulk_upload"
            )
            
            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file)
                    
                    st.success(f"✅ 파일 업로드 완료! 총 **{len(df)}건**의 택배 정보가 확인되었습니다.")
                    
                    # 데이터 미리보기
                    with st.expander("📋 업로드된 데이터 미리보기", expanded=True):
                        st.dataframe(df, use_container_width=True, height=200)
                    
                    # 예상 요금 계산
                    st.markdown("---")
                    st.markdown("#### 💰 예상 요금 계산")
                    
                    total_fee = 0
                    fee_details = []
                    
                    for idx, row in df.iterrows():
                        weight_str = str(row.get('무게', '2kg 이하'))
                        size_str = str(row.get('크기', '소형'))
                        
                        weight_kg = parse_weight(weight_str)
                        size_cat = parse_size(size_str)
                        
                        fee_info = calculate_delivery_fee(weight_kg, size_cat)
                        total_fee += fee_info['total_fee']
                        
                        fee_details.append({
                            '순번': idx + 1,
                            '받는분': row.get('받는분_이름', ''),
                            '무게': weight_str,
                            '크기': size_cat,
                            '예상요금': f"{fee_info['total_fee']:,}원"
                        })
                    
                    # 요금 요약
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                                padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 1rem;">
                        <div style="font-size: 1rem; opacity: 0.9;">총 {len(df)}건 예상 요금</div>
                        <div style="font-size: 2.5rem; font-weight: bold;">{total_fee:,}원</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 개별 요금 표시
                    with st.expander("📊 개별 요금 상세"):
                        fee_df = pd.DataFrame(fee_details)
                        st.dataframe(fee_df, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # 대량 접수 버튼
                    if st.button("🚀 대량 접수 시작", use_container_width=True, type="primary"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # 예약 데이터 준비
                        reservations = []
                        for idx, row in df.iterrows():
                            reservations.append({
                                'sender_name': str(row.get('보내는분_이름', '')),
                                'sender_phone': str(row.get('보내는분_연락처', '')),
                                'sender_address': str(row.get('보내는분_주소', '')),
                                'sender_detail': str(row.get('보내는분_상세주소', '')),
                                'receiver_name': str(row.get('받는분_이름', '')),
                                'receiver_phone': str(row.get('받는분_연락처', '')),
                                'receiver_address': str(row.get('받는분_주소', '')),
                                'receiver_detail': str(row.get('받는분_상세주소', '')),
                                'package_type': str(row.get('포장유형', '박스')),
                                'weight': parse_weight(str(row.get('무게', '2kg 이하'))),
                                'size': parse_size(str(row.get('크기', '소형'))),
                                'contents': str(row.get('내용물', '')),
                                'memo': str(row.get('요청사항', ''))
                            })
                        
                        # 진행 콜백 함수
                        def update_progress(current, total):
                            progress_bar.progress(current / total)
                            status_text.text(f"처리 중... {current}/{total}")
                        
                        # 대량 접수 처리
                        result = process_bulk_reservations(reservations, update_progress)
                        
                        progress_bar.progress(1.0)
                        status_text.empty()
                        
                        # 결과 저장
                        save_bulk_logen_reservations(result)
                        
                        # 결과 표시
                        st.balloons()
                        st.success(f"🎉 대량 접수 완료! 성공: **{result['success_count']}건** / 실패: **{result['fail_count']}건**")
                        st.info(f"💰 총 요금: **{result['total_fee']:,}원**")
                        
                        # 결과 DataFrame
                        result_data = []
                        for r in result['results']:
                            result_data.append({
                                '순번': r['index'],
                                '보내는분': r.get('sender_name', ''),
                                '받는분': r.get('receiver_name', ''),
                                '상태': '✅ 접수완료' if r['success'] else '❌ 실패',
                                '예약번호': r.get('reservation_number', '-'),
                                '요금': f"{r.get('fee', 0):,}원" if r['success'] else '-',
                                '비고': r.get('error', '') if not r['success'] else ''
                            })
                        
                        result_df = pd.DataFrame(result_data)
                        st.dataframe(result_df, use_container_width=True)
                        
                        # 결과 엑셀 다운로드
                        result_output = io.BytesIO()
                        with pd.ExcelWriter(result_output, engine='openpyxl') as writer:
                            result_df.to_excel(writer, index=False, sheet_name='접수결과')
                        result_excel = result_output.getvalue()
                        
                        st.download_button(
                            label="📥 접수 결과 다운로드 (Excel)",
                            data=result_excel,
                            file_name=f"로젠택배_접수결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        
                except Exception as e:
                    st.error(f"❌ 파일 처리 중 오류: {str(e)}")
        
        # ==========================================
        # 💰 요금표 탭
        # ==========================================
        with tab_fee:
            st.markdown(get_fee_table_html(), unsafe_allow_html=True)
            
            st.markdown("---")
            st.link_button("🔗 로젠택배 공식 사이트", "https://www.ilogen.com/", use_container_width=True)
        
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        
        if st.button("⬅️  처음으로 돌아가기", key="back_from_delivery", use_container_width=True):
            st.session_state.show_delivery_form = False
            st.rerun()
    
    elif st.session_state.get("show_store_page"):
        # 선택한 매장 페이지 표시
        store_id = st.session_state.get("selected_store_id")
        stores = get_all_stores()
        store = stores.get(store_id, {})
        
        st.markdown(f"### 🏪 {store.get('name', store_id)}")
        
        category = store.get('category', 'other')
        
        # 테이블 예약 폼 (식당/카페인 경우)
        if category in ['restaurant', 'cafe']:
            render_table_reservation_form(store_id, store)
        else:
            # 일반 주문 폼
            render_order_form(store_id, store)
        
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        
        if st.button("⬅️  매장 목록으로 돌아가기", key="back_from_store_page", use_container_width=True):
            st.session_state.show_store_page = False
            st.rerun()
    
    else:
        # 하단 홍보
        st.markdown("")
        st.success("""
        🎁 **사장님이신가요?**
        
        지금 가입하면 **한 달 무료 체험** 혜택!
        
        사이드바에서 '🆕 사장님 가입'을 눌러주세요.
        """)


# ==========================================
# 💰 사용요금
# ==========================================
elif menu == "사용요금":
    st.markdown("""
    <div style="text-align: center; padding: 24px 16px; margin-bottom: 16px;">
        <p style="font-size: 16px; font-weight: 600; color: #000; margin: 0 0 4px 0;">사용요금 안내</p>
        <p style="font-size: 14px; color: #888; margin: 0;">월 정액제로 간편하게 이용하세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 일반/간이 사업자
    st.markdown("""
    <div style="border: 1px solid #ccc; padding: 20px; margin-bottom: 12px;">
        <p style="font-size: 14px; font-weight: 500; color: #000; margin: 0 0 8px 0;">일반사업자 / 간이사업자</p>
        <p style="font-size: 14px; color: #333; margin: 0 0 4px 0;">월 <b>50,000원</b></p>
        <p style="font-size: 14px; color: #888; margin: 0;">부가세 별도</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 택배사업자
    st.markdown("""
    <div style="border: 1px solid #ccc; padding: 20px; margin-bottom: 12px;">
        <p style="font-size: 14px; font-weight: 500; color: #000; margin: 0 0 8px 0;">택배사업자</p>
        <p style="font-size: 14px; color: #333; margin: 0 0 4px 0;">월 <b>30,000원</b></p>
        <p style="font-size: 14px; color: #888; margin: 0;">부가세 별도</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 농어민
    st.markdown("""
    <div style="border: 1px solid #ccc; padding: 20px; margin-bottom: 12px;">
        <p style="font-size: 14px; font-weight: 500; color: #000; margin: 0 0 8px 0;">농어민</p>
        <p style="font-size: 14px; color: #333; margin: 0 0 4px 0;">월 <b>30,000원</b></p>
        <p style="font-size: 14px; color: #888; margin: 0;">부가세 포함</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 기업고객
    st.markdown("""
    <div style="border: 1px solid #ccc; padding: 20px; margin-bottom: 12px;">
        <p style="font-size: 14px; font-weight: 500; color: #000; margin: 0 0 8px 0;">기업고객</p>
        <p style="font-size: 14px; color: #333; margin: 0;">상담요망</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
    st.markdown("""
    <p style="font-size: 14px; color: #888; line-height: 1.6;">
    · 신규 가입 시 첫 달 무료 체험<br>
    · 해지 수수료 없음<br>
    · 카드/계좌이체 결제 가능
    </p>
    """, unsafe_allow_html=True)

# ==========================================
# 📋 이용 안내
# ==========================================
elif menu == "이용 안내":
    st.markdown("""
    <div style="text-align: center; padding: 24px 16px; margin-bottom: 16px;">
        <p style="font-size: 16px; font-weight: 600; color: #000; margin: 0 0 4px 0;">이용 안내</p>
        <p style="font-size: 14px; color: #888; margin: 0;">서비스 사용 방법</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
**동네비서**  
AI 기술로 24시간 운영되는 스마트 매장 관리 시스템

---

**매장 예약/주문**  
· 식당, 카페, 미용실 등 다양한 매장 예약  
· 실시간 테이블 현황 확인  
· 간편한 주문 및 결제

**택배 접수**  
· 로젠택배 연동 간편 접수  
· 대량 발송 엑셀 업로드  
· 배송 추적

---

**사장님 혜택**  
· 첫 달 무료 체험  
· 24시간 AI 자동 응대  
· 간편한 메뉴 관리  
· 실시간 주문 알림  
· 매출 통계 분석

가입: 사이드바 '사장님 가입'
    """)


# ==========================================
# 🆕 사장님 가입 (카테고리 선택 → 가입)
# ==========================================
elif menu == "사장님 가입":
    
    # 세션 상태 초기화
    if "signup_step" not in st.session_state:
        st.session_state.signup_step = 1
    if "signup_main_category" not in st.session_state:
        st.session_state.signup_main_category = None
    if "signup_sub_category" not in st.session_state:
        st.session_state.signup_sub_category = None
    if "signup_store_name" not in st.session_state:
        st.session_state.signup_store_name = ""
    
    st.markdown("""
    <div style="text-align: center; padding: 24px 16px; margin-bottom: 16px;">
        <p style="font-size: 16px; font-weight: 600; color: #000; margin: 0 0 4px 0;">신규 가맹점 가입</p>
        <p style="font-size: 14px; color: #888; margin: 0;">간단한 정보 입력으로 시작하세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    progress_cols = st.columns(4)
    steps = ["1️⃣ 업종 선택", "2️⃣ 세부 카테고리", "3️⃣ 기본 정보", "4️⃣ 가입 완료"]
    for i, (col, step) in enumerate(zip(progress_cols, steps)):
        with col:
            if st.session_state.signup_step > i + 1:
                st.success(step)
            elif st.session_state.signup_step == i + 1:
                st.info(step)
            else:
                st.markdown(f"<div style='color: #aaa; text-align: center;'>{step}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==========================================
    # STEP 1: 대분류 업종 선택
    # ==========================================
    if st.session_state.signup_step == 1:
        st.markdown("### 🏢 어떤 업종의 매장인가요?")
        st.info("💡 업종을 선택하면 맞춤형 서비스를 제공해드립니다!")
        
        # 카테고리 카드 UI
        st.markdown("""
        <style>
        .category-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
            padding: 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-bottom: 1rem;
        }
        .category-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        .category-icon {
            font-size: 3rem;
            margin-bottom: 0.5rem;
        }
        .category-name {
            font-size: 1.2rem;
            font-weight: bold;
            color: #333;
        }
        .category-desc {
            font-size: 0.9rem;
            color: #666;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 2열 레이아웃으로 카테고리 표시
        cat_items = list(BUSINESS_CATEGORIES.items())
        cols = st.columns(2)
        
        for idx, (cat_key, cat_info) in enumerate(cat_items):
            with cols[idx % 2]:
                icon = cat_info['name'].split()[0]  # 이모지 추출
                name = cat_info['name']
                desc = cat_info['description']
                
                if st.button(
                    f"{name}\n{desc}",
                    key=f"cat_{cat_key}",
                    use_container_width=True
                ):
                    st.session_state.signup_main_category = cat_key
                    st.session_state.signup_step = 2
                    st.rerun()
    
    # ==========================================
    # STEP 2: 세부 카테고리 선택
    # ==========================================
    elif st.session_state.signup_step == 2:
        main_cat = st.session_state.signup_main_category
        main_cat_info = BUSINESS_CATEGORIES.get(main_cat, {})
        
        st.markdown(f"### {main_cat_info.get('name', '')} - 세부 카테고리 선택")
        
        # 업종별 세부 카테고리
        if main_cat == 'restaurant':
            subcategories = RESTAURANT_SUBCATEGORIES
            st.info("🍽️ 어떤 종류의 음식점인가요?")
        elif main_cat == 'delivery':
            subcategories = DELIVERY_SUBCATEGORIES
            st.info("📦 어떤 배송 서비스를 제공하나요?")
        elif main_cat == 'laundry':
            subcategories = LAUNDRY_SUBCATEGORIES
            st.info("👔 어떤 세탁 서비스를 제공하나요?")
        elif main_cat == 'retail':
            subcategories = RETAIL_SUBCATEGORIES
            st.info("🛒 어떤 상품을 판매하나요?")
        else:
            # 세부 카테고리가 없는 업종은 바로 3단계로
            subcategories = None
            st.session_state.signup_sub_category = 'general'
            st.session_state.signup_step = 3
            st.rerun()
        
        if subcategories:
            # 3열 레이아웃
            sub_items = list(subcategories.items())
            cols = st.columns(3)
            
            for idx, (sub_key, sub_info) in enumerate(sub_items):
                with cols[idx % 3]:
                    if st.button(
                        f"{sub_info['icon']} {sub_info['name']}\n({sub_info['examples']})",
                        key=f"sub_{sub_key}",
                        use_container_width=True
                    ):
                        st.session_state.signup_sub_category = sub_key
                        st.session_state.signup_step = 3
                        st.rerun()
        
        st.markdown("---")
        if st.button("⬅️ 이전 단계로"):
            st.session_state.signup_step = 1
            st.session_state.signup_main_category = None
            st.rerun()
    
    # ==========================================
    # STEP 3: 기본 정보 입력
    # ==========================================
    elif st.session_state.signup_step == 3:
        main_cat = st.session_state.signup_main_category
        sub_cat = st.session_state.signup_sub_category
        main_cat_info = BUSINESS_CATEGORIES.get(main_cat, {})
        
        # 세부 카테고리 정보 가져오기
        if main_cat == 'restaurant':
            sub_info = RESTAURANT_SUBCATEGORIES.get(sub_cat, {})
        elif main_cat == 'delivery':
            sub_info = DELIVERY_SUBCATEGORIES.get(sub_cat, {})
        elif main_cat == 'laundry':
            sub_info = LAUNDRY_SUBCATEGORIES.get(sub_cat, {})
        elif main_cat == 'retail':
            sub_info = RETAIL_SUBCATEGORIES.get(sub_cat, {})
        else:
            sub_info = {'name': '일반', 'icon': '📋'}
        
        st.markdown("### 📋 기본 정보 입력")
        
        # 선택된 카테고리 표시
        st.success(f"""
        **선택된 업종:** {main_cat_info.get('name', '')}
        
        **세부 카테고리:** {sub_info.get('name', '일반')}
        """)
        
        with st.form("signup_form"):
            st.markdown("#### 🏪 매장 정보")
            
            store_name = st.text_input(
                "상호명 (매장 이름) *",
                placeholder="예: 맛있는 치킨, 행복한 세탁소",
                value=st.session_state.signup_store_name
            )
            
            col1, col2 = st.columns(2)
            with col1:
                store_id = st.text_input(
                    "아이디 (영문/숫자) *",
                    placeholder="로그인 시 사용할 아이디"
                )
                password = st.text_input(
                    f"비밀번호 (최소 {MIN_PASSWORD_LENGTH}자) *",
                    type="password",
                    placeholder="10자 이상"
                )
            
            with col2:
                password_confirm = st.text_input(
                    "비밀번호 확인 *",
                    type="password"
                )
                phone = st.text_input(
                    "연락처 *",
                    placeholder="01012345678"
                )
            
            business_info = st.text_input(
                "영업 정보",
                placeholder="예: 매일 10:00 ~ 22:00, 일요일 휴무"
            )
            
            st.markdown("---")
            st.caption("📌 메뉴/서비스 목록은 가입 완료 후 관리자 페이지에서 등록할 수 있습니다.")
            
            submitted = st.form_submit_button("🎉 가입하기", use_container_width=True, type="primary")
            
            if submitted:
                # 유효성 검사
                if not store_name.strip():
                    st.error("❌ 상호명을 입력해주세요!")
                elif not store_id.strip():
                    st.error("❌ 아이디를 입력해주세요!")
                elif not password:
                    st.error("❌ 비밀번호를 입력해주세요!")
                elif password != password_confirm:
                    st.error("❌ 비밀번호가 일치하지 않습니다!")
                elif not phone.strip():
                    st.error("❌ 연락처를 입력해주세요!")
                else:
                    pw_valid, pw_msg = validate_password_length(password)
                    if not pw_valid:
                        st.error(f"❌ {pw_msg}")
                    else:
                        existing_stores = get_all_stores()
                        if store_id in existing_stores:
                            st.error("❌ 이미 사용 중인 아이디입니다!")
                        else:
                            from datetime import datetime, timedelta
                            
                            free_trial_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                            
                            # 카테고리 조합 (main_sub 형식)
                            full_category = f"{main_cat}_{sub_cat}" if sub_cat else main_cat
                            
                            store_data = {
                                'password': password,
                                'name': store_name.strip(),
                                'phone': phone.strip(),
                                'info': business_info,
                                'menu_text': '',
                                'printer_ip': '',
                                'img_files': '',
                                'status': '미납',
                                'billing_key': '',
                                'expiry_date': free_trial_expiry,
                                'payment_status': '무료체험',
                                'next_payment_date': '',
                                'category': full_category
                            }
                            
                            if save_store(store_id, store_data):
                                st.session_state.signup_step = 4
                                st.session_state.signup_store_id = store_id
                                st.session_state.signup_store_name = store_name.strip()
                                st.session_state.signup_expiry = free_trial_expiry
                                st.rerun()
                            else:
                                st.error("❌ 가입에 실패했습니다. 다시 시도해주세요.")
        
        if st.button("⬅️ 이전 단계로"):
            st.session_state.signup_step = 2
            st.rerun()
    
    # ==========================================
    # STEP 4: 가입 완료
    # ==========================================
    elif st.session_state.signup_step == 4:
        from toss_payments import issue_billing_key_with_card, get_bank_transfer_info
        from db_manager import update_billing_info
        
        main_cat = st.session_state.signup_main_category
        main_cat_info = BUSINESS_CATEGORIES.get(main_cat, {})
        store_id = st.session_state.get('signup_store_id', '')
        
        st.markdown("""
        <div style="text-align: center; padding: 24px 16px; margin-bottom: 16px;">
            <p style="font-size: 16px; font-weight: 600; color: #000; margin: 0 0 4px 0;">가입 완료</p>
            <p style="font-size: 14px; color: #888; margin: 0;">30일 무료 체험이 시작되었습니다</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="border: 1px solid #ccc; padding: 20px; margin-bottom: 16px;">
            <p style="font-size: 14px; margin: 0 0 8px 0;"><b>{st.session_state.signup_store_name}</b></p>
            <p style="font-size: 14px; color: #666; margin: 0;">아이디: {store_id}</p>
            <p style="font-size: 14px; color: #666; margin: 0;">만료일: {st.session_state.get('signup_expiry', '')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 결제 수단 등록 (선택)
        st.markdown("**결제 수단 등록** (무료 체험 후 자동 결제)")
        
        payment_tab1, payment_tab2 = st.tabs(["카드 등록", "무통장 입금"])
        
        with payment_tab1:
            if "card_registered" not in st.session_state:
                st.session_state.card_registered = False
            
            if st.session_state.card_registered:
                st.success("카드가 등록되었습니다.")
            else:
                with st.form("card_form"):
                    card_number = st.text_input("카드 번호", placeholder="0000-0000-0000-0000")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        expiry = st.text_input("유효기간 (MM/YY)", placeholder="01/28")
                    with col2:
                        card_pw = st.text_input("비밀번호 앞 2자리", type="password", max_chars=2)
                    
                    id_number = st.text_input("생년월일 6자리 또는 사업자번호 10자리", placeholder="990101")
                    
                    if st.form_submit_button("카드 등록", use_container_width=True):
                        if card_number and expiry and card_pw and id_number:
                            # 유효기간 파싱
                            try:
                                exp_parts = expiry.replace(" ", "").split("/")
                                exp_month = exp_parts[0]
                                exp_year = exp_parts[1]
                                
                                result, error = issue_billing_key_with_card(
                                    customer_key=store_id,
                                    card_number=card_number,
                                    expiry_year=exp_year,
                                    expiry_month=exp_month,
                                    card_password=card_pw,
                                    id_number=id_number
                                )
                                
                                if result:
                                    from toss_payments import calculate_next_payment_date, calculate_expiry_date
                                    update_billing_info(
                                        store_id,
                                        result['billing_key'],
                                        calculate_expiry_date(30),
                                        "등록완료",
                                        calculate_next_payment_date(30)
                                    )
                                    st.session_state.card_registered = True
                                    st.success("카드가 등록되었습니다.")
                                    st.rerun()
                                else:
                                    st.error(f"등록 실패: {error}")
                            except Exception as e:
                                st.error(f"유효기간 형식 오류: MM/YY 형식으로 입력하세요")
                        else:
                            st.error("모든 정보를 입력해주세요.")
        
        with payment_tab2:
            bank_info = get_bank_transfer_info()
            st.markdown(f"""
            <div style="border: 1px solid #ccc; padding: 16px;">
                <p style="font-size: 14px; margin: 0 0 8px 0;"><b>{bank_info['bank_name']}</b></p>
                <p style="font-size: 14px; color: #333; margin: 0 0 4px 0;">{bank_info['account_number']}</p>
                <p style="font-size: 14px; color: #666; margin: 0 0 8px 0;">예금주: {bank_info['account_holder']}</p>
                <p style="font-size: 14px; color: #888; margin: 0;">{bank_info['note']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 관리 페이지 안내
        with st.expander("관리 페이지 안내"):
            st.markdown(f"""
아이디: **{store_id}**  
비밀번호: 가입 시 설정한 비밀번호

관리 페이지에서 메뉴 등록, QR코드 생성, 주문 관리를 할 수 있습니다.
            """)
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("처음으로", use_container_width=True):
                for key in ['signup_step', 'signup_main_category', 'signup_sub_category', 
                           'signup_store_name', 'signup_store_id', 'signup_expiry', 'card_registered']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        with col2:
            if st.button("다른 매장 등록", use_container_width=True):
                for key in ['signup_step', 'signup_main_category', 'signup_sub_category', 
                           'signup_store_name', 'signup_store_id', 'signup_expiry', 'card_registered']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.signup_step = 1
                st.rerun()
        
        # 관리 페이지 바로가기
        st.markdown("")
        st.markdown("""
        <div style="text-align: center; margin-top: 1rem;">
            <p style="color: #666; margin-bottom: 0.5rem;">준비가 되셨나요?</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 실제 admin 페이지 URL (같은 서버에서 다른 포트로 실행 중인 경우)
        st.link_button(
            "🚀 사장님 관리 페이지 바로가기",
            "http://localhost:8502",
            use_container_width=True,
            type="primary"
        )


# ==========================================
# 🏠 매장 입장 (고객용 - 기존 매장 이용)
# ==========================================
elif menu == "🏠 매장 입장":
    
    # 세션 상태 초기화
    if "store_id" not in st.session_state:
        st.session_state.store_id = None
    if "order_complete" not in st.session_state:
        st.session_state.order_complete = False
    
    # 주문 완료 화면
    if st.session_state.order_complete:
        st.markdown("## 🎉 주문이 완료되었습니다!")
        
        order_info = st.session_state.get('last_order', {})
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.success(f"""
            ### 주문번호: {order_info.get('order_id', 'N/A')}
            
            **{order_info.get('store_name', '')}** 에서 맛있게 준비하겠습니다!
            
            📞 문의: {order_info.get('store_phone', '')}
            """)
            
            if st.button("🏠 처음으로 돌아가기", use_container_width=True):
                st.session_state.order_complete = False
                st.session_state.store_id = None
                st.rerun()
        
        st.stop()
    
    # 매장 선택 안됨 - 로그인 화면
    if st.session_state.store_id is None:
        st.markdown("## 🔑 매장 선택")
        
        # 데이터베이스에서 가게 목록 로드
        try:
            stores = get_all_stores()
        except Exception as e:
            st.error(f"❌ 가게 목록을 불러올 수 없습니다: {e}")
            st.info("💡 네트워크 연결을 확인하고 새로고침 해주세요.")
            stores = {}
        
        if not stores:
            st.warning("📭 등록된 가게가 없습니다.")
            st.info("사장님이시라면 '📝 가게 등록' 메뉴에서 가게를 등록해주세요!")
        else:
            # 가게 목록 표시
            st.markdown("### 🏪 가게를 선택하세요")
            
            cols = st.columns(2)
            for idx, (store_id, store_info) in enumerate(stores.items()):
                if store_id.strip():  # 빈 아이디 제외
                    with cols[idx % 2]:
                        with st.container():
                            # 업종 아이콘 가져오기
                            store_category = store_info.get('category', 'restaurant')
                            category_info = BUSINESS_CATEGORIES.get(store_category, BUSINESS_CATEGORIES['other'])
                            category_name = category_info['name']
                            
                            st.markdown(f"""
                            **🏪 {store_info.get('name', store_id)}**
                            
                            {category_name}
                            
                            📞 {store_info.get('phone', '-')}
                            
                            ⏰ {store_info.get('info', '-')}
                            """)
                            
                            if st.button(f"입장하기", key=f"enter_{store_id}", use_container_width=True):
                                st.session_state.store_id = store_id
                                st.rerun()
                        
                        st.markdown("---")
    
    # 매장 선택됨 - 주문 화면
    else:
        store_id = st.session_state.store_id
        store = get_store(store_id)
        
        if store is None:
            st.error("❌ 가게 정보를 불러올 수 없습니다.")
            if st.button("🔙 돌아가기"):
                st.session_state.store_id = None
                st.rerun()
            st.stop()
        
        # 가게 헤더
        st.markdown(f"## 🏠 {store.get('name', store_id)}")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info(f"⏰ {store.get('info', '')} | 📞 {store.get('phone', '')}")
        with col2:
            if st.button("🔙 다른 가게 선택"):
                st.session_state.store_id = None
                st.session_state.messages = []
                st.rerun()
        
        st.divider()
        
        # 메뉴판
        with st.expander("📋 메뉴판 보기", expanded=True):
            menu_text = store.get('menu_text', '메뉴 정보가 없습니다.')
            st.text(menu_text)
        
        st.divider()
        
        # ==========================================
        # 📦 업종별 주문/예약 폼
        # ==========================================
        store_category = store.get('category', 'restaurant')
        
        # 업종별 폼 렌더링
        if store_category == 'restaurant':
            render_restaurant_form(store, store_id)
        elif store_category == 'delivery':
            render_delivery_form(store, store_id)
        elif store_category == 'laundry':
            render_laundry_form(store, store_id)
        elif store_category == 'retail':
            render_retail_form(store, store_id)
        else:
            render_general_form(store, store_id)
        
        st.divider()
        
        # ==========================================
        # 💬 AI 챗봇 (고객 기억 기능 포함)
        # ==========================================
        if model:
            from customer_memory import (
                CustomerContext, get_personalized_greeting,
                update_customer_from_conversation, get_ai_system_prompt_with_customer,
                normalize_phone, increment_customer_order
            )
            from db_manager import get_customer, save_customer
            
            st.markdown("### 💬 AI 주문 도우미")
            
            # 고객 컨텍스트 초기화
            if "customer_context" not in st.session_state:
                st.session_state.customer_context = CustomerContext(store_id, store.get('name', ''))
            
            # 전화번호 입력 (고객 식별용)
            if "customer_phone" not in st.session_state:
                st.session_state.customer_phone = ""
            if "customer_identified" not in st.session_state:
                st.session_state.customer_identified = False
            
            # 고객 식별 단계
            if not st.session_state.customer_identified:
                st.info("📱 전화번호를 입력하시면 맞춤 서비스를 받으실 수 있어요!")
                
                col_phone, col_btn = st.columns([3, 1])
                with col_phone:
                    phone_input = st.text_input(
                        "전화번호",
                        placeholder="010-1234-5678",
                        key="phone_input_chat",
                        label_visibility="collapsed"
                    )
                with col_btn:
                    if st.button("확인", key="phone_confirm", use_container_width=True):
                        if phone_input:
                            st.session_state.customer_phone = normalize_phone(phone_input)
                            st.session_state.customer_context.set_customer(st.session_state.customer_phone)
                            st.session_state.customer_identified = True
                            
                            # 기존 고객 확인 및 환영 메시지
                            greeting, customer = get_personalized_greeting(
                                st.session_state.customer_phone, 
                                store_id, 
                                store.get('name', '')
                            )
                            
                            if greeting:
                                # 기존 고객 - 개인화된 인사
                                st.session_state.messages = [
                                    {"role": "assistant", "content": greeting}
                                ]
                            else:
                                # 신규 고객 - 기본 인사 + 정보 저장
                                save_customer({
                                    'customer_id': st.session_state.customer_phone,
                                    'store_id': store_id,
                                    'phone': st.session_state.customer_phone
                                })
                                st.session_state.messages = [
                                    {"role": "assistant", "content": "처음 오셨군요! 환영합니다! 🎉\n성함을 알려주시면 다음에 더 편하게 주문하실 수 있어요!"}
                                ]
                            
                            st.rerun()
                        else:
                            st.warning("전화번호를 입력해주세요")
                
                # 건너뛰기 옵션
                if st.button("그냥 주문할게요", key="skip_phone"):
                    st.session_state.customer_identified = True
                    st.session_state.messages = [
                        {"role": "assistant", "content": "어서오세요! 주문 도와드릴까요? 🙋"}
                    ]
                    st.rerun()
            
            else:
                # 고객 정보 표시 (있으면)
                customer_info = st.session_state.customer_context.customer_info
                if customer_info and customer_info.get('name'):
                    st.caption(f"👤 {customer_info.get('name')}님 | 📞 {st.session_state.customer_phone}")
                elif st.session_state.customer_phone:
                    st.caption(f"📞 {st.session_state.customer_phone}")
                
                st.caption("메뉴나 주문에 대해 물어보세요! AI가 당신의 취향을 기억해요 🧠")
                
                # 메시지 초기화
                if "messages" not in st.session_state:
                    st.session_state.messages = [
                        {"role": "assistant", "content": "어서오세요! 주문 도와드릴까요? 🙋"}
                    ]
                
                # 메시지 표시
                for msg in st.session_state.messages:
                    st.chat_message(msg["role"]).write(msg["content"])
                
                # 채팅 입력
                if prompt := st.chat_input("메뉴 추천해줘, 이거 맛있어? 등"):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.chat_message("user").write(prompt)
                    
                    # 대화에서 고객 정보 추출 및 저장
                    if st.session_state.customer_phone:
                        st.session_state.customer_context.add_message("user", prompt, model)
                    
                    try:
                        # 고객 정보를 포함한 AI 프롬프트 생성
                        customer_summary = st.session_state.customer_context.get_context_summary()
                        
                        full_prompt = f"""당신은 '{store.get('name', '')}'의 친절한 AI 주문 도우미입니다.

[가게 정보]
메뉴: {store.get('menu_text', '')}

{customer_summary}

[대화 지침]
1. 고객의 취향과 이전 정보를 기억하고 활용하세요
2. 고객이 이름, 주소, 취향 등을 알려주면 "기억해둘게요!"라고 말해주세요
3. 짧고 친절하게 한국어로 답변하세요
4. 적절히 이모지를 사용해 친근하게 대화하세요

고객 질문: {prompt}"""
                        
                        response = model.generate_content(full_prompt)
                        bot_reply = response.text
                        
                        # 새로 추출된 정보가 있으면 알림
                        if st.session_state.customer_context.extracted_info:
                            new_info = st.session_state.customer_context.extracted_info
                            if new_info.get('name') or new_info.get('address') or new_info.get('preferences'):
                                # 정보가 저장됨 - 이미 bot_reply에 반영됨
                                pass
                        
                    except Exception as e:
                        bot_reply = "죄송합니다. 잠시 후 다시 시도해주세요. 🙏"
                    
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    st.chat_message("assistant").write(bot_reply)
                
                # 대화 초기화 버튼
                with st.expander("🔧 대화 관리"):
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 대화 초기화", use_container_width=True):
                            st.session_state.messages = [
                                {"role": "assistant", "content": "새로운 대화를 시작합니다! 무엇을 도와드릴까요? 🙋"}
                            ]
                            st.rerun()
                    with col2:
                        if st.button("👤 다른 고객", use_container_width=True):
                            st.session_state.customer_identified = False
                            st.session_state.customer_phone = ""
                            st.session_state.customer_context = CustomerContext(store_id, store.get('name', ''))
                            st.session_state.messages = []
                            st.rerun()
                    
                    # 고객 정보 확인
                    if customer_info:
                        st.markdown("---")
                        st.markdown("**🧠 기억된 정보:**")
                        if customer_info.get('name'):
                            st.markdown(f"- 이름: {customer_info['name']}")
                        if customer_info.get('address'):
                            st.markdown(f"- 주소: {customer_info['address']}")
                        if customer_info.get('preferences'):
                            st.markdown(f"- 취향: {customer_info['preferences']}")
                        if customer_info.get('total_orders', 0) > 0:
                            st.markdown(f"- 총 주문: {customer_info['total_orders']}회")


# ==========================================
# 📌 푸터
# ==========================================
st.markdown("---")
st.markdown("""
<div style="
    text-align: center;
    padding: 20px 0;
    color: #64748b;
    font-size: 0.85rem;
">
    <p style="margin: 0 0 5px 0; font-weight: 500;">🏘️ 동네비서</p>
    <p style="margin: 0; font-size: 0.75rem; color: #475569;">기억하고, 연결하며, 24시간 함께합니다.</p>
</div>
""", unsafe_allow_html=True)
