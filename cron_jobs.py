import threading
import time
import schedule
import logging
import sqlite3
from datetime import datetime, timedelta
import db_manager as db
from comm_middleware import CommMiddleware

logger = logging.getLogger(__name__)

TOKEN_DB_PATH = "/var/www/dnbsir/database.db"

def auto_refill_tokens():
    """
    auto_refill_on=1 인 store의 wallet_balance를 auto_refill_amount 이상으로 유지.
    매 시간 실행 — 잔액이 auto_refill_amount 미만이면 자동으로 채움.
    """
    try:
        conn = sqlite3.connect(TOKEN_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT store_id, wallet_balance, auto_refill_amount "
            "FROM stores WHERE auto_refill_on=1"
        )
        rows = cur.fetchall()
        for store_id, balance, refill_amount in rows:
            target = refill_amount if refill_amount and refill_amount > 0 else 10000
            if balance < target:
                cur.execute(
                    "UPDATE stores SET wallet_balance=? WHERE store_id=?",
                    (target, store_id)
                )
                logger.info(f"[AutoRefill] {store_id}: {balance} → {target} 자동 충전")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"[AutoRefill] 오류: {e}")


def ask_tomorrow_schedule():
    """
    매일 22:00에 실행되어 점주들에게 익일 영업 여부를 묻는 발송 로직
    """
    logger.info("Executing 22:00 Schedule Check Job")
    stores = db.get_all_stores()
    
    if not stores:
        logger.info("등록된 상점이 없습니다.")
        return

    import config
    import sms_manager
    base_url = config.get_secret("APP_BASE_URL", "https://dongnebiseo.com").rstrip("/")
    solapi_cfg = sms_manager.get_solapi_config()
    api_key = solapi_cfg.get('api_key', '')
    api_secret = solapi_cfg.get('api_secret', '')
    sender_phone = solapi_cfg.get('sender_phone', '')
    
    # 알림톡 템플릿(가정)
    template_id = config.get_secret("SOLAPI_SCHEDULE_CHECK_TEMPLATE_ID", "")
    pf_id = config.get_secret("SOLAPI_PF_ID", "")

    for store in stores:
        store_phone = store.get("phone", "")
        store_id = store.get("store_id", "")
        store_name = store.get("name", "가맹점")
        
        if not store_phone or not store_id:
            continue
            
        settings_link = f"{base_url}/schedule/confirm?store_id={store_id}"
        
        msg_body = f"[{store_name}] 사장님, 내일 영업 일정을 확인해주세요.\n\n정상 영업하시나요? 아래 링크를 통해 간편하게 내일 영업/휴무 스케줄을 확정하실 수 있습니다.\n\n▶ 스케줄 확정 링크:\n{settings_link}\n\n※ 오늘 자정 전까지 미응답 시 '기본 스케줄'로 자동 설정됩니다."

        if not api_key:
             logger.info(f"[Mock 22:00 알림] To: {store_phone}, Msg: {msg_body}")
             try: db.log_sms(store_id, store_phone, "SCHEDULE_CHK", msg_body, "SUCCESS", "Mock Mode")
             except: pass
             continue

        # 발송
        try:
             CommMiddleware.send_solapi_message_with_retry(
                 to_phone=store_phone,
                 message=msg_body,
                 sender_phone=sender_phone,
                 api_key=api_key,
                 api_secret=api_secret,
                 template_id=template_id,
                 pf_id=pf_id,
                 variables={"#{store_name}": store_name, "#{settings_link}": settings_link}
             )
             try: db.log_sms(store_id, store_phone, "SCHEDULE_CHK", msg_body, "SUCCESS", "OK")
             except: pass
        except Exception as e:
             logger.error(f"스케줄 확인 문자 발송 실패 ({store_id}): {e}")
             try: db.log_sms(store_id, store_phone, "SCHEDULE_CHK", msg_body, "ERROR", str(e))
             except: pass

