"""
📞 Callback Manager & Decoupled Abstraction Layer
- Normalizes raw incoming callback events (Android App or Telecom Webhook)
- Executes rate limits, cooldowns, and validation logic
- Dispatches messages via Solapi SMS/Alimtalk
- Logs telemetry data (unified logs, callback logs, AI call logs)
"""
import time
import re
from datetime import datetime, timedelta
import db_manager as db
import sms_manager as sms
import config
from dongne_biseo.database import SessionLocal
from dongne_biseo import models

# Cooldown memory cache
_recent_callbacks = {}
COOLDOWN_SECONDS = 300
RATE_LIMIT_PER_MIN = 10
_rate_window_start = 0.0
_rate_count = 0

def check_recent_callback_db(customer_phone: str, hours: float = 5/60) -> bool:
    """DB check for recent successful callbacks (default 5 mins)"""
    db_session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        clean_phone = customer_phone.replace("-", "").strip()
        recent = db_session.query(models.CallbackLog).filter(
            models.CallbackLog.sender == clean_phone,
            models.CallbackLog.status == models.CommStatus.SUCCESS,
            models.CallbackLog.created_at >= cutoff
        ).first()
        return recent is not None
    except Exception as e:
        print(f"[check_recent_callback_db Error] {e}")
        return False
    finally:
        db_session.close()

def log_callback_sent(sender: str, receiver: str, content: str, success: bool):
    """Save record to callback_logs DB"""
    db_session = SessionLocal()
    try:
        clean_sender = sender.replace("-", "").strip()
        clean_receiver = receiver.replace("-", "").strip()
        db_log = models.CallbackLog(
            sender=clean_sender,
            receiver=clean_receiver,
            comm_type=models.CommType.SMS,
            content=content[:500],
            status=models.CommStatus.SUCCESS if success else models.CommStatus.FAILED,
            created_at=datetime.utcnow()
        )
        db_session.add(db_log)
        db_session.commit()
    except Exception as e:
        print(f"[log_callback_sent Error] {e}")
    finally:
        db_session.close()

def check_rate_limit() -> bool:
    """Rate limit safeguard (Max 10 messages per minute)"""
    global _rate_window_start, _rate_count
    now = time.time()
    if now - _rate_window_start >= 60:
        _rate_window_start = now
        _rate_count = 0
    _rate_count += 1
    if _rate_count > RATE_LIMIT_PER_MIN:
        print(f"[RateLimit] Callback rate limit exceeded ({RATE_LIMIT_PER_MIN}/min)")
        return False
    return True

