from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
import json
import hmac
import hashlib
import os
import re
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
    백그라운드에서 부재중 전화/콜백 발송 및 DB 기록을 비동기로 처리 (callback_manager 연동)
    """
    try:
        import callback_manager
        ok, msg = callback_manager.handle_incoming_callback_event(
            event_source=f"telecom_server_{log_subtype}",
            customer_phone=payload_dict.get("caller_phone") or "",
            store_id=payload_dict.get("store_id")
        )
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
COOLDOWN_SECONDS  = 300   # ★ 5분 (테스트용 — 운영 전환 시 3600으로 복원)

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

def _process_async_callback(customer_phone: str, _log_id=None):
    """
    백그라운드 콜백 발송 — callback_manager를 통한 단일 추상화 경로 처리
    """
    try:
        import callback_manager
        callback_manager.handle_incoming_callback_event(
            event_source="android_app",
            customer_phone=customer_phone,
            log_id=_log_id
        )
    except Exception as e:
        print(f"[SmartCallback Error] {e}")

@router.api_route("/webhook", methods=["GET", "POST"])
@router.api_route("/webhook/", methods=["GET", "POST"])  # 구버전 앱 슬래시 포함 URL 대응
async def android_app_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    안드로이드 앱에서 통화 수신/부재중 감지 시 호출되는 웹훅.
    ★ 블랙박스: 인증/처리 결과와 무관하게 수신 즉시 webhook_logs에 기록
    """
    import config, json as _json
    import re

    APP_API_TOKEN = os.environ.get("APP_API_TOKEN", "DONGNE_BISEO_APP_SECRET_2026_!@")
    source_ip = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or str(request.client.host)

    # ── 페이로드 파싱 ────────────────────────────────────────────────────
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
        customer_phone = body.get("customer_number") or body.get("phone_number", "")
        call_state     = body.get("call_state", "").upper().strip()
        call_type      = body.get("call_type", "").strip()
        auth_token     = body.get("auth_token", "")
        raw_payload    = _json.dumps(body, ensure_ascii=False)[:2000]
    else:
        params         = dict(request.query_params)
        customer_phone = params.get("customer_number") or params.get("phone_number", "")
        call_state     = params.get("call_state", "").upper().strip()
        call_type      = params.get("call_type", "").strip()
        auth_token     = params.get("auth_token", "")
        raw_payload    = _json.dumps(params, ensure_ascii=False)[:2000]

    # ── ★ 블랙박스: 수신 즉시 기록 ──────────────────────────────────────
    _log_id = None
    try:
        _log_id = db.save_webhook_log(
            source_ip=source_ip,
            method=request.method,
            path=str(request.url.path),
            auth_ok=0,
            customer_phone=customer_phone,
            call_state=call_state,
            call_type=call_type,
            raw_payload=raw_payload,
            stage='RECEIVED',
        )
    except Exception as _le:
        print(f"[BlackBox] 초기 기록 실패: {_le}")

    def _log(stage, result_msg='', sms_sent=0, auth_ok=None):
        """처리 단계 업데이트 헬퍼"""
        try:
            kw = dict(stage=stage, result_msg=result_msg, sms_sent=sms_sent)
            if auth_ok is not None:
                kw['auth_ok'] = auth_ok
            db.update_webhook_log(_log_id, **kw)
        except Exception:
            pass

    # ── 인증: 다중 토큰 허용 (토큰 만료/교체 시에도 중단 없음) ────────────
    # 우선순위: 1) POST body auth_token  2) X-Webhook-Token 헤더
    token = auth_token or request.headers.get("X-Webhook-Token", "")

    # 유효 토큰 집합 — 주 토큰 + 백업 토큰 모두 허용
    _primary  = os.environ.get("APP_API_TOKEN",        "DONGNE_BISEO_APP_SECRET_2026_!@")
    _backup   = os.environ.get("APP_API_TOKEN_BACKUP", "DONGNE_BISEO_PERMANENT_KEY")
    valid_tokens = {t for t in [_primary, _backup] if t}

    if token and token not in valid_tokens:
        _log('AUTH_FAIL', f'인증 토큰 불일치 (수신: {token[:10]}...)', auth_ok=0)
        # ★ AUTH_FAIL 발생 즉시 관리자에게 SMS 경보
        try:
            admin_phone = os.environ.get("ADMIN_ALERT_PHONE", "01023847447")
            sms.send_cloud_sms(
                admin_phone,
                f"[동네비서 경보] 콜백 인증 실패!\n수신 토큰: {token[:12]}...\nIP: {source_ip}\n→ 앱 토큰이 서버와 달라졌습니다. 즉시 확인 필요.",
                store_id="SYSTEM"
            )
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Unauthorized")
    _log('RECEIVED', '인증 통과', auth_ok=1)

    if not customer_phone:
        _log('PHONE_INVALID', '전화번호 없음')
        return {"result": "ignored", "message": "전화번호가 없습니다."}

    customer_phone = re.sub(r'[^0-9]', '', customer_phone)
    if not customer_phone.startswith("01") or len(customer_phone) < 9:
        _log('PHONE_INVALID', f'유효하지 않은 번호: {customer_phone}')
        return {"result": "ignored", "message": "유효하지 않은 휴대폰 번호입니다."}

    # 전화번호 확정 후 업데이트
    try:
        db.update_webhook_log(_log_id, customer_phone=customer_phone)
    except Exception:
        pass

    store_id = config.get_secret("SENDER_PHONE", "SYSTEM")

    # ── 발신 차단 ────────────────────────────────────────────────────────
    if call_filter.is_outgoing(call_type):
        print(f"[Webhook] 발신전화 차단: {customer_phone}")
        _log('OUTGOING_SKIP', '발신전화 — 발송 안 함')
        return {"result": "ignored", "message": "발신전화 — 발송 안 함"}

    # ── State Machine (POST 신규 앱) ─────────────────────────────────────
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
                _log('SMS_QUEUED', reason)
                background_tasks.add_task(_process_async_callback, customer_phone, _log_id)
                return {"result": "success", "message": f"{reason} — SMS 발송 등록"}
            _log('COOLDOWN' if '쿨다운' in reason or 'Cooldown' in reason else 'STATE_CACHED', reason)
            print(f"[State Machine] {reason}: {customer_phone}")
            return {"result": "ignored", "message": reason}
        _log('STATE_CACHED', f'상태 캐싱 ({call_state})')
        return {"result": "ignored", "message": f"상태 캐싱 ({call_state})"}

    # ── GET 구버전 앱 / 레거시 폴백 ─────────────────────────────────────
    should_send, reason = call_filter.should_send_sms_legacy(call_type, call_state)
    if should_send:
        print(f"[Legacy] {reason} → SMS 발송: {customer_phone}")
        _log('SMS_QUEUED', reason)
        background_tasks.add_task(_process_async_callback, customer_phone, _log_id)
        return {"result": "success", "message": f"{reason} — SMS 발송 등록"}

    _log('COOLDOWN' if '쿨다운' in reason else 'STATE_CACHED', reason)
    print(f"[Legacy] 차단: {reason} ({customer_phone})")
    return {"result": "ignored", "message": reason}