def check_unanswered_schedules():
    """
    무응답 시 기본 스케줄 자동 전환 및 최종 확인 메시지 발송 로직 (자정 00:00 경 실행)
    (이 함수는 23:59 경에 실행되도록 예약합니다.)
    """
    logger.info("Executing 23:59 Unanswered Schedule Fallback Job")
    stores = db.get_all_stores()
    
    import config
    import sms_manager
    solapi_cfg = sms_manager.get_solapi_config()
    api_key = solapi_cfg.get('api_key', '')
    api_secret = solapi_cfg.get('api_secret', '')
    sender_phone = solapi_cfg.get('sender_phone', '')

    for store in stores:
        store_phone = store.get("phone", "")
        store_id = store.get("store_id", "")
        store_name = store.get("name", "가맹점")
        
        if not store_phone or not store_id:
             continue
             
        # 오늘 응답 여부 체크 로직 추가 필요. (여기서는 모의로 무조건 진행한다고 가정하거나 DB 필드 확인)
        # 예: store.get("has_confirmed_schedule", False)
        # 기본 스케줄로 복구한다고 업데이트
        # db.update_store(store_id, {"has_confirmed_schedule": False, "closed_message": ""}) ...
        
        # 임시 발송 메시지
        msg_body = f"[{store_name}] 사장님, 오늘 스케줄 응답이 없어 내일 영업은 '기본 설정(정상영업)'으로 자동 적용되었습니다.\n변경이 필요하면 대시보드를 통해 수정해주세요."
        
        if not api_key:
             logger.info(f"[Mock 23:59 알림] To: {store_phone}, Msg: {msg_body}")
             continue
             
        try:
             CommMiddleware.send_solapi_message_with_retry(
                 to_phone=store_phone,
                 message=msg_body,
                 sender_phone=sender_phone,
                 api_key=api_key,
                 api_secret=api_secret
             )
        except Exception as e:
             logger.error(f"스케줄 최종 확인 문자 발송 실패 ({store_id}): {e}")

def check_security_anomalies():
    """
    주기적으로 보안 로그(security_logs)를 파악하여 해킹 시도 또는 이상 징후를 관리자에게 알림
    """
    logger.info("Executing Security Reports & Anomalies Check")
    try:
        df = db.get_security_logs_summary(hours=1)
        if df is None or df.empty:
            return
            
        alert_msg = []
        for _, row in df.iterrows():
            store_id = row.get("store_id", "UNKNOWN")
            evt = row.get("event_type", "UNKNOWN")
            cnt = row.get("count", 0)
            
            # 1시간 내 에러/보안 알림 기준 초과
            if cnt >= 5:
                alert_msg.append(f"[{store_id}] {evt} 다수 발생 ({cnt}건)")
                
        if alert_msg:
            full_msg = "[AI 보안 감시 알림]\n동네비서 시스템에 이상 징후가 감지되었습니다.\n\n" + "\n".join(alert_msg)
            logger.warning(full_msg)
            
            import config
            import sms_manager
            
            admin_phone = config.get_secret("ADMIN_PHONE")
            if not admin_phone:
                return
                
            solapi_cfg = sms_manager.get_solapi_config()
            if not solapi_cfg.get('api_key'):
                return
                
            CommMiddleware.send_solapi_message_with_retry(
                to_phone=admin_phone,
                message=full_msg,
                sender_phone=solapi_cfg.get('sender_phone', admin_phone),
                api_key=solapi_cfg.get('api_key'),
                api_secret=solapi_cfg.get('api_secret')
            )
    except Exception as e:
        logger.error(f"Security Alert Job Error: {e}")

def check_solapi_health():
    """
    Solapi API 키 유효성 6시간마다 점검.
    키가 만료/무효면 관리자에게 즉시 SMS 경보.
    """
    try:
        import config, sms_manager, requests as _req
        api_key    = config.get_secret("SOLAPI_API_KEY", "")
        api_secret = config.get_secret("SOLAPI_API_SECRET", "")
        admin_phone = config.get_secret("ADMIN_ALERT_PHONE", "01023847447")

        if not api_key or not api_secret:
            logger.warning("[SolapiHealth] API 키 미설정")
            return

        # Solapi 잔액 조회로 키 유효성 확인
        import hmac as _hmac, hashlib as _hash, time as _time
        date_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        salt      = str(int(_time.time() * 1000))
        sig_data  = date_str + salt
        signature = _hmac.new(api_secret.encode(), sig_data.encode(), _hash.sha256).hexdigest()
        auth_hdr  = f"HMAC-SHA256 apiKey={api_key}, date={date_str}, salt={salt}, signature={signature}"

        resp = _req.get(
            "https://api.solapi.com/cash/v1/balance",
            headers={"Authorization": auth_hdr},
            timeout=10
        )
        if resp.status_code == 200:
            data    = resp.json()
            balance = data.get("balance", {}).get("balance", "?")
            logger.info(f"[SolapiHealth] ✅ 정상 | 잔액: {balance}원")
        else:
            err_msg = f"Solapi 응답 이상: HTTP {resp.status_code} — {resp.text[:100]}"
            logger.error(f"[SolapiHealth] ❌ {err_msg}")
            sms_manager.send_cloud_sms(
                admin_phone,
                f"[동네비서 경보] Solapi API 키 이상!\n{err_msg}\n→ SMS 발송이 중단될 수 있습니다. 즉시 확인 필요.",
                store_id="SYSTEM"
            )
    except Exception as e:
        logger.error(f"[SolapiHealth] 점검 실패: {e}")


