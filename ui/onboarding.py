import streamlit as st
import db_manager as db
from ui.styles import load_css

def render_onboarding():
    load_css()
    
    st.markdown("""
    <div style="text-align: center; margin-top: 20px; margin-bottom: 30px;">
        <h2>🏪 매장 정보 설정</h2>
        <p>서비스 이용을 위해 기본 정보를 입력해주세요.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="kiosk-card card-glass" style="min-height: auto; padding: 30px 20px;">', unsafe_allow_html=True)
        
        # We assume store_id is the phone number or whatever was set in auth
        store_id = st.session_state.store_id
        store_name = st.session_state.assistant_member_name
        
        st.info(f"아이디(연락처): {store_id}")
        
        # 1. Business Category
        category = st.selectbox("업종 선택", ["음식점", "카페", "편의점/마트", "미용/뷰티", "택배/물류", "기타"])
        
        # 2. Address (Simple text for now)
        address = st.text_input("매장 주소", placeholder="예: 서울시 강남구...")
        
        # 3. Simple Description
        info = st.text_area("매장 소개(한줄)", placeholder="예: 맛과 정성을 다하는 분식집입니다.")
        
        st.write("")
        if st.button("✅ 저장하고 시작하기", use_container_width=True, type="primary"):
            if not address.strip():
                st.error("주소를 입력해주세요.")
            else:
                # Save to DB
                store_data = {
                    "store_id": store_id,
                    "name": store_name,
                    "category": category,
                    "address": address, # Add address col to DB schema if needed or put in info
                    "info": info,
                    "phone": store_id
                }
                # We need to make sure db_sqlite supports this. For now adapt.
                # db_manager.save_store delegates to db_sqlite.save_store
                db.save_store(store_id, store_data)
                
                # Flag as done
                st.session_state.store_setup_done = True
                st.session_state.page = "member_dashboard"
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)
