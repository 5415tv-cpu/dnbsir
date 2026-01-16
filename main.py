import streamlit as st
import textwrap
from datetime import datetime
import pwa_helper
import printer_manager
import db_manager
import logen_delivery
import address_helper
import sms_manager
import qrcode
import io
import pandas as pd
from PIL import Image
import ai_manager
import streamlit.components.v1 as components
import time
import json
import requests
from uuid import uuid4
from urllib.parse import urlencode

# ==========================================
# 💎 동네비서 PREMIUM KIOSK - v2.2.0 (Sales Optimized)
# ==========================================
BUILD_VERSION = "20260116_SALES_PRO"

# 1. 페이지 초기 설정 (Streamlit 규칙: 첫 호출이어야 함)
st.set_page_config(page_title="동네비서 Premium", layout="centered")

# 🎨 글로벌 스타일 주입 (Transparent Glass + Bold Black Text)
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 1. 전체 배경: 은은한 라이트 톤 */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"], .main {
        background: radial-gradient(circle at top, #FFFFFF 0%, #F4F7FF 55%, #EEF2FA 100%) !important;
        font-family: 'Pretendard', sans-serif !important;
    }

    /* 2. 모든 텍스트 강제 검정색 고정 및 굵게 */
    div, p, span, label, h1, h2, h3, h4, h5, h6, .stMarkdown p, .stText p, a {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        font-weight: 900 !important;
    }
    
    /* 2-1. 어두운 버튼/배지용 흰색 텍스트 */
    .force-white, .force-white * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    /* 3. 투명 유리 카드 스타일 */
    .glass-container {
        background: rgba(255, 255, 255, 0.55) !important;
        backdrop-filter: blur(24px) saturate(180%);
        -webkit-backdrop-filter: blur(24px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.8);
        border-radius: 30px;
        padding: 22px 26px;
        margin-bottom: 18px;
        box-shadow: 0 18px 38px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.7);
    }

    .glass-card {
        background: rgba(255, 255, 255, 0.55) !important;
        backdrop-filter: blur(26px) saturate(180%);
        -webkit-backdrop-filter: blur(26px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.9);
        border-radius: 32px;
        padding: 28px 32px;
        box-shadow: 0 22px 44px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.75);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        display: block;
        text-decoration: none;
        margin-bottom: 15px;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.62) !important;
        box-shadow: 0 26px 52px rgba(0, 0, 0, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.85);
    }
    
    .glass-card:active {
        animation: card-bounce 0.25s ease-out;
    }

    .membership-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        min-height: 86px;
    }

    .membership-badges {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    .level-badge {
        background: rgba(0, 0, 0, 0.85);
        color: #FFFFFF !important;
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 12px;
        font-weight: 900;
    }

    .level-badge.premium {
        background: #7B2CF4;
        color: #FFFFFF !important;
    }
    
    .kakao-btn {
        background: #FEE500;
        color: #1E1E1E !important;
        padding: 10px 16px;
        border-radius: 50px;
        font-weight: 900;
        font-size: 13px;
        border: 1px solid rgba(0, 0, 0, 0.08);
        box-shadow: 0 8px 20px rgba(0,0,0,0.12);
    }

    .core-cards {
        margin: 10px auto 26px;
        max-width: 880px;
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .core-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        min-height: 150px;
        width: 100%;
        border: 1px solid rgba(255, 255, 255, 0.85);
    }

    .core-card .core-title {
        font-size: 28px;
        font-weight: 900;
        color: #000000;
        margin-bottom: 8px;
        letter-spacing: -0.5px;
    }

    .core-card .core-desc {
        font-size: 15px;
        font-weight: 900;
        color: #000000;
        line-height: 1.45;
    }

    .core-icon {
        font-size: 58px;
        flex-shrink: 0;
    }

    /* 4. 입력창 스타일 */
    input, textarea, [data-baseweb="input"], [data-baseweb="textarea"] {
        background-color: rgba(255, 255, 255, 0.9) !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 12px !important;
    }

    /* 5. 버튼 스타일 */
    .stButton button, [data-testid="stForm"] button {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 50px !important;
        font-weight: 900 !important;
        border: none !important;
        padding: 12px 25px !important;
        font-size: 16px !important;
    }
    
    .stButton button *, [data-testid="stForm"] button * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    .stButton button svg, [data-testid="stForm"] button svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }
    
    /* 6. Streamlit 기본 UI 제거 */
    header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {
        display: none !important;
    }

    /* 7. 하단 아이콘 그리드 (컬러 카드 + 튀어나오는 터치 효과) */
    .icon-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 14px;
        padding: 10px 0;
    }
    
    .icon-item {
        border-radius: 16px;
        padding: 18px 12px;
        min-height: 96px;
        text-align: left;
        text-decoration: none;
        border: 1px solid rgba(255, 255, 255, 0.75);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.12);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        display: flex;
        align-items: center;
        gap: 12px;
        will-change: transform;
    }
    
    .icon-item:active {
        animation: card-bounce 0.25s ease-out;
        transform: translateY(-6px) scale(1.03);
        box-shadow: 0 16px 30px rgba(0, 0, 0, 0.18);
    }
    
    .icon-emoji { font-size: 28px; }
    .icon-text { font-size: 15px; font-weight: 900; color: #FFFFFF; }
    
    @keyframes card-bounce {
        0% { transform: translateY(0) scale(1); }
        55% { transform: translateY(-10px) scale(1.04); }
        100% { transform: translateY(-4px) scale(1.02); }
    }
</style>
""", unsafe_allow_html=True)

# PWA 메타 주입
pwa_helper.inject_pwa_tags()

# 📌 모바일 캐시 갱신 (빌드 버전 변경 시 강제 새로고침)
def inject_cache_bust(build_version: str):
    components.html(f"""
    <script>
    (function() {{
        const v = "{build_version}";
        const k = "dnbs_build_version";
        const prev = localStorage.getItem(k);
        if (prev && prev !== v) {{
            if ('caches' in window) {{
                caches.keys().then(keys => Promise.all(keys.map(key => caches.delete(key))));
            }}
            if (navigator.serviceWorker) {{
                navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(r => r.unregister()));
            }}
            setTimeout(() => location.reload(), 150);
        }}
        localStorage.setItem(k, v);
    }})();
    </script>
    """, height=0, scrolling=False)

def inject_manifest(build_version: str):
    components.html(f"""
    <script>
    (function() {{
        const href = "/manifest.json?v={build_version}";
        let link = document.querySelector('link[rel="manifest"]');
        if (!link) {{
            link = document.createElement('link');
            link.rel = 'manifest';
            document.head.appendChild(link);
        }}
        link.href = href;
    }})();
    </script>
    """, height=0, scrolling=False)

inject_manifest(BUILD_VERSION)
inject_cache_bust(BUILD_VERSION)

# =========================
# Kakao Login Helpers
# =========================
def get_kakao_auth_url():
    rest_key = st.secrets.get("KAKAO_REST_API_KEY", "")
    redirect_uri = st.secrets.get("KAKAO_REDIRECT_URI", "")
    if not rest_key or not redirect_uri:
        return None
    params = {
        "client_id": rest_key,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "profile_nickname account_email phone_number",
        "state": "dnbs"
    }
    return f"https://kauth.kakao.com/oauth/authorize?{urlencode(params)}"


def normalize_kakao_phone(phone_raw: str) -> str:
    if not phone_raw:
        return ""
    digits = "".join([c for c in phone_raw if c.isdigit()])
    if digits.startswith("82"):
        digits = "0" + digits[2:]
    return digits


def handle_kakao_callback():
    if "code" not in st.query_params:
        return
    if st.query_params.get("state") != "dnbs":
        return
    if st.session_state.get("kakao_processing"):
        return
    st.session_state.kakao_processing = True

    code = st.query_params.get("code")
    rest_key = st.secrets.get("KAKAO_REST_API_KEY", "")
    redirect_uri = st.secrets.get("KAKAO_REDIRECT_URI", "")
    if not rest_key or not redirect_uri:
        st.error("카카오 로그인 설정이 없습니다. 관리자에게 문의하세요.")
        return

    try:
        token_res = requests.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": rest_key,
                "redirect_uri": redirect_uri,
                "code": code
            },
            timeout=10
        )
        if token_res.status_code != 200:
            st.error("카카오 로그인에 실패했습니다. 다시 시도해주세요.")
            return

        access_token = token_res.json().get("access_token")
        if not access_token:
            st.error("카카오 토큰이 발급되지 않았습니다.")
            return

        user_res = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if user_res.status_code != 200:
            st.error("카카오 계정 정보를 가져오지 못했습니다.")
            return

        user_data = user_res.json()
        kakao_id = str(user_data.get("id", ""))
        kakao_account = user_data.get("kakao_account", {})
        profile = kakao_account.get("profile", {}) if kakao_account else {}
        nickname = profile.get("nickname") or "카카오 사용자"
        email = kakao_account.get("email", "") if kakao_account else ""
        phone_raw = kakao_account.get("phone_number", "") if kakao_account else ""
        phone = normalize_kakao_phone(phone_raw)

        store_id = f"kakao_{kakao_id}"
        store = db_manager.get_store(store_id)
        if not store:
            store_data = {
                "password": uuid4().hex[:12],
                "name": nickname,
                "owner_name": nickname,
                "phone": phone,
                "info": "카카오 로그인 가입",
                "menu_text": "",
                "category": "other",
                "membership": "일반"
            }
            db_manager.save_store(store_id, store_data, encrypt_password=True)
            store = db_manager.get_store(store_id)

        if store:
            st.session_state.logged_in_store = store
            welcome_msg = "동네비서 AI 가족이 되신 것을 환영합니다! 프리미엄 혜택을 확인해보세요"
            if phone:
                ok, msg = sms_manager.send_alimtalk(phone, welcome_msg)
                if not ok:
                    st.warning(f"알림톡 발송 실패: {msg}")
            else:
                st.info("카카오 계정에 전화번호가 없어 알림톡 발송을 생략했습니다.")
            st.query_params.clear()
            st.session_state.page = "HOME"
            st.rerun()
        else:
            st.error("가입 처리 중 문제가 발생했습니다. 다시 시도해주세요.")
    finally:
        st.session_state.kakao_processing = False


# 🔐 [자동 로그인 시스템]
def handle_persistent_login():
    if st.session_state.get("logout_requested"):
        st.session_state.logout_requested = False
        st.session_state.logged_in_store = None
        st.markdown("""
        <script>
            localStorage.removeItem('dnbs_store_id');
            localStorage.setItem('dnbs_logout', 'true');
            const url = new URL(window.location.href);
            url.searchParams.delete('pl');
            window.location.href = url.origin + url.pathname;
        </script>
        """, unsafe_allow_html=True)
        st.stop()

    if "pl" in st.query_params and st.session_state.get("logged_in_store") is None:
        saved_id = st.query_params["pl"]
        import db_manager
        success = False
        store_info = None
        if saved_id in ["5415tv", "admin777"]:
            if saved_id == "admin777":
                success, msg, store_info = db_manager.verify_master_login(saved_id, "pass777!")
            else:
                master_pw = st.secrets.get("admin", {}).get("password", "Qqss12!!0")
                success, msg, store_info = db_manager.verify_master_login(saved_id, master_pw)
        else:
            store_info = db_manager.get_store(saved_id)
            if store_info: success = True
        
        if success and store_info:
            st.session_state.logged_in_store = store_info
            st.markdown("<script>const url = new URL(window.location.href); url.searchParams.delete('pl'); window.history.replaceState({}, '', url.href);</script>", unsafe_allow_html=True)
            st.rerun()

    if st.session_state.get("logged_in_store") is None:
        st.markdown("""
        <script>
            (function() {
                const savedId = localStorage.getItem('dnbs_store_id');
                const isLogout = localStorage.getItem('dnbs_logout');
                const url = new URL(window.location.href);
                if (savedId && !url.searchParams.has('pl') && isLogout !== 'true') {
                    url.searchParams.set('pl', savedId);
                    window.location.href = url.href;
                }
                if (isLogout === 'true') { setTimeout(() => localStorage.removeItem('dnbs_logout'), 1000); }
            })();
        </script>
        """, unsafe_allow_html=True)

handle_persistent_login()
handle_kakao_callback()
st.markdown(printer_manager.get_bluetooth_printer_js(), unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "HOME"
if "selected_store" not in st.session_state: st.session_state.selected_store = None
if "pending_payment" not in st.session_state: st.session_state.pending_payment = None
if "bt_printer_connected" not in st.session_state: st.session_state.bt_printer_connected = False
if "lock_sender" not in st.session_state: st.session_state.lock_sender = False
if "fixed_sender" not in st.session_state: st.session_state.fixed_sender = {}
if "logged_in_store" not in st.session_state: st.session_state.logged_in_store = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "logout_requested" not in st.session_state: st.session_state.logout_requested = False
if "mgmt_tab_index" not in st.session_state: st.session_state.mgmt_tab_index = 0

if "page" in st.query_params: st.session_state.page = st.query_params["page"]

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

def go_home():
    st.session_state.page = "HOME"
    st.session_state.selected_store = None
    st.session_state.pending_payment = None
    st.query_params.clear()
    st.rerun()

def render_health_check():
    """연결 상태 점검 (쿼리 파라미터로만 노출)"""
    if st.query_params.get("health") != "1":
        return
    st.markdown("### 🔍 연결 상태 점검", unsafe_allow_html=True)
    spreadsheet = db_manager.get_spreadsheet()
    if spreadsheet:
        st.success("✅ Google Sheets 연결 성공")
        try:
            st.info(f"시트 제목: {spreadsheet.title}")
        except Exception:
            st.info("시트 제목 읽기 성공")
    else:
        st.error("❌ Google Sheets 연결 실패")

now = datetime.now()
time_str = now.strftime('%H:%M:%S')
date_str = now.strftime('%Y. %m. %d') + f" ({['월','화','수','목','금','토','일'][now.weekday()]})"

# 🏠 [메인 화면]
if st.session_state.page == "HOME":
    render_health_check()
    # 1. 멤버십 바 구성
    is_logged_in = st.session_state.logged_in_store is not None
    if not is_logged_in:
        kakao_auth_url = get_kakao_auth_url()
        kakao_button_html = ""
        if kakao_auth_url:
            kakao_button_html = f"""
            <a href="{kakao_auth_url}" target="_top" style="text-decoration: none;">
                <div class="kakao-btn">카카오톡으로 시작하기</div>
            </a>
            """
        membership_html = f"""
        <div class="glass-container membership-bar">
            <div>
                <div style="font-size: 16px; font-weight: 900; color: #000000;">지금 가입하고 프리미엄 혜택을 받으세요</div>
                <div style="font-size: 12px; font-weight: 800; color: #000000; opacity: 0.8;">로그인 후 일반/프리미엄 등급이 자동 표시됩니다</div>
            </div>
            <div class="membership-badges">
                <span class="level-badge force-white">일반</span>
                <span class="level-badge premium force-white">프리미엄</span>
                <a href="/?page=JOIN" target="_top" style="text-decoration: none;">
                    <div class="force-white" style="background: #000000; color: white; padding: 10px 18px; border-radius: 50px; font-weight: 900; font-size: 14px;">로그인 / 회원가입</div>
                </a>
                {kakao_button_html}
            </div>
        </div>
        """
    else:
        store = st.session_state.logged_in_store
        level = store.get('membership', '일반')
        level_color = "#9D4EDD" if level == '프리미엄' else "#666666"
        membership_html = f"""
        <div class="glass-container membership-bar">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div class="level-badge force-white {'premium' if level == '프리미엄' else ''}">{level} 멤버십</div>
                <div style="font-size: 18px; font-weight: 900; color: #000000;">{store["name"]} 사장님</div>
            </div>
            <div class="membership-badges">
                <a href="/?page=PREMIUM_ONLY" target="_top" style="text-decoration: none;">
                    <div style="border: 2px solid #000000; color: #000000; padding: 8px 16px; border-radius: 50px; font-weight: 900; font-size: 13px;">혜택 안내</div>
                </a>
            </div>
        </div>
        """

    # 2. 3대 핵심 킬러 카드
    killer_cards_html = f"""
    <div class="core-cards">
        <a href="/?page=DELIVERY" target="_top" class="glass-card core-card" onclick="window.top.location.href='/?page=DELIVERY'; return false;">
            <div>
                <div class="force-white" style="background: #000000; color: white; display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 900; margin-bottom: 10px;">인기 서비스</div>
                <div class="core-title">AI 택배</div>
                <div class="core-desc">택배기사님 필수! 주소 입력 없이 음성으로 송장 즉시 출력</div>
            </div>
            <div class="core-icon">📦</div>
        </a>
        <a href="/?page=AI_CHAT" target="_top" class="glass-card core-card" onclick="window.top.location.href='/?page=AI_CHAT'; return false;">
            <div>
                <div class="force-white" style="background: #000000; color: white; display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 900; margin-bottom: 10px;">AI 자동화</div>
                <div class="core-title">AI 매장비서</div>
                <div class="core-desc">자영업 사장님 필수! 단골 관리부터 예약까지 AI가 24시간 응대</div>
            </div>
            <div class="core-icon">🤖</div>
        </a>
        <a href="/?page=SETTLEMENT" target="_top" class="glass-card core-card" onclick="window.top.location.href='/?page=SETTLEMENT'; return false;">
            <div>
                <div class="force-white" style="background: #000000; color: white; display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 900; margin-bottom: 10px;">정산 센터</div>
                <div class="core-title">실시간 수익</div>
                <div class="core-desc">투명한 정산! 오늘 번 순수익을 실시간으로 확인하세요</div>
            </div>
            <div class="core-icon">💰</div>
        </a>
    </div>
    """

    # 3. 하단 아이콘 버튼 그리드
    bottom_menus = [
        {"title": "매장 예약", "icon": "📅", "target": "RESERVE", "color": "#F4A300"},
        {"title": "매장 관리", "icon": "🛠️", "target": "STORE_MGMT", "color": "#6C5CE7"},
        {"title": "택배 접수", "icon": "📦", "target": "DELIVERY", "color": "#2D3436"},
        {"title": "AI 상담원", "icon": "🤖", "target": "AI_CHAT", "color": "#00B894"},
        {"title": "매출 정산", "icon": "💰", "target": "SETTLEMENT", "color": "#2E86DE"},
        {"title": "결제하기", "icon": "💳", "target": "PAYMENT", "color": "#00A8FF"},
        {"title": "주문 장부", "icon": "📋", "target": "ORDERS", "color": "#E17055"},
        {"title": "가맹 신청", "icon": "🤝", "target": "JOIN", "color": "#D63031"},
        {"title": "공지 사항", "icon": "📢", "target": "NOTICE", "color": "#6C5CE7"},
        {"title": "고객 센터", "icon": "📞", "target": "CONTACT", "color": "#00B894"}
    ]
    
    icon_grid_html = '<div class="icon-grid">'
    for m in bottom_menus:
        icon_grid_html += f'<a href="/?page={m["target"]}" target="_top" class="icon-item" style="background:{m["color"]};" onclick="window.top.location.href=\'/?page={m["target"]}\'; return false;"><div class="icon-emoji">{m["icon"]}</div><div class="icon-text">{m["title"]}</div></a>'
    icon_grid_html += '</div>'

    # 상단 멤버십 바 (iframe 밖에서 렌더링하여 링크 동작 보장)
    st.markdown(membership_html, unsafe_allow_html=True)

    # 전체 레이아웃 결합
    full_ui_html = textwrap.dedent(f"""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        html, body {{
            background: transparent;
            font-family: 'Pretendard', sans-serif !important;
        }}
        a {{ color: #000000; text-decoration: none; }}
        .glass-container {{
            background: rgba(255, 255, 255, 0.55) !important;
            backdrop-filter: blur(24px) saturate(180%);
            -webkit-backdrop-filter: blur(24px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.8);
            border-radius: 30px;
            padding: 22px 26px;
            margin-bottom: 18px;
            box-shadow: 0 18px 38px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.7);
        }}
        .force-white, .force-white * {{
            color: #FFFFFF !important;
        }}
        .glass-card {{
            background: rgba(255, 255, 255, 0.55) !important;
            backdrop-filter: blur(26px) saturate(180%);
            -webkit-backdrop-filter: blur(26px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.9);
            border-radius: 32px;
            padding: 28px 32px;
            box-shadow: 0 22px 44px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.75);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            display: block;
            text-decoration: none;
            margin-bottom: 15px;
        }}
        .glass-card:hover {{
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.62) !important;
            box-shadow: 0 26px 52px rgba(0, 0, 0, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.85);
        }}
        .glass-card:active {{
            animation: card-bounce 0.25s ease-out;
        }}
        .core-card {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            min-height: 150px;
            width: 100%;
            border: 1px solid rgba(255, 255, 255, 0.85);
        }}
        .core-title {{
            font-size: 28px;
            font-weight: 900;
            color: #000000;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}
        .core-desc {{
            font-size: 15px;
            font-weight: 900;
            color: #000000;
            line-height: 1.45;
        }}
        .core-icon {{
            font-size: 58px;
            flex-shrink: 0;
        }}
        .icon-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 14px;
            padding: 10px 0;
        }}
        .icon-item {{
            border-radius: 16px;
            padding: 18px 12px;
            min-height: 96px;
            text-align: left;
            text-decoration: none;
            border: 1px solid rgba(255, 255, 255, 0.9);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.12);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            display: flex;
            align-items: center;
            gap: 12px;
            will-change: transform;
        }}
        .icon-item:active {{
            transform: translateY(-6px) scale(1.03);
            box-shadow: 0 16px 30px rgba(0, 0, 0, 0.18);
            animation: card-bounce 0.25s ease-out;
        }}
        .icon-emoji {{ font-size: 28px; }}
        .icon-text {{ font-size: 15px; font-weight: 900; color: #FFFFFF; }}
        @keyframes card-bounce {{
            0% {{ transform: translateY(0) scale(1); }}
            55% {{ transform: translateY(-10px) scale(1.04); }}
            100% {{ transform: translateY(-4px) scale(1.02); }}
        }}
        .mini-clock {{
            width: 48px;
            height: 48px;
            border: 3px solid #000000;
            border-radius: 50%;
            position: relative;
            background: rgba(255, 255, 255, 0.6);
            box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.12);
        }}
        .mini-clock .hand {{
            position: absolute;
            left: 50%;
            top: 50%;
            transform-origin: 50% 100%;
            background: #000000;
            border-radius: 6px;
        }}
        .mini-clock .second-hand {{
            width: 2px;
            height: 20px;
        }}
        .mini-clock .minute-hand {{
            width: 3px;
            height: 16px;
        }}
        .mini-clock .hour-hand {{
            width: 4px;
            height: 12px;
        }}
        .mini-clock .center-dot {{
            width: 6px;
            height: 6px;
            background: #000000;
            border-radius: 50%;
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
        }}
        .premium-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.45);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            padding: 16px;
        }}
        .premium-modal {{
            width: min(520px, 92vw);
            background: rgba(255, 255, 255, 0.92);
            border-radius: 28px;
            border: 1px solid rgba(255, 255, 255, 0.9);
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.18);
            padding: 22px 22px 18px;
            position: relative;
            backdrop-filter: blur(18px) saturate(160%);
        }}
        .premium-badge {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #000000;
            color: #FFFFFF !important;
            font-size: 12px;
            font-weight: 900;
            margin-bottom: 12px;
        }}
        .premium-title {{
            font-size: 24px;
            font-weight: 900;
            color: #000000;
            margin: 6px 0 10px;
            line-height: 1.2;
        }}
        .premium-headline {{
            font-size: 16px;
            font-weight: 900;
            color: #000000;
            margin-bottom: 12px;
        }}
        .premium-desc {{
            font-size: 14px;
            font-weight: 900;
            color: #000000;
            line-height: 1.5;
            margin-bottom: 16px;
        }}
        .premium-desc .bullet {{
            display: block;
            margin-bottom: 6px;
        }}
        .premium-cta {{
            width: 100%;
            background: #000000;
            color: #FFFFFF !important;
            border-radius: 999px;
            padding: 12px 16px;
            text-align: center;
            font-weight: 900;
            font-size: 15px;
        }}
        .premium-close {{
            position: absolute;
            top: 12px;
            right: 12px;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: rgba(0, 0, 0, 0.08);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            color: #000000;
            cursor: pointer;
        }}
        .premium-nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 14px;
            gap: 8px;
        }}
        .premium-nav button {{
            border: 0;
            background: #FFFFFF;
            color: #000000;
            padding: 8px 12px;
            border-radius: 10px;
            font-weight: 900;
            cursor: pointer;
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.08);
        }}
        .premium-dots {{
            display: flex;
            gap: 6px;
            align-items: center;
            justify-content: center;
            flex: 1;
        }}
        .premium-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: rgba(0, 0, 0, 0.2);
        }}
        .premium-dot.active {{
            background: #000000;
        }}
        .premium-snooze {{
            width: 100%;
            margin-top: 12px;
            text-align: right;
        }}
        .premium-snooze button {{
            background: transparent;
            border: 0;
            color: #000000;
            font-weight: 900;
            cursor: pointer;
            text-decoration: underline;
        }}
    </style>
    <div style="padding: 0 5px 10px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0 25px; padding: 0 5px;">
            <div>
                <div style="font-size: 30px; font-weight: 900; color: #000000; letter-spacing: -1px;">동네비서<span>.</span></div>
                <div style="font-size: 13px; color: #000000; opacity: 0.7;">Premium AI Store Management</div>
            </div>
            <div style="text-align: right; display: flex; align-items: center; gap: 10px; justify-content: flex-end;">
                <div>
                    <div id="clock" style="font-size: 28px; font-weight: 800; color: #000000;">{time_str}</div>
                    <div style="font-size: 14px; color: #000000; opacity: 0.7;">{date_str}</div>
                </div>
                <div class="mini-clock" aria-hidden="true">
                    <div class="hand hour-hand" id="clock-hour"></div>
                    <div class="hand minute-hand" id="clock-minute"></div>
                    <div class="hand second-hand" id="clock-second"></div>
                    <div class="center-dot"></div>
                </div>
            </div>
        </div>
        {killer_cards_html}
        
        <div style="margin-bottom: 15px; padding: 0 10px;">
            <div style="font-size: 16px; font-weight: 900; color: #000000;">기타 서비스</div>
        </div>
        {icon_grid_html}

        <div style="margin-top: 35px; background: rgba(255,255,255,0.2); border-radius: 100px; padding: 12px 25px; display: flex; align-items: center; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);">
            <span class="force-white" style="background: #000000; color: white; font-size: 12px; font-weight: 900; padding: 3px 12px; border-radius: 50px; margin-right: 15px;">SYSTEM</span>
            <span style="color: #000000; font-size: 14px; font-weight: 800;">동네비서 AI 시스템 최적화 완료</span>
        </div>
    </div>

    <div id="premium-overlay" class="premium-overlay" style="display: none;">
        <div class="premium-modal">
            <div class="premium-close" id="premium-close">✕</div>
            <div class="premium-badge" id="premium-tag">🚀 프리미엄 멤버십</div>
            <div class="premium-title" id="premium-title">시간이 곧 돈입니다</div>
            <div class="premium-headline" id="premium-headline">송장 타이핑에 뺏긴 하루 1시간, AI가 찾아드립니다.</div>
            <div class="premium-desc" id="premium-desc"></div>
            <a href="/?page=PREMIUM_ONLY" target="_top" class="premium-cta" id="premium-cta" onclick="window.top.location.href='/?page=PREMIUM_ONLY'; return false;">지금 바로 업무 시간 단축하기</a>
            <div class="premium-nav">
                <button type="button" id="premium-prev">이전</button>
                <div class="premium-dots" id="premium-dots"></div>
                <button type="button" id="premium-next">다음</button>
            </div>
            <div class="premium-snooze">
                <button type="button" id="premium-snooze">오늘은 그만보기</button>
            </div>
        </div>
    </div>
    
    <script>
    (function() {{
        const parentDoc = window.parent ? window.parent.document : document;
        const doc = document;
        const updateClock = () => {{
            const clockEl = parentDoc.getElementById('clock') || doc.getElementById('clock');
            const hourHand = doc.getElementById('clock-hour');
            const minuteHand = doc.getElementById('clock-minute');
            const secondHand = doc.getElementById('clock-second');
            if (clockEl) {{
                const now = new Date();
                const h = String(now.getHours()).padStart(2, '0');
                const m = String(now.getMinutes()).padStart(2, '0');
                const s = String(now.getSeconds()).padStart(2, '0');
                clockEl.innerText = h + ':' + m + ':' + s;
                if (hourHand && minuteHand && secondHand) {{
                    const seconds = now.getSeconds() + now.getMilliseconds() / 1000;
                    const minutes = now.getMinutes() + seconds / 60;
                    const hours = (now.getHours() % 12) + minutes / 60;
                    hourHand.style.transform = `translate(-50%, -100%) rotate(${{hours * 30}}deg)`;
                    minuteHand.style.transform = `translate(-50%, -100%) rotate(${{minutes * 6}}deg)`;
                    secondHand.style.transform = `translate(-50%, -100%) rotate(${{seconds * 6}}deg)`;
                }}
            }}
            window.requestAnimationFrame(updateClock);
        }};
        updateClock();
        const premiumSlides = [
            {{
                title: "시간이 곧 돈입니다",
                headline: "송장 타이핑에 뺏긴 하루 1시간, AI가 찾아드립니다.",
                desc: [
                    "프리미엄 가입 시 음성 주소 인식 무제한 제공",
                    "송장 출력 수수료 건당 10원 추가 할인"
                ],
                cta: "지금 바로 업무 시간 단축하기"
            }},
            {{
                title: "비서 한 명 고용한 효과",
                headline: "단골 손님 예약 전화, 이제 AI 비서에게 맡기고 쉬세요.",
                desc: [
                    "부재중 전화 자동 응대 및 예약 확정 알림톡 무상 발송",
                    "매장 매출 분석 대시보드 실시간 제공"
                ],
                cta: "월 00원으로 전담 비서 채용하기"
            }},
            {{
                title: "가입 즉시 버는 돈",
                headline: "지금 프리미엄 가입 시, 택배 발송 포인트 10,000P 즉시 증정!",
                desc: [
                    "일반 회원은 50원, 프리미엄은 35원! 보낼수록 커지는 차이",
                    "오늘만 드리는 한정 혜택을 놓치지 마세요."
                ],
                cta: "10,000원 받고 시작하기"
            }}
        ];
        const overlay = document.getElementById('premium-overlay');
        const titleEl = document.getElementById('premium-title');
        const headlineEl = document.getElementById('premium-headline');
        const descEl = document.getElementById('premium-desc');
        const ctaEl = document.getElementById('premium-cta');
        const closeBtn = document.getElementById('premium-close');
        const prevBtn = document.getElementById('premium-prev');
        const nextBtn = document.getElementById('premium-next');
        const dotsEl = document.getElementById('premium-dots');
        const snoozeBtn = document.getElementById('premium-snooze');
        let slideIndex = 0;

        const renderSlide = () => {{
            const data = premiumSlides[slideIndex];
            titleEl.innerText = data.title;
            headlineEl.innerText = data.headline;
            descEl.innerHTML = data.desc.map((d) => `<span class="bullet">• ${{d}}</span>`).join('');
            ctaEl.innerText = data.cta;
            dotsEl.innerHTML = premiumSlides.map((_, i) => `<span class="premium-dot ${'{'}i === slideIndex ? 'active' : ''{'}'}"></span>`).join('');
        }};

        const todayKey = new Date().toISOString().slice(0, 10);
        const snoozeKey = "dnbs_premium_snooze";
        const showPremium = () => {{
            const snoozed = localStorage.getItem(snoozeKey);
            if (snoozed === todayKey) {{
                overlay.style.display = 'none';
                return;
            }}
            overlay.style.display = 'flex';
            renderSlide();
        }};
        const hidePremium = () => {{
            overlay.style.display = 'none';
        }};

        prevBtn.addEventListener('click', () => {{
            slideIndex = (slideIndex - 1 + premiumSlides.length) % premiumSlides.length;
            renderSlide();
        }});
        nextBtn.addEventListener('click', () => {{
            slideIndex = (slideIndex + 1) % premiumSlides.length;
            renderSlide();
        }});
        closeBtn.addEventListener('click', hidePremium);
        snoozeBtn.addEventListener('click', () => {{
            localStorage.setItem(snoozeKey, todayKey);
            hidePremium();
        }});

        showPremium();
    }})();
    </script>
    """)
    full_ui_html = "\n".join([line.lstrip() for line in full_ui_html.splitlines()])
    st.markdown(full_ui_html, unsafe_allow_html=True)
    components.html("""
    <script>
    (function() {
        const parentDoc = window.parent ? window.parent.document : document;
        const tick = () => {
            const clockEl = parentDoc.getElementById('clock');
            const hourHand = parentDoc.getElementById('clock-hour');
            const minuteHand = parentDoc.getElementById('clock-minute');
            const secondHand = parentDoc.getElementById('clock-second');
            if (clockEl) {
                const now = new Date();
                const h = String(now.getHours()).padStart(2, '0');
                const m = String(now.getMinutes()).padStart(2, '0');
                const s = String(now.getSeconds()).padStart(2, '0');
                clockEl.innerText = h + ':' + m + ':' + s;
                if (hourHand && minuteHand && secondHand) {
                    const seconds = now.getSeconds() + now.getMilliseconds() / 1000;
                    const minutes = now.getMinutes() + seconds / 60;
                    const hours = (now.getHours() % 12) + minutes / 60;
                    hourHand.style.transform = `translate(-50%, -100%) rotate(${hours * 30}deg)`;
                    minuteHand.style.transform = `translate(-50%, -100%) rotate(${minutes * 6}deg)`;
                    secondHand.style.transform = `translate(-50%, -100%) rotate(${seconds * 6}deg)`;
                }
            }
            window.requestAnimationFrame(tick);
        };
        tick();
    })();
    </script>
    """, height=0, scrolling=False)

    query_params = st.query_params
    if "page" in query_params:
        target = query_params["page"]
        st.query_params.clear()
        navigate_to(target)

# 📄 [서브 페이지] 서비스 신청 관리 (택배/예약 통합)
elif st.session_state.page == "RESERVE" or st.session_state.page == "DELIVERY":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.session_state.selected_store is None:
        if st.button("⬅️ 메인으로 돌아가기"): go_home()
        page_title = "📦 택배 매장 검색" if st.session_state.page == "DELIVERY" else "📅 매장 예약 검색"
        st.markdown(f'<h1 style="color:#000000; font-weight:900;">{page_title}</h1>', unsafe_allow_html=True)
        search_query = st.text_input("🔍 가맹점 이름 또는 연락처로 검색", placeholder="가게 이름을 입력하세요...")
        try:
            stores_dict = db_manager.get_all_stores()
            if stores_dict:
                store_list = [sdata for sid, sdata in stores_dict.items() if search_query.lower() in sdata.get('name', '').lower() or search_query in sdata.get('phone', '').replace('-', '')]
                for store in store_list:
                    with st.container():
                        st.markdown(f'<div class="glass-card" style="margin-bottom:10px;"><h3 style="margin:0; color:#000000;">{store["name"]}</h3><p style="margin:5px 0; color:#000000;">📍 {store.get("address", "주소 미등록")}</p></div>', unsafe_allow_html=True)
                        if st.button(f"👉 {store['name']} 선택하기", key=f"sel_{store.get('store_id', store['name'])}"):
                            st.session_state.selected_store = store
                            st.rerun()
        except Exception as e: st.error(f"DB 오류: {e}")
    else:
        store = st.session_state.selected_store
        if st.button(f"⬅️ '{store['name']}' 선택 취소"):
            st.session_state.selected_store = None
            st.rerun()
        st.markdown(f'<h2 style="color:#000000;">🏢 {store["name"]}</h2>', unsafe_allow_html=True)
        service_type = st.radio("🔔 서비스 선택", ["📅 매장 예약", "📦 택배 발송"], index=0 if st.session_state.page == "RESERVE" else 1, horizontal=True)
        st.markdown("---")
        
        if "예약" in service_type:
            with st.form("reservation_form"):
                reservation_date = st.date_input("예약 날짜")
                reservation_time = st.time_input("예약 시간")
                party_size = st.number_input("인원 수", min_value=1, max_value=50, value=2)
                cust_name = st.text_input("예약자 성함")
                cust_phone = st.text_input("연락처")
                request = st.text_area("요청사항", height=80)
                submit = st.form_submit_button("✅ 예약 신청")
                if submit:
                    if not cust_name or not cust_phone:
                        st.error("예약자 성함과 연락처를 입력해주세요.")
                    else:
                        reservation_data = {
                            "reservation_date": reservation_date.strftime("%Y-%m-%d"),
                            "reservation_time": reservation_time.strftime("%H:%M"),
                            "party_size": int(party_size),
                            "customer_name": cust_name,
                            "customer_phone": cust_phone,
                            "request": request,
                            "store_name": store.get("name", "")
                        }
                        saved = db_manager.save_table_reservation(store.get("store_id", ""), reservation_data)
                        if saved:
                            st.success("예약이 접수되었습니다.")
                            go_home()
                        else:
                            st.error("예약 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")
        else:
            st.markdown("### 📦 택배 발송 신청")
            s_name = st.text_input("보내는 분 성함")
            s_phone = st.text_input("보내는 분 연락처")
            s_addr = st.text_input("보내는 분 주소")
            s_addr_detail = st.text_input("보내는 분 상세주소")
            r_name = st.text_input("받는 분 성함")
            r_phone = st.text_input("받는 분 연락처")
            r_addr = st.text_input("받는 분 주소")
            r_addr_detail = st.text_input("받는 분 상세주소")
            item_name = st.text_input("물품명")
            item_count = st.number_input("수량", min_value=1, max_value=999, value=1)
            pickup_date = st.date_input("수거 희망일")
            weight_str = st.selectbox("무게", logen_delivery.get_weight_options())
            size_str = st.selectbox("크기", logen_delivery.get_size_options())
            use_logen = st.checkbox("로젠택배로 바로 예약하기", value=True)
            memo = st.text_area("요청사항", height=80)
            if st.button("🚀 택배 접수 완료"):
                if not s_name or not s_phone or not r_name or not r_phone or not r_addr:
                    st.error("보내는 분/받는 분 정보와 주소를 입력해주세요.")
                else:
                    if use_logen:
                        sender = {
                            "name": s_name,
                            "phone": s_phone,
                            "address": s_addr,
                            "detail_address": s_addr_detail
                        }
                        receiver = {
                            "name": r_name,
                            "phone": r_phone,
                            "address": r_addr,
                            "detail_address": r_addr_detail
                        }
                        package = {
                            "type": "박스",
                            "weight": logen_delivery.parse_weight(weight_str),
                            "size": logen_delivery.parse_size(size_str),
                            "contents": item_name or "일반상품",
                            "count": int(item_count)
                        }
                        result, error = logen_delivery.create_delivery_reservation(
                            sender=sender,
                            receiver=receiver,
                            package=package,
                            pickup_date=pickup_date.strftime("%Y-%m-%d"),
                            memo=memo
                        )
                        if error:
                            st.error(f"로젠택배 예약 실패: {error}")
                            st.stop()
                        saved = db_manager.save_logen_reservation(result)
                        if saved:
                            st.success(f"로젠택배 예약 완료! 예약번호: {result.get('reservation_number')}")
                            if result.get("logen_web_url"):
                                st.markdown(f"[로젠택배 예약 확인하기]({result.get('logen_web_url')})")
                            go_home()
                        else:
                            st.error("로젠택배 예약 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")
                        st.stop()
                    order_data = {
                        "store_id": store.get("store_id", "delivery"),
                        "store_name": store.get("name", "택배 접수"),
                        "sender_name": s_name,
                        "sender_phone": s_phone,
                        "sender_address": s_addr,
                        "receiver_name": r_name,
                        "receiver_phone": r_phone,
                        "receiver_address": r_addr,
                        "item_name": item_name,
                        "item_count": int(item_count),
                        "memo": memo
                    }
                    saved = db_manager.save_delivery_order(order_data)
                    if saved:
                        st.success("택배가 접수되었습니다.")
                        go_home()
                    else:
                        st.error("택배 접수 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")

# 📄 [서브 페이지] 결제 시스템
elif st.session_state.page == "PAYMENT":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.button("⬅️ 홈으로"): go_home()
    st.markdown('<h1 style="color:#000000; font-weight:900;">💳 결제하기</h1>', unsafe_allow_html=True)
    st.info("결제 기능 준비 중입니다.")

# 📄 [서브 페이지] 가맹점 가입 신청
elif st.session_state.page == "JOIN":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.button("⬅️ 메인으로 돌아가기"): go_home()
    st.markdown('<h1 style="color:#000000; font-weight:900;">🤝 가맹 가입 신청</h1>', unsafe_allow_html=True)
    login_tab, join_tab, find_tab = st.tabs(["🔐 로그인", "🧾 회원가입", "🔎 아이디/비밀번호 찾기"])

    with login_tab:
        with st.form("login_form"):
            login_id = st.text_input("아이디")
            login_pw = st.text_input("비밀번호", type="password")
            if st.form_submit_button("🚀 로그인"):
                success, msg, store_info = db_manager.verify_store_login(login_id, login_pw)
                if not success:
                    success, msg, store_info = db_manager.verify_master_login(login_id, login_pw)
                if success:
                    st.success(f"환영합니다, {store_info['name']} 사장님!")
                    st.session_state.logged_in_store = store_info
                    go_home()
                else:
                    st.error(f"로그인 실패: {msg}")

    with join_tab:
        with st.form("join_form"):
            store_name = st.text_input("상호명")
            owner_name = st.text_input("대표자명")
            phone = st.text_input("연락처")
            kakao_id = st.text_input("카톡 아이디")
            store_id = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            business_type = st.selectbox("업종", ["식당/음식점", "택배/물류", "카페/디저트", "미용/뷰티", "일반판매", "기타"])
            region = st.text_input("지역(예: 서울 강남구)")
            memo = st.text_area("추가 문의", height=90)
            if st.form_submit_button("🚀 신청하기"):
                if not owner_name or not phone or not store_id or not password:
                    st.error("대표자명, 연락처, 아이디, 비밀번호는 필수입니다.")
                else:
                    detail_data = {
                        "store_name": store_name,
                        "owner_name": owner_name,
                        "kakao_id": kakao_id
                    }
                    inquiry_data = {
                        "name": owner_name,
                        "phone": phone,
                        "kakao_id": kakao_id,
                        "business_type": business_type,
                        "region": region,
                        "memo": memo,
                        "store_id": store_id,
                        "password": password,
                        "detail_data": json.dumps(detail_data, ensure_ascii=True)
                    }
                    saved = db_manager.save_inquiry(inquiry_data)
                    if saved:
                        st.success("가맹 신청이 완료되었습니다.")
                        go_home()
                    else:
                        st.error("가맹 신청 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")

    with find_tab:
        st.markdown("### 아이디 찾기", unsafe_allow_html=True)
        with st.form("find_id_form"):
            find_owner_name = st.text_input("대표자 성함")
            find_phone = st.text_input("연락처")
            if st.form_submit_button("🔎 아이디 찾기"):
                if not find_owner_name or not find_phone:
                    st.error("대표자 성함과 연락처를 입력해주세요.")
                else:
                    found_id = db_manager.find_store_id(find_owner_name, find_phone)
                    if found_id:
                        st.success(f"아이디는 '{found_id}' 입니다.")
                    else:
                        st.error("일치하는 아이디를 찾을 수 없습니다.")

        st.markdown("---")
        st.markdown("### 비밀번호 재설정", unsafe_allow_html=True)
        with st.form("reset_pw_form"):
            reset_store_id = st.text_input("아이디", key="reset_store_id")
            reset_phone = st.text_input("연락처", key="reset_phone")
            reset_pw = st.text_input("새 비밀번호", type="password", key="reset_pw")
            if st.form_submit_button("🔐 비밀번호 재설정"):
                if not reset_store_id or not reset_phone or not reset_pw:
                    st.error("아이디, 연락처, 새 비밀번호를 입력해주세요.")
                else:
                    is_ok, msg = db_manager.validate_password_length(reset_pw)
                    if not is_ok:
                        st.error(msg)
                    else:
                        store = db_manager.get_store(reset_store_id)
                        if not store:
                            st.error("등록된 아이디를 찾을 수 없습니다.")
                        else:
                            stored_phone = store.get("phone", "").replace("-", "").strip()
                            target_phone = reset_phone.replace("-", "").strip()
                            if stored_phone != target_phone:
                                st.error("연락처가 일치하지 않습니다.")
                            else:
                                store["password"] = reset_pw
                                saved = db_manager.save_store(reset_store_id, store, encrypt_password=True)
                                if saved:
                                    st.success("비밀번호가 재설정되었습니다. 새 비밀번호로 로그인하세요.")
                                else:
                                    st.error("비밀번호 재설정에 실패했습니다. 잠시 후 다시 시도해주세요.")

# 📄 [서브 페이지] 프리미엄 멤버십 포털
elif st.session_state.page == "PREMIUM_ONLY":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.button("⬅️ 메인으로 돌아가기"): go_home()
    st.markdown('<h1 style="color:#000000; font-weight:900;">💎 프리미엄 멤버십</h1>', unsafe_allow_html=True)
    st.info("프리미엄 회원 전용 공간입니다.")

# 📄 [서브 페이지] 매장 관리
elif st.session_state.page == "STORE_MGMT":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.button("⬅️ 메인으로 돌아가기"): go_home()
    st.markdown('<h1 style="color:#000000; font-weight:900;">🛠️ 매장 통합 관리</h1>', unsafe_allow_html=True)
    if st.session_state.logged_in_store is None:
        with st.form("login_form"):
            login_id = st.text_input("아이디")
            login_pw = st.text_input("비밀번호", type="password")
            if st.form_submit_button("🚀 로그인"):
                success, msg, store_info = db_manager.verify_store_login(login_id, login_pw)
                if not success:
                    success, msg, store_info = db_manager.verify_master_login(login_id, login_pw)
                if success:
                    st.success(f"환영합니다, {store_info['name']} 사장님!")
                    st.session_state.logged_in_store = store_info
                    st.rerun()
                else:
                    st.error(f"로그인 실패: {msg}")
    else:
        st.write(f"환영합니다, {st.session_state.logged_in_store['name']} 사장님!")
        if st.button("🔓 로그아웃"):
            st.session_state.logout_requested = True
            st.rerun()

# 🤖 [서브 페이지] AI 상담원
elif st.session_state.page == "AI_CHAT":
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.button("⬅️ 메인으로 돌아가기"): go_home()
    st.markdown('<h1 style="color:#000000; font-weight:900;">🤖 AI 지능형 상담원</h1>', unsafe_allow_html=True)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    voice_ui_html = """
    <style>
        .voice-card {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 16px 18px;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.9);
            box-shadow: 0 10px 24px rgba(0,0,0,0.12);
            margin: 10px 0 16px;
        }
        .mic-btn {
            width: 54px;
            height: 54px;
            border-radius: 50%;
            background: #000000;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            cursor: pointer;
            border: 0;
            flex-shrink: 0;
        }
        .voice-text {
            color: #000000;
            font-weight: 900;
        }
        .voice-title {
            font-size: 16px;
            margin-bottom: 6px;
        }
        .voice-live {
            font-size: 14px;
            line-height: 1.5;
            min-height: 42px;
            padding: 8px 10px;
            border-radius: 10px;
            background: rgba(0,0,0,0.04);
        }
        .voice-status {
            font-size: 12px;
            opacity: 0.7;
            margin-top: 6px;
        }
        .voice-actions {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }
        .voice-action {
            background: #000000;
            color: #FFFFFF;
            border-radius: 999px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 900;
            border: 0;
            cursor: pointer;
        }
        .voice-action.secondary {
            background: #FFFFFF;
            color: #000000;
            border: 1px solid #000000;
        }
    </style>
    <div class="voice-card">
        <button class="mic-btn" id="mic-btn" aria-label="voice">🎤</button>
        <div class="voice-text">
            <div class="voice-title">무엇이든 불어 보세요</div>
            <div class="voice-live" id="voice-live">대화 내용을 실시간으로 표시합니다.</div>
            <div class="voice-status" id="voice-status">마이크 버튼을 누르고 말씀하세요.</div>
            <div class="voice-actions">
                <button class="voice-action" id="voice-copy">텍스트 복사</button>
                <button class="voice-action secondary" id="voice-clear">지우기</button>
            </div>
        </div>
    </div>
    <script>
        (function() {
            const micBtn = document.getElementById('mic-btn');
            const liveEl = document.getElementById('voice-live');
            const statusEl = document.getElementById('voice-status');
            const copyBtn = document.getElementById('voice-copy');
            const clearBtn = document.getElementById('voice-clear');
            let recognition = null;
            let listening = false;

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                statusEl.textContent = '이 브라우저는 음성 인식을 지원하지 않습니다.';
                micBtn.disabled = true;
            } else {
                recognition = new SpeechRecognition();
                recognition.lang = 'ko-KR';
                recognition.interimResults = true;
                recognition.continuous = true;

                recognition.onstart = () => {
                    listening = true;
                    statusEl.textContent = '듣는 중...';
                    micBtn.style.background = '#2E86DE';
                };
                recognition.onend = () => {
                    listening = false;
                    statusEl.textContent = '중지됨. 다시 누르면 재시작합니다.';
                    micBtn.style.background = '#000000';
                };
                recognition.onerror = (e) => {
                    statusEl.textContent = '오류: ' + e.error;
                };
                recognition.onresult = (event) => {
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    if (transcript.trim().length > 0) {
                        liveEl.textContent = transcript.trim();
                    }
                };
            }

            micBtn.addEventListener('click', () => {
                if (!recognition) return;
                if (listening) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            });
            copyBtn.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(liveEl.textContent);
                    statusEl.textContent = '복사 완료! 채팅 입력창에 붙여넣기 하세요.';
                } catch (e) {
                    statusEl.textContent = '복사 실패: 브라우저 권한을 확인하세요.';
                }
            });
            clearBtn.addEventListener('click', () => {
                liveEl.textContent = '';
                statusEl.textContent = '지웠습니다. 다시 말씀하세요.';
            });
        })();
    </script>
    """
    components.html(voice_ui_html, height=200, scrolling=False)
    
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).markdown(msg["content"])
    
    user_input = st.chat_input("문의 내용을 입력하세요")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("AI 답변 생성 중..."):
            reply = ai_manager.get_ai_response(user_input, st.session_state.chat_history)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

else:
    st.markdown('<div style="padding-top: 20px;"></div>', unsafe_allow_html=True)
    if st.button("⬅️ 메인으로 돌아가기"): go_home()
    st.header(f"✨ {st.session_state.page} 기능 준비 중")