def watch_auth_fail():
    """
    최근 30분 내 AUTH_FAIL 로그를 감시.
    3건 이상이면 관리자에게 SMS 경보.
    """
    try:
        import config, sms_manager, db_sqlite
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        conn = sqlite3.connect(TOKEN_DB_PATH)
        cur  = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM webhook_logs WHERE stage='AUTH_FAIL' AND received_at >= ?",
            (cutoff.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        count = cur.fetchone()[0]
        conn.close()

        if count >= 3:
            admin_phone = config.get_secret("ADMIN_ALERT_PHONE", "01023847447")
            logger.warning(f"[AuthFailWatch] 30분 내 AUTH_FAIL {count}건 감지 → 관리자 경보")
            sms_manager.send_cloud_sms(
                admin_phone,
                f"[동네비서 경보] 인증 실패 다발!\n최근 30분 내 {count}건의 AUTH_FAIL 발생.\n→ 앱 토큰이 서버와 불일치할 수 있습니다.\ntantanfab.com/admin/webhook-monitor 확인 요망.",
                store_id="SYSTEM"
            )
        else:
            logger.debug(f"[AuthFailWatch] AUTH_FAIL {count}건 (정상 범위)")
    except Exception as e:
        logger.error(f"[AuthFailWatch] 감시 실패: {e}")


def cleanup_expired_reservations_job():
    """
    주기적으로 만료시간이 지난 임시 점유(Hold) 예약을 정리합니다.
    """
    logger.info("Executing Reservation Expiry Hold Cleanup Job")
    try:
        cleaned = db.cleanup_expired_holds()
        if cleaned > 0:
            logger.info(f"[ReservationCleanup] 만료된 임시 점유 예약 {cleaned}건 정리 완료")
    except Exception as e:
        logger.error(f"[ReservationCleanup] 만료 처리 오류: {e}")


def run_schedule_loop():
    logger.info("Scheduler thread started.")
    schedule.every().minute.do(cleanup_expired_reservations_job) # ★ 매 분 임시 점유 만료 예약 정리
    schedule.every().day.at("22:00").do(ask_tomorrow_schedule)
    schedule.every().day.at("23:59").do(check_unanswered_schedules)
    schedule.every().hour.do(check_security_anomalies)
    schedule.every().hour.do(auto_refill_tokens)
    # ★ webhook_logs 자동 정리 — 매일 새벽 3시
    schedule.every().day.at("03:00").do(_purge_webhook_logs)
    # ★ Solapi API 키 유효성 — 6시간마다
    schedule.every(6).hours.do(check_solapi_health)
    # ★ AUTH_FAIL 다발 감시 — 30분마다
    schedule.every(30).minutes.do(watch_auth_fail)
    # ★ 태백 날씨 갱신 — 1시간마다 (코리욨 브리지로 asyncio 호출)
    schedule.every().hour.do(_refresh_weather_sync)

    auto_refill_tokens()       # 시작 즉시 실행
    check_solapi_health()      # ★ 서버 시작 시 즉시 Solapi 점검
    _refresh_weather_sync()    # ★ 서버 시작 시 즉시 날씨 로드

    import os
    if os.environ.get("MOCK_CRON_TEST", "false").lower() == "true":
        schedule.every(2).minutes.do(ask_tomorrow_schedule)

    while True:
        schedule.run_pending()
        time.sleep(1)

def _purge_webhook_logs():
    """콘_직에서 호출하는 webhook_logs 정리 래퍼"""
    try:
        if hasattr(db, 'purge_old_webhook_logs'):
            deleted = db.purge_old_webhook_logs()
        else:
            import db_sqlite
            deleted = db_sqlite.purge_old_webhook_logs()
        logger.info(f"[webhook_purge] 자동 정리 완료: {deleted}건 삭제")
    except Exception as e:
        logger.error(f"[webhook_purge] 오류: {e}")


def _refresh_weather_sync():
    """
    동기 스케줄러 스레드에서 asyncio 코루틴을 실행하는 브리지 함수.
    routers.kiosk.refresh_weather()를 asyncio.run()으로 호출하여
    서버 메모리의 cached_weather를 갱신한다.
    """
    import asyncio as _asyncio
    try:
        from routers.kiosk import refresh_weather
        _asyncio.run(refresh_weather())
    except Exception as e:
        logger.warning(f"[날씨 스케줄러] 실패: {e}")


def start_cron_jobs():
    t = threading.Thread(target=run_schedule_loop, daemon=True)
    t.start()