def handle_incoming_callback_event(
    event_source: str,  # "android_app" or "telecom_server"
    customer_phone: str,
    store_id: str = None,
    log_id: int = None
):
    """
    Decoupled unified entry point for all callback events.
    Normalizes inputs, applies business rules, dispatches messages, and saves logs.
    """
    try:
        # 1. Normalize phone numbers
        customer_phone = re.sub(r'[^0-9]', '', customer_phone)
        if not customer_phone.startswith("01") or len(customer_phone) < 9:
            print(f"[CallbackManager] Ignored: Invalid phone number '{customer_phone}'")
            if log_id:
                db.update_webhook_log(log_id, stage='PHONE_INVALID', result_msg=f'Invalid phone: {customer_phone}')
            return False, "Invalid customer phone number"

        # 2. Get store info and determine store_id
        if not store_id:
            store_id = config.get_secret("SENDER_PHONE", "SYSTEM")
            
        store = db.get_store(store_id)
        if not store:
            print(f"[CallbackManager] Store not found: {store_id}")
            if log_id:
                db.update_webhook_log(log_id, stage='STORE_NOT_FOUND', result_msg=f'Store {store_id} not found')
            return False, "Store not found"

        store_name = store.get("name", "동네비서")

        # 3. Check if smart callbacks are enabled
        if store.get("smart_callback_on", 1) == 0:
            print(f"[CallbackManager] Blocked: Callback disabled (smart_callback_on=0) for store {store_id}")
            if log_id:
                db.update_webhook_log(log_id, stage='DISABLED_BY_USER', result_msg='smart_callback_on is off')
            return False, "Callbacks disabled for this store"

        # 4. Self-calling protection
        owner_phones = set()
        owner_phones.add(re.sub(r'[^0-9]', '', store_id))
        owner_db_phone = store.get("phone", "")
        if owner_db_phone:
            owner_phones.add(re.sub(r'[^0-9]', '', owner_db_phone))
            
        if customer_phone in owner_phones:
            print(f"[CallbackManager] Blocked: Self-calling detected for phone {customer_phone}")
            if log_id:
                db.update_webhook_log(log_id, stage='SELF_CALL_SKIP', result_msg='Self-calling blocked')
            return False, "Self-calling skipped"

        # 5. Cooldown checks (Only apply memory/DB cooldowns to real notifications, not system calls)
        now = time.time()
        cooldown_key = (store_id, customer_phone)
        
        # 5a. Memory cooldown check
        if now - _recent_callbacks.get(cooldown_key, 0) < COOLDOWN_SECONDS:
            elapsed = (now - _recent_callbacks[cooldown_key]) / 60
            print(f"[CallbackManager] Blocked: Cooldown active (Memory: {elapsed:.1f}m) for {customer_phone}")
            if log_id:
                db.update_webhook_log(log_id, stage='COOLDOWN', result_msg='Memory cooldown active')
            return False, "Memory cooldown active"

        # 5b. DB cooldown check
        if check_recent_callback_db(customer_phone, hours=COOLDOWN_SECONDS/3600):
            print(f"[CallbackManager] Blocked: Cooldown active (DB: 5m) for {customer_phone}")
            if log_id:
                db.update_webhook_log(log_id, stage='COOLDOWN', result_msg='DB cooldown active')
            return False, "DB cooldown active"

        # 5c. Global rate limiter
        if not check_rate_limit():
            print(f"[CallbackManager] Blocked: Global rate limit reached for {customer_phone}")
            if log_id:
                db.update_webhook_log(log_id, stage='RATE_LIMITED', result_msg='Rate limit reached')
            return False, "Rate limit active"

        # 6. Pass validation - Update memory cooldown
        _recent_callbacks[cooldown_key] = now

        # 7. Send the callback message
        print(f"[CallbackManager] Dispatching callback ({event_source}) -> customer={customer_phone}, store={store_id}")
        success, ret_msg, msg_content = sms.send_smart_callback(
            store_id=store_id,
            customer_phone=customer_phone,
            store_name=store_name
        )

        # 8. Update webhook tracking log
        if log_id:
            db.update_webhook_log(
                log_id,
                stage='SMS_OK' if success else 'SMS_FAIL',
                result_msg=ret_msg[:500],
                sms_sent=1 if success else -1
            )

        # 9. Log to DB Callback logs (for cooldown tracking)
        try:
            log_callback_sent(
                sender=customer_phone,
                receiver=store_id,
                content=msg_content,
                success=success
            )
        except Exception as err:
            print(f"[CallbackManager] Failed to write callback log: {err}")

        # 10. Log to Unified AI Call Log
        try:
            db.save_ai_call_log(
                store_id=store_id,
                customer_phone=customer_phone,
                customer_name="이름 미상",
                intent=f"콜백 ({event_source})",
                summary=f"자동 콜백 결과: {ret_msg}",
                audio_url="",
                event_type="CALLBACK_SUCCESS" if success else "CALLBACK_FAILED",
                event_details=msg_content
            )
        except Exception as err:
            print(f"[CallbackManager] Failed to write unified AI call log: {err}")

        return success, ret_msg

    except Exception as e:
        print(f"[CallbackManager Error] Exception occurred: {e}")
        if log_id:
            db.update_webhook_log(log_id, stage='ERROR', result_msg=str(e)[:500])
        return False, str(e)
