from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
import json
import hmac
import hashlib
import os
import db_manager as db
import sms_manager as sms
import server.logen_service as logen
import call_filter  # 수신/발신 판별 전용 모듈 — 이 파일만 수정하십시오

router = APIRouter()

class MissedCallWebhook(BaseModel):
    virtual_number: str
    caller_phone: str
    store_id: str | None = None
    store_name: str | None = None
    order_link: str | None = None

def _get_env(app_, key: str, default: str = "") -> str:
    return app_.extra.get(key, default)

def _extract_value(payload: dict, keys: list) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    return ""

def _normalize_nhn_payload(app_, payload: dict) -> dict:
    virtual_number = _extract_value(
        payload,
        ["virtual_number", "virtualNumber", "called", "callee", "to", "dn", "called_number", "vn"],
    )
    caller_phone = _extract_value(
        payload,
        ["caller_phone", "caller", "from", "ani", "src", "callerNumber", "caller_number"],
    )
    store_id = _extract_value(payload, ["store_id", "storeId", "merchant_id"])
    store_name = _extract_value(payload, ["store_name", "storeName", "merchant_name"])
    order_link = _extract_value(payload, ["order_link", "orderLink", "link"])
    if not order_link and store_id:
        base_url = _get_env(app_, "APP_BASE_URL", "https://dongnebiseo.com").rstrip("/")
        order_link = f"{base_url}/?id={store_id}"
    return {
        "virtual_number": virtual_number,
        "caller_phone": caller_phone,
        "store_id": store_id,
        "store_name": store_name,
        "order_link": order_link,
    }

def _check_token(request: Request) -> None:
    token = request.headers.get("X-Webhook-Token", "")
    expected = _get_env(request.app, "WEBHOOK_TOKEN", "")
    if expected and token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")

def _send_test_notice(app_):
    if not _get_env(app_, "ENABLE_WEBHOOK_TEST_NOTIFY", "true").lower().startswith("t"):
        return
    admin_phone = _get_env(app_, "ADMIN_ALERT_PHONE", "010-2384-7447")
    sms.send_cloud_sms(admin_phone, "연결 성공", store_id="SYSTEM")

def _process_async_missed_call_common(payload_dict: dict, app_, log_subtype: str):
    """
    백그라운드에서 부재중 전화/콜백 발송 및 DB 기록을 비동기로 처리
    """
    try:
        ok, msg, msg_content = sms.process_missed_call_webhook(payload_dict)
        db.log_sms(
            payload_dict.get("store_id") or "UNKNOWN",
            payload_dict.get("caller_phone") or "",
            "WEBHOOK",
            log_subtype,
            "OK" if ok else "FAIL",
            msg,
        )
        # Save to ai_call_logs for dashboard visibility
        try:
            event_type = "CALLBACK_SUCCESS" if ok else "CALLBACK_FAILED"
            db.save_ai_call_log(
                store_id=payload_dict.get("store_id") or "UNKNOWN",
                customer_phone=payload_dict.get("caller_phone") or "",
                customer_name="이름 미상",
                intent="부재중 전화",
                summary=f"부재중 전화 감지 ({log_subtype}). 자동 콜백 결과: {msg}",
                audio_url="",
                event_type=event_type,
                event_details=msg_content
            )
        except Exception as db_err:
            print(f"Failed to log call to ai_call_logs in webhook: {db_err}")

        if ok:
            _send_test_notice(app_)
    except Exception as e:
        print(f"[{log_subtype} Error] 백그라운드 처리 중 예외 발생: {e}")

@router.post("/webhook/missed-call")
async def handle_missed_call(payload: MissedCallWebhook, request: Request, background_tasks: BackgroundTasks):
    _check_token(request)
    background_tasks.add_task(
        _process_async_missed_call_common,
        payload.model_dump(),
        request.app,
        "missed_call"
    )
    return {"success": True, "message": "Callback queued"}

@router.post("/api/webhook/call-detect")
async def handle_call_detect(request: Request, background_tasks: BackgroundTasks):
    _check_token(request)
    payload = await request.json()
    normalized = _normalize_nhn_payload(request.app, payload)
    background_tasks.add_task(
        _process_async_missed_call_common,
        normalized,
        request.app,
        "call_detect"
    )
    return {"success": True, "message": "Callback queued"}

class CallRecordWebhook(BaseModel):
    store_id: str
    customer_phone: str
    audio_url: str

