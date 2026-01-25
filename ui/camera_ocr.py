import streamlit as st
import ocr_manager
import time
from ui.styles import load_css

def render_camera_ocr():
    load_css()
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h2>📷 AI 촬영 접수</h2>
        <p>송장이나 주소를 촬영하면 AI가 자동으로 입력합니다.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Camera / File Input Strategy
    st.caption("🔒 보안 브라우저에서는 카메라 권한 허용이 필요합니다.")
    st.info("⚠️ 카메라가 안 켜지시면, 아래 **[📁 앨범/파일 선택]** 탭을 눌러주세요!", icon="💡")
    
    # We provide both options for better compatibility
    tab_cam, tab_file = st.tabs(["📸 카메라 촬영", "📁 앨범/파일 선택"])
    
    img_file = None
    
    with tab_cam:
        img_cam = st.camera_input("송장이 잘 보이게 찍어주세요")
        if img_cam:
            img_file = img_cam
            
    with tab_file:
        st.info("카메라가 작동하지 않으면 파일을 직접 업로드하세요.")
        img_upload = st.file_uploader("갤러리에서 사진 선택", type=['png', 'jpg', 'jpeg'])
        if img_upload:
            img_file = img_upload
    
    # Session state to hold OCR result to prevent re-running OCR on slight interactions
    if "ocr_result" not in st.session_state:
        st.session_state.ocr_result = None
    
    if img_file:
        if st.session_state.ocr_result is None:
            # Show Loading
            with st.spinner("🤖 AI가 주소를 읽고 있습니다... (약 5초)"):
                # Call OCR
                bytes_data = img_file.getvalue()
                result = ocr_manager.call_naver_ocr(bytes_data)
                st.session_state.ocr_result = result
                st.rerun()
                
    # 2. Result Verification
    if st.session_state.ocr_result:
        data = st.session_state.ocr_result
        
        st.markdown("### 📝 읽어온 정보 확인")
        st.info("AI가 분석한 내용입니다. 맞는지 확인해주세요.")
        
        with st.form("ocr_confirm_form"):
            col1, col2 = st.columns(2)
            r_name = col1.text_input("받는 분", value=data.get("receiver_name", "홍길동"))
            r_phone = col2.text_input("연락처", value=data.get("receiver_phone", "010-0000-0000"))
            address = st.text_input("주소", value=data.get("address", ""))
            item = st.text_input("물품 정보", value=data.get("item_name", "잡화"))
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("✅ 이대로 접수하기", type="primary", use_container_width=True):
                # Save to DB (Assuming delivery logic)
                st.success("접수가 완료되었습니다!")
                time.sleep(1.5)
                # Clear and go back
                st.session_state.ocr_result = None
                st.session_state.page = "member_dashboard"
                st.rerun()
                
        if st.button("🔄 다시 촬영하기", use_container_width=True):
            st.session_state.ocr_result = None
            st.rerun()

    # Back button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔙 메인으로 돌아가기", use_container_width=True):
        st.session_state.page = "member_dashboard"
        st.session_state.ocr_result = None
        st.rerun()
