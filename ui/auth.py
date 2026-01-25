import streamlit as st
import db_manager as db
from datetime import datetime
from ui.styles import load_css

TIER_CATALOG = {
    "general": {
        "label": "🏢 일반 등급",
        "fee": 0,
        "benefits": ["기본 택배 접수", "수동 주소 입력"],
        "description": "기본 기능 무료 제공"
    },
    "premium": {
        "label": "💎 프리미엄",
        "fee": 30000,
        "benefits": ["AI OCR 사진 스캔", "실시간 매출 분석 리포트"],
        "description": "스마트한 매장 관리의 시작"
    },
    "master": {
        "label": "👑 마스터",
        "fee": 50000,
        "benefits": ["음성 에이전트 무제한", "최저가 택배 자동 매칭", "VIP 우선 수거"],
        "description": "모든 기능을 제한 없이"
    },
}

def render_login_page():
    load_css()
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("is_admin", False)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="font-size: 28px; font-weight: 800; margin-bottom: 8px;">🏪 동네비서</h1>
        <p style="opacity: 0.6;">소상공인을 위한 스마트 매장 관리</p>
    </div>
    """, unsafe_allow_html=True)

    # Login Container
    with st.container():
        st.markdown('<div class="kiosk-card card-glass" style="min-height: auto; padding: 30px 20px;">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔒 간편 로그인", "🛡️ 관리자"])
        
        with tab1:
            name = st.text_input("아이디 (이름/상호명)", key="login_name", placeholder="예: 맛있는분식")
            phone = st.text_input("전화번호", key="login_phone", placeholder="010-1234-5678")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 로그인 및 시작하기", use_container_width=True, key="btn_member_login"):
                if not name.strip() or not phone.strip():
                    st.error("이름과 전화번호를 입력해주세요.")
                else:
                    # Default new users to 'general'
                    tier_key = "general"
                    tier_info = TIER_CATALOG[tier_key]
                    
                    st.session_state.logged_in = True
                    st.session_state.is_admin = False
                    st.session_state.store_id = phone
                    st.session_state.assistant_member_name = name
                    st.session_state.assistant_member_phone = phone
                    st.session_state.assistant_member_tier = tier_info["label"]
                    st.session_state.assistant_tier_key = tier_key
                    st.session_state.assistant_tier_fee = tier_info["fee"]
                    
                    # Async save (Create or Update)
                    db.save_user_management({
                        "가입일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "아이디": phone,
                        "상호명": name,
                        "유저 등급": tier_info["label"],
                        "연락처": phone
                    })
                    
                    # 🍪 Persist Login
                    st.query_params["user_id"] = phone
                    
                    st.rerun()

        with tab2:
            st.warning("관계자 외 접근 금지")
            admin_pin = st.text_input("관리자 PIN", type="password", key="login_admin_pin")
            if st.button("관리자 접속", use_container_width=True, key="btn_admin_login"):
                expected_pin = st.secrets.get("admin_pin", "admin777")
                if admin_pin == expected_pin:
                    st.session_state.logged_in = True
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("승인되지 않은 접근입니다.")

        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown("""
    <div style="text-align: center; margin-top: 40px; opacity: 0.5; font-size: 12px;">
        서비스 문의: 1588-0000<br>
        copyright © 동네비서 All rights reserved.
    </div>
    """, unsafe_allow_html=True)


def logout():
    # Clear Session
    for key in ["logged_in", "is_admin", "show_login_form", "store_id", "assistant_member_name"]:
        if key in st.session_state:
            del st.session_state[key]
            
    # Clear URL Params
    st.query_params.clear()
    
    st.rerun()