@router.post("/api/webhook/call-record")
async def handle_call_record(payload: CallRecordWebhook, request: Request):
    import ai_manager
    import db_manager as db
    import sms_manager as sms
    
    # 1. Parse Audio to Text
    transcript = await ai_manager.parse_call_audio(payload.audio_url)
    
    # 2. Summarize Text to JSON
    summary_data = await ai_manager.summarize_call_text(transcript)
    
    # 3. Save to AI Call Ledger DB
    customer_name = summary_data.get("name", "이름 미상")
    intent = summary_data.get("intent", "단순문의")
    summary_text = summary_data.get("summary", transcript)
    event_type = summary_data.get("event_type")
    event_details = summary_data.get("event_details")
    
    db.save_ai_call_log(
        store_id=payload.store_id,
        customer_phone=payload.customer_phone,
        customer_name=customer_name,
        intent=intent,
        summary=summary_text,
        audio_url=payload.audio_url,
        event_type=event_type,
        event_details=event_details
    )
    
    # 4. Notify Owner via AlimTalk (알림톡 전송)
    store = db.get_store(payload.store_id)
    owner_phone = store.get("phone") if store else ""
    if owner_phone:
        msg = f"[AI 통화 요약]\n방금 {customer_name} 고객님의 전화가 있었습니다.\n\n요건: {intent}\n요약: {summary_text}\n"
        if event_type:
             msg += f"\n🎉 캐치된 일정: [{event_type}] {event_details}"
        
        msg += f"\n\n사장님 앱의 'AI 장부'에서 상세 내용을 확인하세요."
        sms.send_alimtalk(owner_phone, msg, template_id="tmp_ai_call_summary", variables={"#{name}": customer_name, "#{intent}": intent})

    return {"success": True, "data": summary_data}

@router.post("/v1/payments/webhook")
async def payment_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Payment-Signature", "")

    webhook_secret = request.app.extra.get("PAYMENT_WEBHOOK_SECRET", "")

    expected_signature = hmac.new(
        webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()

    if not webhook_secret or not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=400, detail="유효하지 않은 신호입니다.")

    data = json.loads(payload)
    order_id = data.get("orderId")
    status = data.get("status")

    if status == "DONE":
        payment_method = data.get("paymentMethod") or data.get("method") or "CARD"
        db.update_payment_method(order_id, payment_method)
        db.update_order_status(order_id, "SUCCESS")
        await logen.send_to_logen(order_id)
        return {"message": "ok"}
    elif status in ["CANCELED", "ABORTED", "FAIL"]:
        await logen.process_refund(order_id)

    return {"message": "ignored"}

from solapi import SolapiMessageService

