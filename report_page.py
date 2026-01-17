import streamlit as st
import pandas as pd


def render_report():
    # 메인 디자인과 분리된 리포트 전용 스타일
    st.markdown("""
        <style>
        .report-card {
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 15px;
            border: 1px solid #D4AF37;
            margin-bottom: 20px;
        }
        .gold-text { color: #D4AF37; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    st.title("💎 프리미엄 경영 리포트")
    st.write("지난 일주일간의 데이터를 AI가 분석한 결과입니다.")

    # [데이터 섹션]
    col1, col2, col3 = st.columns(3)
    col1.metric("주간 매출", "659만원", "▲12%")
    col2.metric("택배 접수", "234건", "▲45건")
    col3.metric("단골 재방문", "88%", "▲5%")

    # [차트 섹션]
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.subheader("📊 요일별 매출 및 택배 현황")
    chart_data = pd.DataFrame({
        '요일': ['월', '화', '수', '목', '금', '토', '일'],
        '매출(만원)': [85, 72, 98, 79, 125, 140, 60],
        '택배(건)': [42, 38, 55, 31, 48, 15, 5]
    })
    st.line_chart(data=chart_data, x='요일')
    st.markdown('</div>', unsafe_allow_html=True)

    # [AI 전략 섹션]
    st.markdown('<div class="report-card">', unsafe_allow_html=True)
    st.subheader("🤖 AI 맞춤 전략")
    st.markdown("""
    - <span class="gold-text">전략 1:</span> 수요일 택배 고객 대상 **'금요일 식사 쿠폰'** 발송
    - <span class="gold-text">전략 2:</span> 금요일 저녁 피크타임 **AICC(AI 전화) 집중 가동**
    - <span class="gold-text">전략 3:</span> 미방문 단골 4인 대상 **컴백 알림톡 발송**
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
