import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import db_manager


def render_admin_page():
    st.markdown(
        """
        <style>
        .admin-title {
            font-size: 28px;
            font-weight: 900;
            margin-bottom: 6px;
        }
        .admin-subtitle {
            font-size: 14px;
            font-weight: 700;
            color: #333333;
            margin-bottom: 24px;
        }
        .big-card {
            border: 1px solid #E6E6E6;
            border-radius: 16px;
            padding: 18px 20px;
            background: #FFFFFF;
            box-shadow: 0 6px 16px rgba(0,0,0,0.05);
            min-height: 116px;
        }
        .big-card-title {
            font-size: 13px;
            font-weight: 800;
            color: #555555;
            letter-spacing: -0.2px;
            margin-bottom: 6px;
        }
        .big-card-value {
            font-size: 30px;
            font-weight: 900;
            color: #111111;
            line-height: 1.1;
        }
        .big-card-sub {
            font-size: 12px;
            color: #888888;
            margin-top: 6px;
        }
        .section-title {
            font-size: 18px;
            font-weight: 900;
            margin: 24px 0 12px;
        }
        .section-sub {
            font-size: 12px;
            font-weight: 700;
            color: #666666;
            margin-bottom: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="admin-title">경영 대시보드</div>', unsafe_allow_html=True)
    st.markdown('<div class="admin-subtitle">실시간 수익과 정산 지표를 한눈에 확인합니다.</div>', unsafe_allow_html=True)

    def _safe_int(value):
        try:
            return int(str(value).replace(",", "").strip())
        except Exception:
            return 0

    def _parse_datetime(value):
        if not value:
            return None
        try:
            parsed = pd.to_datetime(value, errors="coerce")
            if pd.isna(parsed):
                return None
            return parsed.to_pydatetime()
        except Exception:
            return None

    def _load_user_management_records():
        spreadsheet = db_manager.get_spreadsheet()
        if spreadsheet is None:
            return []
        try:
            worksheet = spreadsheet.worksheet("유저관리")
            return worksheet.get_all_records()
        except Exception:
            return []

    def _fee_rate_from_level(level_value):
        level_value = str(level_value or "")
        return "4%" if "프리미엄" in level_value else "5%"

    user_records = _load_user_management_records()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    last_24_hours = now - timedelta(hours=24)

    today_fee_total = 0
    new_store_count = 0
    pending_settlement_total = 0

    for row in user_records:
        joined_at = _parse_datetime(row.get("가입일시", ""))
        joined_str = str(row.get("가입일시", "") or "")

        if joined_at and joined_at >= last_24_hours:
            new_store_count += 1
        elif joined_str.startswith(today_str):
            new_store_count += 1

        if joined_at and joined_at.strftime("%Y-%m-%d") == today_str:
            today_fee_total += _safe_int(row.get("사장님수수료", 0))
        elif joined_str.startswith(today_str):
            today_fee_total += _safe_int(row.get("사장님수수료", 0))

        if str(row.get("정산상태", "") or "").strip() == "대기":
            pending_settlement_total += _safe_int(row.get("총 결제금액", 0))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="big-card">
                <div class="big-card-title">실시간 수익 (당일 수수료 합계)</div>
                <div class="big-card-value">{today_fee_total:,}원</div>
                <div class="big-card-sub">H열 수수료 기준</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="big-card">
                <div class="big-card-title">정산 관리 (대기 합계)</div>
                <div class="big-card-value" style="color:#E53935;">{pending_settlement_total:,}원</div>
                <div class="big-card-sub">J열 상태가 '대기'인 금액 합산</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"""
            <div class="big-card">
                <div class="big-card-title">신규 유저 (최근 24시간)</div>
                <div class="big-card-value">{new_store_count:,}명</div>
                <div class="big-card-sub">가입일시 기준</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">실시간 거래 현황</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">최근 결제 기록 기준, 상호/금액/수수료율/시간</div>', unsafe_allow_html=True)

    feed_rows = []
    for row in user_records:
        amount = _safe_int(row.get("총 결제금액", 0))
        if amount <= 0:
            continue
        joined_at = _parse_datetime(row.get("가입일시", "")) or _parse_datetime(row.get("정산예정일", ""))
        store_name = row.get("상호명") or row.get("가게명") or row.get("store_name") or "미상"
        feed_rows.append(
            {
                "상호명": store_name,
                "금액": f"{amount:,}원",
                "수수료율": _fee_rate_from_level(row.get("유저 등급", "")),
                "시간": joined_at.strftime("%m-%d %H:%M") if joined_at else "-",
                "_sort_time": joined_at or datetime.min,
            }
        )

    if feed_rows:
        feed_df = pd.DataFrame(feed_rows).sort_values("_sort_time", ascending=False).head(12)
        feed_df.drop(columns=["_sort_time"], inplace=True)
        st.dataframe(feed_df, use_container_width=True, hide_index=True)
    else:
        st.info("실시간 거래 내역이 없습니다.")

    st.markdown('<div class="section-title">빠른 실행 메뉴</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">관리자가 자주 쓰는 기능만 표시합니다.</div>', unsafe_allow_html=True)
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        if st.button("공지사항 작성", use_container_width=True):
            st.info("공지사항 작성 화면은 사이드바에서 열 수 있습니다.")
    with a2:
        if st.button("수수료율 일괄 변경", use_container_width=True):
            st.info("수수료율 설정은 사이드바에서 관리합니다.")
    with a3:
        if st.button("정산 확정", use_container_width=True):
            st.info("정산 확정 기능은 사이드바에서 진행합니다.")
    with a4:
        if st.button("정산 내역 내보내기", use_container_width=True):
            st.info("내보내기는 사이드바에서 진행합니다.")

    st.sidebar.markdown("### 관리 메뉴")

    with st.sidebar.expander("💎 포인트 관리", expanded=False):
        stores = db_manager.get_all_stores()
        if stores:
            st.metric("전체 가맹점", f"{len(stores)}개")
            total_pts = sum([int(s.get('points', 0) or 0) for s in stores.values()])
            st.metric("총 유통 포인트", f"{total_pts:,}원")
            options = [f"{s.get('name')} ({sid})" for sid, s in stores.items()]
            sel = st.selectbox("가맹점 선택", ["선택하세요..."] + options, key="sb_store_select")
            amt = st.number_input("충전 금액", min_value=0, step=1000, value=10000, key="sb_store_amount")
            if st.button("즉시 충전", key="sb_charge_btn"):
                if sel != "선택하세요...":
                    tid = sel.split("(")[-1].rstrip(")")
                    if db_manager.update_store_points(tid, amt):
                        st.success("충전 완료")
                        st.rerun()

    with st.sidebar.expander("🏢 가맹점 목록", expanded=False):
        stores = db_manager.get_all_stores()
        if stores:
            data = []
            for sid, info in stores.items():
                data.append({
                    "ID": sid,
                    "가게명": info.get('name'),
                    "점주": info.get('owner_name'),
                    "연락처": info.get('phone'),
                    "포인트": f"{int(info.get('points', 0) or 0):,}원"
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        else:
            st.info("가맹점 데이터가 없습니다.")

    with st.sidebar.expander("📝 신규 가맹점 등록", expanded=False):
        with st.form("sb_new_store"):
            nid = st.text_input("아이디*")
            npw = st.text_input("비밀번호*", type="password")
            nname = st.text_input("가게명*")
            nowner = st.text_input("대표자명*")
            nphone = st.text_input("연락처")
            npts = st.number_input("초기 포인트", value=1000)
            if st.form_submit_button("등록하기"):
                if nid and npw and nname and nowner:
                    if db_manager.save_store(nid, {'password': npw, 'name': nname, 'owner_name': nowner, 'phone': nphone, 'points': npts}):
                        st.success("등록 완료")
                        st.rerun()

    with st.sidebar.expander("⚙️ 설정/테스트", expanded=False):
        st.markdown("#### ✅ 구글시트 연동 테스트")
        if st.button("구글시트 연결 테스트", key="sb_sheet_test"):
            try:
                spreadsheet = db_manager.get_spreadsheet()
                if spreadsheet is None:
                    st.error("구글시트 연결 실패: 스프레드시트를 찾을 수 없습니다.")
                else:
                    st.success(f"연동 성공: {spreadsheet.title}")
            except Exception as e:
                st.error(f"구글시트 연결 실패: {e}")

        st.divider()
        st.markdown("#### 🧾 정산 로직 시뮬레이터")
        st.markdown("유저관리 시트의 **아이디**와 금액을 입력한 뒤 **테스트 실행**을 눌러주세요.", unsafe_allow_html=True)
        sim_id = st.text_input("테스트 아이디", key="sb_sim_user_id")
        sim_amount = st.number_input("테스트 결제금액", min_value=0, step=1000, value=100000, key="sb_sim_pay_amount")
        if st.button("테스트 실행", key="sb_sim_run"):
            ok, msg = db_manager.update_user_plan_status(
                store_id=sim_id,
                plan_status="유료",
                payment_amount=sim_amount,
                settlement_status="대기"
            )
            if ok:
                st.success("정산 테스트 완료: 시트에 데이터가 기록되었습니다.")
            else:
                st.error(f"정산 테스트 실패: {msg}")

    st.sidebar.divider()
    if st.sidebar.button("로그아웃"):
        st.session_state.logged_in_store = None
        st.session_state.store_id = None
        st.session_state.is_admin = False
        st.session_state.page = "home"
        st.rerun()