@router.post("/webhook/solapi")
async def solapi_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Solapi 발송 결과 리포트 수신 전용 — 메시지 발송 절대 없음
    (발송결과 콜백을 전화수신으로 착각해서 SMS 재발송하는 무한루프 완전 차단)
    """
    try:
        raw = await request.json()
        items = raw if isinstance(raw, list) else [raw]
        for data in items:
            if not isinstance(data, dict):
                continue
            msg_id  = data.get("messageId", "?")
            status  = data.get("statusCode", "?")
            to      = data.get("to", "?")
            print(f"[Solapi DeliveryReport] {msg_id} → {to} | status={status}")
        return {"status": "ok"}
    except Exception as e:
        print(f"[Solapi Webhook 에러]: {e}")
        return {"status": "error"}


# Old send_order_notification using sync call is replaced by sms.send_highway_alimtalk

class AndroidAppWebhook(BaseModel):
    phone_number: str | None = None
    customer_number: str | None = None
    call_type: str | None = None
    call_state: str | None = None  # RINGING, OFFHOOK, IDLE
    my_number: str | None = None
    auth_token: str | None = None

import time
from datetime import datetime, timedelta
from dongne_biseo.database import SessionLocal
from dongne_biseo import models

_recent_callbacks = {}  # (store_id, customer_phone) -> timestamp  [메모리 쿨다운 — 1차 방어]
_call_state_cache = {}   # (store_id, customer_phone) -> {state 정보}
COOLDOWN_SECONDS  = 3600  # 1시간

# ── 전역 Rate Limiter (분당 최대 발송 수) ────────────────────────────────
_rate_window_start = 0.0   # 현재 분 창 시작 시각
_rate_count        = 0     # 현재 분 창 내 발송 수
RATE_LIMIT_PER_MIN = 10    # 분당 최대 콜백 발송 수 (초과 시 차단)

def _check_rate_limit() -> bool:
    """True = 발송 허용, False = Rate Limit 초과 → 차단"""
    global _rate_window_start, _rate_count
    now = time.time()
    if now - _rate_window_start >= 60:
        _rate_window_start = now
        _rate_count = 0
    _rate_count += 1
    if _rate_count > RATE_LIMIT_PER_MIN:
        print(f"[RateLimit] 분당 {RATE_LIMIT_PER_MIN}건 초과 → 콜백 차단 (이번 분 {_rate_count}번째)")
        return False
    return True

def check_recent_callback_db(customer_phone: str, hours: int = 24) -> bool:
    """DB에서 N시간 이내에 동일 고객 번호로 발송된 성공한 콜백이 있는지 확인"""
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
    """콜백 발송 결과를 callback_logs 테이블에 기록"""
    db_session = SessionLocal()
    try:
        clean_sender = sender.replace("-", "").strip()
        clean_receiver = receiver.replace("-", "").strip()
        db_log = models.CallbackLog(
            sender=clean_sender,
            receiver=clean_receiver,
            comm_type=models.CommType.SMS,
            content=content[:500],  # truncate if too long
            status=models.CommStatus.SUCCESS if success else models.CommStatus.FAILED,
            created_at=datetime.utcnow()
        )
        db_session.add(db_log)
        db_session.commit()
    except Exception as e:
        print(f"[log_callback_sent Error] {e}")
    finally:
        db_session.close()

def _process_async_callback(customer_phone: str):
    """
    백그라운드 콜백 발송 — send_smart_callback 단일 경로 통일

    ★ 안전장치 5중 방어:
      1) smart_callback_on 스위치 확인
      2) 사장님 번호 자기발송 차단
      3) 메모리 쿨다운 (1시간, 재시작 초기화 가능 — 1차 방어)
      4) DB 쿨다운 (1시간 이내 성공 이력 체크 — 2차 방어, 재시작 후에도 유지)
      5) 전역 Rate Limiter (분당 최대 10건)
    """
    try:
        import config
        store_id = config.get_secret("SENDER_PHONE", "SYSTEM")

        # ── [1] smart_callback_on 스위치 ──────────────────────────────────
        store = db.get_store(store_id)
        if not store or not store.get("smart_callback_on", 0):
            print(f"[SmartCallback] 비활성화 상태 → 발송 중단 (store_id={store_id})")
            return

        # ── [2] 사장님 번호 자기발송 차단 (이중 확인) ────────────────────
        # store_id(=SENDER_PHONE 환경변수)와 DB에 등록된 phone 필드 둘 다 차단
        owner_phones = set()
        owner_phones.add(re.sub(r'[^0-9]', '', store_id))  # SENDER_PHONE
        _owner_db_phone = (store or {}).get("phone", "")
        if _owner_db_phone:
            owner_phones.add(re.sub(r'[^0-9]', '', _owner_db_phone))
        clean_customer = re.sub(r'[^0-9]', '', customer_phone)
        if clean_customer in owner_phones:
            print(f"[SmartCallback] 차단: 사장님 번호에 발송 불가 ({customer_phone})")
            return

        # ── [3] 메모리 쿨다운 (1시간, 1차 방어) ──────────────────────────
        now = time.time()
        key = (store_id, customer_phone)
        if now - _recent_callbacks.get(key, 0) < COOLDOWN_SECONDS:
            elapsed = (now - _recent_callbacks[key]) / 60
            print(f"[SmartCallback Cooldown(메모리)] {elapsed:.1f}분 전 발송 → 차단: {customer_phone}")
            return

        # ── [4] DB 쿨다운 (1시간, 2차 방어 — 재시작 후에도 유지) ─────────
        if check_recent_callback_db(customer_phone, hours=1):
            print(f"[SmartCallback Cooldown(DB)] 1시간 이내 발송 이력 있음 → 차단: {customer_phone}")
            return

        # ── [5] 전역 Rate Limiter ─────────────────────────────────────────
        if not _check_rate_limit():
            print(f"[SmartCallback RateLimit] 분당 한도 초과 → 차단: {customer_phone}")
            return

        # 여기까지 통과하면 발송 확정 — 메모리 쿨다운 등록
        _recent_callbacks[key] = now

        store_name = (store or {}).get("name", "동네비서")
        print(f"[SmartCallback] 발송 시작 → 고객: {customer_phone} / 가게: {store_id}")

        # ── SMS 발송 ──────────────────────────────────────────────────────
        success, ret_msg, msg_content = sms.send_smart_callback(
            store_id=store_id,
            customer_phone=customer_phone,
            store_name=store_name
        )
        print(f"[SmartCallback] {'성공' if success else '실패'}: {ret_msg}")

        # ── DB 로그 기록 (callback_logs — 중복방지용) ────────────────────
        try:
            log_callback_sent(
                sender=customer_phone,
                receiver=store_id,
                content=msg_content,
                success=success
            )
        except Exception as log_err:
            print(f"[SmartCallback] callback_logs 기록 실패: {log_err}")

        # ── AI 장부 로그 기록 ─────────────────────────────────────────────
        try:
            db.save_ai_call_log(
                store_id=store_id,
                customer_phone=customer_phone,
                customer_name="이름 미상",
                intent="부재중 콜백",
                summary=f"SMS 콜백 → {customer_phone}: {ret_msg}",
                audio_url="",
                event_type="CALLBACK_SUCCESS" if success else "CALLBACK_FAILED",
                event_details=msg_content
            )
        except Exception as db_err:
            print(f"[SmartCallback] AI 장부 기록 실패: {db_err}")

    except Exception as e:
        print(f"[SmartCallback Error] {e}")

@router.api_route("/webhook", methods=["GET", "POST"])
@router.api_route("/webhook/", methods=["GET", "POST"])  # 구버전 앱 슬래시 포함 URL 대응
async def android_app_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    안드로이드 앱에서 통화 수신/부재중 감지 시 호출되는 웹훅.
    - POST: 신규 APK (HTTPS 직접 전송)
    - GET:  구버전 APK (301 리다이렉트로 POST→GET 변환된 경우 호환 처리)
    """
    import config
    import re

    APP_API_TOKEN = os.environ.get("APP_API_TOKEN", "DONGNE_BISEO_APP_SECRET_2026_!@")

    # ── 페이로드 파싱 (POST=JSON body, GET=query string) ──────────────
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
        customer_phone = body.get("customer_number") or body.get("phone_number", "")
        call_state     = body.get("call_state", "").upper().strip()
        # call_type 기본값을 빈 문자열로 — 알 수 없는 전화는 발신으로 간주하지 않음
        call_type      = body.get("call_type", "").strip()
        auth_token     = body.get("auth_token", "")
    else:  # GET (구버전 앱 호환)
        params         = dict(request.query_params)
        customer_phone = params.get("customer_number") or params.get("phone_number", "")
        call_state     = params.get("call_state", "").upper().strip()
        call_type      = params.get("call_type", "").strip()
        auth_token     = params.get("auth_token", "")

    # 인증
    token = auth_token or request.headers.get("X-Webhook-Token", "")
    if token and token != APP_API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not customer_phone:
        return {"result": "ignored", "message": "전화번호가 없습니다."}

    customer_phone = re.sub(r'[^0-9]', '', customer_phone)
    if not customer_phone.startswith("01") or len(customer_phone) < 9:
        return {"result": "ignored", "message": "유효하지 않은 휴대폰 번호입니다."}

    store_id = config.get_secret("SENDER_PHONE", "SYSTEM")

    # ── 발신 전화 제일 먼저 차단 (항상 유효) ──────────────────────────
    if call_filter.is_outgoing(call_type):
        print(f"[Webhook] 발신전화 차단: {customer_phone}")
        return {"result": "ignored", "message": "발신전화 — 발송 안 함"}

    # ── State Machine (POST 신규 앱) ───────────────────────────────────────
    if call_state and request.method == "POST":
        key   = (store_id, customer_phone)
        entry = _call_state_cache.get(key) or {
            "previous_state": None, "current_state": None,
            "has_ringing": False, "updated_at": 0.0
        }
        prev_state = entry["current_state"]
        entry.update({"previous_state": prev_state, "current_state": call_state, "updated_at": time.time()})
        if call_state == "RINGING":
            entry["has_ringing"] = True
        _call_state_cache[key] = entry
        print(f"[State Machine] {customer_phone}: {prev_state} → {call_state}")

        if call_state == call_filter.STATE_IDLE:
            should_send, reason = call_filter.should_send_sms_state_machine(
                prev_state, call_state, entry.get("has_ringing", False)
            )
            _call_state_cache.pop(key, None)
            if should_send:
                print(f"[State Machine] {reason} → SMS 발송: {customer_phone}")
                background_tasks.add_task(_process_async_callback, customer_phone)
                return {"result": "success", "message": f"{reason} — SMS 발송 등록"}
            print(f"[State Machine] {reason}: {customer_phone}")
            return {"result": "ignored", "message": reason}
        return {"result": "ignored", "message": f"상태 캐싱 ({call_state})"}

    # ── GET 구버전 앱 / 레거시 폴백 ─────────────────────────────────────
    should_send, reason = call_filter.should_send_sms_legacy(call_type, call_state)
    if should_send:
        print(f"[Legacy] {reason} → SMS 발송: {customer_phone}")
        background_tasks.add_task(_process_async_callback, customer_phone)
        return {"result": "success", "message": f"{reason} — SMS 발송 등록"}

    print(f"[Legacy] 차단: {reason} ({customer_phone})")
    return {"result": "ignored", "message": reason}
