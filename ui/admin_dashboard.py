import streamlit as st
import db_manager as db
import pandas as pd

def render_admin_dashboard():
    st.title("통합 관리자 모드")
    
    if st.button("로그아웃 (Admin)", key="admin_logout"):
        from ui.auth import logout
        logout()
    
    tab1, tab2, tab3 = st.tabs(["유저 관리", "충전 승인", "전체 통계"])
    
    with tab1:
        st.subheader("가입 유저 목록")
        # Load user data
        df = db.get_business_data("유저관리") # You might need to adjust this depending on how data is stored
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("데이터가 없습니다.")
            
    with tab2:
        st.subheader("지갑 충전 요청")
        requests = db.get_all_topups()
        if requests:
            df_req = pd.DataFrame(requests)
            st.dataframe(df_req)
            
            # Simple approval mechanism
            req_id_to_approve = st.text_input("승인할 요청 ID 입력")
            if st.button("승인 처리"):
                # Logic to find row and update
                st.success("승인 로직은 db_manager.update_topup_status와 연동 필요")
        else:
            st.info("대기 중인 요청이 없습니다.")

    with tab3:
        st.metric("총 가입자 수", "124명")
        st.metric("이번 달 총 거래액", "₩45,200,000")

def render_admin_billing():
    st.title("정산 관리")
    st.write("구현 예정...")
