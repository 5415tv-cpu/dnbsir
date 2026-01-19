import streamlit as st
import streamlit.components.v1 as components
import db_manager
from datetime import datetime, timedelta


def render_payment_page():
    user_type = st.session_state.get("user_type", "일반사업자")
    today = datetime.now()
    settlement_date = today + timedelta(days=5)
    plans = {
        "일반사업자": {"name": "매장 올인원 비서", "price": 33000},
        "택배사업자": {"name": "물류 자동화 마스터", "price": 11000},
        "농어민": {"name": "농가 상생 패키지", "price": 55000}
    }
    plan = plans.get(user_type, plans["일반사업자"])
    plan_name = plan["name"]
    amount = plan["price"]

    pay_status = st.query_params.get("pay")
    if "pay_status_done" not in st.session_state:
        st.session_state.pay_status_done = False
    if not pay_status:
        st.session_state.pay_status_done = False
    if pay_status == "success" and not st.session_state.pay_status_done:
        store = st.session_state.get("logged_in_store") or {}
        store_id = store.get("store_id") or st.session_state.get("store_id")
        phone = store.get("phone")
        settlement_str = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        ok, msg = db_manager.update_user_plan_status(
            store_id=store_id,
            phone=phone,
            plan_status="유료",
            payment_amount=amount,
            owner_fee=0,
            settlement_date=settlement_str,
            settlement_status="대기"
        )
        if ok:
            st.success("결제가 완료되었습니다. 요금제 상태가 '유료'로 변경되었습니다.")
            st.success("정식 버전 활성화 완료")
        else:
            st.warning(f"결제는 완료됐으나 요금제 상태 업데이트 실패: {msg}")
        st.session_state.pay_status_done = True
        st.markdown(
            "<script>const url=new URL(window.location.href);url.searchParams.delete('pay');window.history.replaceState({},'',url.href);</script>",
            unsafe_allow_html=True
        )
    elif pay_status == "fail" and not st.session_state.pay_status_done:
        st.error("결제가 실패했습니다. 다시 시도해주세요.")
        st.session_state.pay_status_done = True
        st.markdown(
            "<script>const url=new URL(window.location.href);url.searchParams.delete('pay');window.history.replaceState({},'',url.href);</script>",
            unsafe_allow_html=True
        )

    st.markdown("""
        <div class="glass-container" style="margin-bottom: 16px;">
            <div style="font-size: 22px; font-weight: 900; color: #000000; text-align: center;">💳 서비스 구독 및 결제</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 💳 {plan_name} 결제 및 구독", unsafe_allow_html=True)
    st.info(f"📅 **매일 정산 시스템 가동 중**: 오늘 결제 시 **{settlement_date.strftime('%m월 %d일')}** 입금 예정")

    client_key = st.secrets.get("TOSS_CLIENT_KEY", "test_ck_D53Q9DRW8vn67W1pbp98QNkd9Z4G")
    toss_mid = st.secrets.get("TOSS_MID", "dnbsiruydn")
    app_base_url = (st.secrets.get("APP_BASE_URL") or "").strip().rstrip("/")
    order_id = f"order_{st.session_state.get('store_id','guest')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    toss_script = f"""
    <script src="https://js.tosspayments.com/v1/payment"></script>
    <script>
      var clientKey = '{client_key}';
      var mid = '{toss_mid}';
      var tossPayments = TossPayments(clientKey);
      var baseUrl = '{app_base_url}';
      try {{
        if (!baseUrl) baseUrl = window.top.location.origin;
      }} catch (e) {{
        if (!baseUrl) baseUrl = window.location.origin;
      }}
      var basePath = "";
      try {{
        basePath = window.top.location.pathname;
      }} catch (e) {{
        basePath = window.location.pathname;
      }}
      var successUrl = baseUrl + basePath + "?page=PAYMENT&pay=success&mid=" + encodeURIComponent(mid);
      var failUrl = baseUrl + basePath + "?page=PAYMENT&pay=fail&mid=" + encodeURIComponent(mid);

      window.pay = function(method) {{
        try {{
          tossPayments.requestPayment(method, {{
            amount: {amount},
            orderId: '{order_id}',
            orderName: '{plan_name}',
            customerName: '단골비서 사장님',
            successUrl: successUrl,
            failUrl: failUrl
          }});
        }} catch (err) {{
          alert("결제창 호출에 실패했습니다. 키/주소 설정을 확인해주세요.");
          console.error(err);
        }}
      }};
    </script>
    <div style="display:flex; flex-direction:column; gap:10px;">
      <button type="button" onclick="window.pay('카드')" style="width:100%; padding:14px; background:#000000; color:#FFFFFF; border:1px solid #000000; border-radius:14px; cursor:pointer; font-size:16px; font-weight:900;">
        💳 신용카드 결제
      </button>
      <button type="button" onclick="window.pay('TOSSPAY')" style="width:100%; padding:14px; background:#000000; color:#FFFFFF; border:1px solid #000000; border-radius:14px; cursor:pointer; font-size:16px; font-weight:900;">
        🔵 토스페이 결제
      </button>
    </div>
    """
    components.html(toss_script, height=150)

    st.markdown("**현재 7일 무료 체험 중입니다. 체험 종료 후 자동 결제됩니다.**", unsafe_allow_html=True)
    st.markdown("**카드 결제 시 부가세 포함 금액이며, 세금계산서가 자동 발행됩니다**", unsafe_allow_html=True)

    if st.button("⬅️ 홈으로 돌아가기", use_container_width=True):
        st.session_state.page = "home"
        st.rerun()
