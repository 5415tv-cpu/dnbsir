import streamlit as st
import db_manager as db
from ui.auth import render_login_page
from ui.dashboard import render_member_dashboard
from ui.onboarding import render_onboarding
from ui.camera_ocr import render_camera_ocr

# Page Config
st.set_page_config(
    page_title="동네비서",
    page_icon="🏪",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def main():
    # Session State Init
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "page" not in st.session_state:
        st.session_state.page = "home"

    # 🔄 Auto-login Check (Persist Login)
    if not st.session_state.logged_in:
        # Check query params for persisted session
        try:
            params = st.query_params
            user_id = params.get("user_id")
            if user_id:
                # Try to fetch user info to validate
                # Adapting to db_manager which uses sqlite
                # We need a function to get user by ID.
                # Assuming recover_user_session helps or we fetch directly.
                # Quick fix: fetch from user_management table/sheet wrapper
                user_info = db.get_user_by_id(user_id) 
                if user_info:
                    st.session_state.logged_in = True
                    st.session_state.store_id = user_id
                    st.session_state.assistant_member_name = user_info.get("name", "")
                    st.session_state.assistant_member_phone = user_id
                    
                    # Tier Mapping
                    t_label = user_info.get("tier", "일반 등급")
                    t_map = {"일반 등급": "general", "프리미엄": "premium", "마스터": "master"}
                    st.session_state.assistant_tier_key = t_map.get(t_label, "general")
                    st.session_state.assistant_member_tier = t_label
                    # Rerun to refresh state
                    st.rerun()
        except Exception:
            pass # Fail silently if query params invalid
            
    # Routing Logic (Strict Separation)
    if not st.session_state.logged_in:
        # Case 1: Not Logged In
        render_login_page()
    
    else:
        # Case 2: Logged In -> Check Onboarding
        # We check if store info exists in DB
        if not st.session_state.get("is_admin"):
            store_info = db.get_store(st.session_state.store_id)
            if not store_info:
                render_onboarding()
                return # Stop here

        # Case 3: Onboarding Done -> Dashboard
        if st.session_state.get("is_admin"):
            render_admin_dashboard()
        else:
            # Member Pages
            page = st.session_state.page
            if page == "member_dashboard" or page == "home":
                render_member_dashboard()
            elif page == "camera_ocr":
                render_camera_ocr()
            elif page == "delivery":
                st.markdown("### 📦 택배 접수")
                if st.button("🔙 뒤로가기"):
                     st.session_state.page = "member_dashboard"
                     st.rerun()
                st.info("준비 중인 기능입니다.")
            elif page == "ledger":
                st.markdown("### 📓 장부 관리")
                if st.button("🔙 뒤로가기"):
                     st.session_state.page = "member_dashboard"
                     st.rerun()
                st.info("준비 중인 기능입니다.")
            else:
                 render_member_dashboard()


if __name__ == "__main__":
    main()