# ═══════════════════════════════════════════════════════════
# 토스페이먼츠 결제 웹훅 (결제 완료/취소 서버 알림)
# 토스 개발자센터 → 웹훅 메뉴에 아래 URL 등록:
#   https://dongnebiseo.com/api/toss/webhook
# ═══════════════════════════════════════════════════════════
@router.post("/api/toss/webhook")
async def toss_payment_webhook(request: Request, background_tasks: BackgroundTasks):
    """토스페이먼츠 결제 완료/취소 웹훅 수신"""
    try:
        payload_bytes = await request.body()
        payload = json.loads(payload_bytes)
    except Exception as e:
        print(f"[Toss Webhook] 페이로드 파싱 실패: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # 서명 검증 (TOSS_WEBHOOK_SECRET 환경변수 사용)
    webhook_secret = os.environ.get("TOSS_WEBHOOK_SECRET", "")
    if webhook_secret:
        signature = request.headers.get("TossPayments-Signature", "")
        expected = hmac.new(
            webhook_secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            print("[Toss Webhook] 서명 불일치 — 거부")
            raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = payload.get("eventType", "")
    data = payload.get("data", {})
    order_id = data.get("orderId", "")
    payment_key = data.get("paymentKey", "")
    status = data.get("status", "")
    amount = data.get("totalAmount", 0)

    print(f"[Toss Webhook] 이벤트: {event_type} | 주문: {order_id} | 상태: {status} | 금액: {amount}")

    # 결제 완료 처리
    if event_type == "PAYMENT_STATUS_CHANGED" and status == "DONE":
        print(f"[Toss Webhook] ✅ 결제 완료: {order_id} / {amount}원")
        # 마켓 주문이면 상태 업데이트
        if order_id.startswith("MK-"):
            try:
                db.update_market_order_status(order_id, "PAID", payment_key) if hasattr(db, "update_market_order_status") else None
            except Exception as e:
                print(f"[Toss Webhook] 마켓 주문 상태 업데이트 실패: {e}")
        # 택배 주문이면 상태 업데이트
        elif order_id.startswith("COURIER-"):
            try:
                db.update_delivery_order_status(order_id, "REQUESTED") if hasattr(db, "update_delivery_order_status") else None
            except Exception as e:
                print(f"[Toss Webhook] 택배 주문 상태 업데이트 실패: {e}")

    # 결제 취소 처리
    elif event_type == "PAYMENT_STATUS_CHANGED" and status in ("CANCELED", "PARTIAL_CANCELED"):
        print(f"[Toss Webhook] ❌ 결제 취소: {order_id}")

    return {"result": "ok"}
