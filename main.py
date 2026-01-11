import streamlit as st

# 1. 디자인 설정 (배경 제거, 개별 색상 카드)
st.markdown("""
    <style>
    /* 전체 배경: 아주 진한 다크 그레이로 눈의 피로 최소화 */
    .stApp {
        background-color: #121212 !important;
    }

    /* 그리드 컨테이너 (2열 고정) */
    .menu-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        padding: 15px;
    }

    /* 기본 카드 공통 스타일 */
    .menu-item {
        border-radius: 15px;
        aspect-ratio: 1.3 / 1; /* 터치하기 좋은 직사각형 */
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 10px;
        text-decoration: none;
        transition: transform 0.1s ease;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }

    /* 터치 시 눌리는 효과 */
    .menu-item:active {
        transform: scale(0.92);
        filter: brightness(1.2);
    }

    /* 카드 내 텍스트 스타일 */
    .menu-text {
        color: white !important;
        font-size: 19px;
        font-weight: 800;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }

    /* 상단 불필요한 여백 완전 제거 */
    .block-container { padding: 1rem !important; }
    header { visibility: hidden; }
    
    /* 스트림릿 기본 요소 제거 */
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. 메뉴 데이터 (총 10장의 카드로 구성)
menus = [
    {"title": "매장 예약", "color": "#E11E5A"}, # 장미빛
    {"title": "택배 접수", "color": "#2E7D32"}, # 초록
    {"title": "경영 분석", "color": "#1565C0"}, # 파랑
    {"title": "고객 게시판", "color": "#EF6C00"}, # 오렌지
    {"title": "가맹 가입", "color": "#6A1B9A"}, # 보라
    {"title": "관리자 모드", "color": "#455A64"}, # 회색
    {"title": "정산 내역", "color": "#00838F"}, # 청록
    {"title": "사용 방법", "color": "#AD1457"}, # 진분홍
    {"title": "공지 사항", "color": "#F9A825"}, # 황금색
    {"title": "서비스 안내", "color": "#37474F"}  # 어두운 청회색
]

# 3. 레이아웃 출력
st.markdown('<div class="menu-grid">', unsafe_allow_html=True)

for m in menus:
    st.markdown(f'''
        <a href="#" class="menu-item" style="background-color: {m['color']};">
            <div class="menu-text">{m['title']}</div>
        </a>
    ''', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
