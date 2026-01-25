import streamlit as st
import db_manager as db
from ui.auth import TIER_CATALOG
from ui.styles import load_css, card

def render_home():
    load_css()
    st.markdown("## 👋 환영합니다!")
    st.info("👈 왼쪽 사이드바에서 [로그인] 해주세요")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(card("🤖", "AI 비서", "24시간 전화 응대", "card-primary"), unsafe_allow_html=True)
    with col2:
        st.markdown(card("📦", "택배 접수", "운송장 즉시 출력", "card-orange"), unsafe_allow_html=True)
        
    st.markdown("---")
    st.image("https://source.unsplash.com/random/800x400/?store,cafe", use_container_width=True)

def render_member_dashboard():
    load_css()
    
    # Header Section
    col_head, col_out = st.columns([3, 1])
    with col_head:
        st.markdown(f"### {st.session_state.assistant_member_name} 사장님")
    with col_out:
        if st.button("로그아웃", key="dash_logout", use_container_width=True):
            from ui.auth import logout
            logout()
    
    tier_key = st.session_state.get("assistant_tier_key", "general")
    tier_info = TIER_CATALOG.get(tier_key, TIER_CATALOG["general"])
    
    # Logic for Trial Period (7 Days)
    # For demo, if joined_at is missing, assume today.
    # In auth.py we didn't save joined_at to session, so let's default to NOW (Trial Active).
    # Real app would fetch from DB.
    from datetime import datetime
    
    # Mocking join date as today for demonstration of trial
    join_str = st.session_state.get("joined_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    try:
        join_date = datetime.strptime(join_str, "%Y-%m-%d %H:%M:%S")
        days_passed = (datetime.now() - join_date).days
    except:
        days_passed = 0
        
    is_trial_active = days_passed < 7
    trial_days_left = 7 - days_passed
    
    # Locking Logic Helpers
    def check_lock(required_tier, feature_name):
        # 🎁 Trial Override
        if is_trial_active:
            return False, "✨ " # Unlocked with sparkle
            
        if required_tier == "premium":
            if is_general: return True, "🔒 "
        elif required_tier == "master":
            if is_general or is_premium: return True, "🔒 "
        return False, ""
        
    # Free Trial Banner
    if is_trial_active and tier_key == "general":
        st.info(f"🎉 **7일 무료 체험 중입니다!** (남은 기간: {trial_days_left}일)\n모든 프리미엄 기능을 마음껏 써보세요!")

    # 1. 🌟 Killer Features (Top Priority)
    st.markdown("""
    <div style="margin-top: -10px; margin-bottom: 10px;">
        <p style="font-size: 14px; opacity: 0.8; margin-bottom: 4px;">오늘 보낼 택배,</p>
        <span style="font-size: 18px; font-weight: 700; color: #1A73E8;">사진 찍거나 말씀만 하세요!</span>
    </div>
    """, unsafe_allow_html=True)
    
    k1, k2 = st.columns(2)
    with k1:
        if st.button("📷\n촬영 접수\n(AI OCR)", key="btn_camera", use_container_width=True, type="primary"):
            st.session_state.page = "camera_ocr"
            st.rerun()
    with k2:
        if st.button("🎙️\n음성 접수\n(STT)", key="btn_voice", use_container_width=True, type="primary"):
            st.info("마이크 연동 준비 중입니다.") # Placeholder

    # 2. 💰 Real-time Sales Summary
    # Using a simple card style for impact
    st.markdown("""
    <div class="kiosk-card" style="background: linear-gradient(135deg, #1A73E8 0%, #0052cc 100%); color: white; padding: 20px; align-items: flex-start; text-align: left; margin-bottom: 20px;">
        <div style="font-size: 13px; opacity: 0.9; margin-bottom: 4px;">오늘 사장님이 번 돈 (수익)</div>
        <div style="font-size: 32px; font-weight: 800;">155,000원</div>
        <div style="font-size: 12px; opacity: 0.8; margin-top: 4px;">▲ 어제보다 12% 상승</div>
    </div>
    """, unsafe_allow_html=True)

    # 3. 🛡️ Service Menu (Tier Logic)
    # Tiers: general < premium < master
    is_general = (tier_key == "general")
    is_premium = (tier_key == "premium")
    # is_master = (tier_key == "master")
    
    # Locking Logic Helpers
    def check_lock(required_tier, feature_name):
        # Return (is_locked, lock_prefix)
        # If user is general, he fails premium/master checks.
        # If user is premium, he fails master check.
        if required_tier == "premium":
            if is_general: return True, "🔒 "
        elif required_tier == "master":
            if is_general or is_premium: return True, "🔒 "
        return False, ""

    st.markdown("### ⚡ 서비스 메뉴")
    
    # [Row 1]
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        # Ledger: General OK (Basic)
        if st.button("�\n장부 관리\n(기본형)", key="btn_ledger", use_container_width=True):
             st.session_state.page = "ledger"
             st.rerun()
             
    with r1c2:
        # SMS: Premium Only
        locked, prefix = check_lock("premium", "문자 발송")
        if st.button(f"{prefix}📢\n문자 발송\n(단골 홍보)", key="btn_sms", use_container_width=True):
            if locked: show_lock_modal("문자 발송")
            else: st.info("문자 발송 화면으로 이동")

    # [Row 2]
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        # AI Report: Premium Only
        locked, prefix = check_lock("premium", "AI 리포트")
        if st.button(f"{prefix}📊\n매출 분석\n(AI 리포트)", key="btn_report", use_container_width=True):
            if locked: show_lock_modal("AI 경영 리포트")
            else: st.info("리포트 화면으로 이동")
            
    with r2c2:
        # Storage: Master Only
        locked, prefix = check_lock("master", "물품 보관")
        if st.button(f"{prefix}📦\n물품 보관\n(VIP 전용)", key="btn_storage", use_container_width=True):
            if locked: show_lock_modal("매장 물품 보관")
            else: st.info("물품 보관 화면으로 이동")

    # 3. Footer Banner & CTA
    st.markdown("---")
    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
         st.info(f"🎁 현재 **{tier_info['label']}** 이용 중")
    with f_col2:
        if is_general: # Show for free users
            if st.button("🆙 혜택 보기", type="primary", use_container_width=True):
                render_upgrade_section(tier_key)
    
    # 4. Upgrade Section
    render_upgrade_section(tier_key)

@st.dialog("✨ 프리미엄 기능 잠금해제")
def show_lock_modal(feature_name):
    # Session state initialization for toggle within dialog
    # Note: Dialogs share global session state. We need a unique key.
    if "lock_modal_step" not in st.session_state:
        st.session_state.lock_modal_step = "info"

    if st.session_state.lock_modal_step == "info":
        st.markdown(f"""
        ### 🔒 {feature_name}
        이 기능은 **프리미엄 등급**부터 사용할 수 있습니다.
        
        **프리미엄 혜택:**
        - 🧾 **장부 관리**: 일일 매출 자동 분석 리포트
        - 📢 **문자 발송**: 단골 손님 자동 관리
        - 🤖 **AI 비서**: 24시간 전화/예약 대행
        
        월 30,000원으로 매장 관리를 자동화하세요!
        """)
        if st.button("🚀 1분 만에 업그레이드 하기", type="primary", use_container_width=True):
             st.session_state.lock_modal_step = "payment"
             st.rerun()
    
    elif st.session_state.lock_modal_step == "payment":
        _render_payment_info_content("프리미엄", "월 30,000원")
        if st.button("🔙 뒤로가기"):
            st.session_state.lock_modal_step = "info"
            st.rerun()

def _render_payment_info_content(name, price):
    st.markdown(f"""
    ### {name} 업그레이드
    **결제 금액: {price}**
    
    아래 계좌로 입금해주시면 10분 내로 승인됩니다.
    
    ---
    **🏦 카카오뱅크 3333-00-1234567**
    **예금주: 동네비서(주)**
    ---
    
    또는 토스 앱으로 바로 결제하기:
    """)
    st.image("https://static.toss.im/icons/png/4x/logo-toss-blue.png", width=50)
    st.button("토스 결제창 열기 (시뮬레이션)", key="pay_link_btn")
    st.caption("입금 후 '입금완료' 문자를 보내주시면 더 빠릅니다.")

def render_upgrade_section(current_tier_key):
    st.markdown("""
    <div style="text-align: center; margin-top: 40px; margin-bottom: 20px;">
        <h2 style="margin-bottom: 4px;">🚀 더 똑똑한 동네비서 만나기</h2>
        <p style="color: #666; font-size: 14px;">매장 관리가 10배 더 편해집니다</p>
    </div>
    """, unsafe_allow_html=True)
    
    tiers = [
        {
            "key": "general",
            "name": "🏢 일반 등급",
            "price": "무료",
            "features": ["기본 택배 접수", "수동 주소 입력"],
            "color": "#95a5a6"
        },
        {
            "key": "premium",
            "name": "💎 프리미엄",
            "price": "월 30,000원",
            "features": ["AI OCR 사진 스캔", "실시간 매출 분석 리포트"],
            "color": "#3498db"
        },
        {
            "key": "master", 
            "name": "👑 마스터",
            "price": "월 50,000원",
            "features": ["음성 에이전트 무제한", "최저가 택배 자동 매칭", "VIP 우선 수거"],
            "color": "#9b59b6"
        }
    ]
    
    for tier in tiers:
        is_current = (tier["key"] == current_tier_key)
        
        # Prepare Button Label
        features_text = "\n".join([f"• {f}" for f in tier['features']])
        if is_current:
            label = f"✅ {tier['name']} (사용 중)\n{tier['price']}\n\n{features_text}"
        else:
            label = f"{tier['name']}\n{tier['price']}\n\n{features_text}\n\n👉 터치하여 업그레이드"
            
        # Render as a single big button
        if st.button(label, key=f"btn_tier_{tier['key']}", use_container_width=True, disabled=is_current):
             if not is_current:
                # Set session state to show payment info in a modal-like way if needed, 
                # OR call show_payment_modal dialog if outside of another dialog.
                # Since render_upgrade_section is on the main dashboard, we use dialog.
                show_payment_modal(tier['name'], tier['price'])
        
        st.write("") # Spacer

@st.dialog("멤버십 결제 안내")
def show_payment_modal(name, price):
    _render_payment_info_content(name, price)
