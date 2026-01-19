import streamlit as st
import pandas as pd
import db_manager


def get_sheet_data(sheet_name):
    """Streamlit Secrets를 이용해 구글 시트 데이터를 가져옵니다."""
    try:
        spreadsheet = db_manager.get_spreadsheet()
        if spreadsheet is None:
            return pd.DataFrame()
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")
        return pd.DataFrame()


def render_report():
    user_type = st.session_state.get('user_type', '일반사업자')
    
    # 1. 유형별 데이터 로드
    sheet_map = {
        "일반사업자": "매장예약",
        "택배사업자": "택배접수",
        "농어민": "직거래장부"
    }
    df = get_sheet_data(sheet_map[user_type])

    # 2. 리포트 헤더 디자인
    st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.55); padding: 20px; border-radius: 30px; border: 1px solid rgba(255, 255, 255, 0.8);">
            <h2 style="color: #000000; text-align: center;">💎 {user_type} 주간 분석 리포트</h2>
        </div>
    """, unsafe_allow_html=True)

    # 3. 데이터가 있을 경우 지표 계산
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        total_count = len(df)
        
        if user_type == "일반사업자" and '매출액' in df.columns:
            total_val = f"{df['매출액'].sum():,}원"
        else:
            total_val = f"{total_count}건"
            
        col1.metric("주간 총계", total_val, "데이터 기반")
        col2.metric("전일 대비", "보통", "0%")
        col3.metric("AI 기여도", "92%", "▲ 2%")

        if '요일' in df.columns:
            st.write("### 📈 요일별 추이")
            st.line_chart(df.set_index('요일'))
    else:
        st.warning("아직 장부에 기록된 데이터가 없습니다. AI 비서가 업무를 시작하면 여기에 리포트가 생성됩니다.")

    # 4. AI 맞춤 전략
    with st.expander("🤖 AI 매출 향상 전략 확인하기", expanded=True):
        if user_type == "일반사업자":
            st.info("💡 주말 예약 고객에게 '선주문 링크'를 발송하여 노쇼를 방지하세요.")
        elif user_type == "택배사업자":
            st.info("💡 수요일 대량 접수 고객에게 전용 수수료 혜택 알림을 보내세요.")
        else:
            st.info("💡 제철 품목 구매 단골에게 '직거래 장터' 문자를 자동 발송하세요.")

    if st.button("⬅️ 홈으로 돌아가기", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()


def render_premium_report(user_type):
    st.title(f"💎 {user_type} 전용 경영 리포트")

    if user_type == "일반사업자":
        st.subheader("🍽️ 매장 예약 및 회전율 분석")
        st.metric("AI 예약 전환율", "85%", "▲ 10%")

    elif user_type == "택배사업자":
        st.subheader("📦 물동량 및 배송 효율 분석")
        st.metric("송장 자동 발행 건수", "1,240건", "▲ 210건")

    elif user_type == "농어민":
        st.subheader("🍎 농산물 직거래 판매 현황")
        st.metric("단골 재구매율", "62%", "▲ 5%")

    # [AI 전략 섹션]
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.subheader("🤖 AI 맞춤 전략")
    st.markdown("""
    - <span class="gold-text">전략 1:</span> 수요일 택배 고객 대상 **'금요일 식사 쿠폰'** 발송
    - <span class="gold-text">전략 2:</span> 금요일 저녁 피크타임 **AICC(AI 전화) 집중 가동**
    - <span class="gold-text">전략 3:</span> 미방문 단골 4인 대상 **컴백 알림톡 발송**
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
