from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import json
import hmac
import hashlib
import os
import db_manager as db
import sms_manager as sms
import server.logen_service as logen

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
        base_url = _get_env(app_, "APP_BASE_URL", "https://dnbsir.com").rstrip("/")
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

@router.post("/webhook/missed-call")
def handle_missed_call(payload: MissedCallWebhook, request: Request):
    _check_token(request)
    ok, msg = sms.process_missed_call_webhook(payload.model_dump())
    db.log_sms(
        payload.store_id or "UNKNOWN",
        payload.caller_phone,
        "WEBHOOK",
        "missed_call",
        "OK" if ok else "FAIL",
        msg,
    )
    if ok:
        _send_test_notice(request.app)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@router.post("/api/webhook/call-detect")
async def handle_call_detect(request: Request):
    _check_token(request)
    payload = await request.json()
    normalized = _normalize_nhn_payload(request.app, payload)
    ok, msg = sms.process_missed_call_webhook(normalized)
    db.log_sms(
        normalized.get("store_id") or "UNKNOWN",
        normalized.get("caller_phone", ""),
        "WEBHOOK",
        "call_detect",
        "OK" if ok else "FAIL",
        msg,
    )
    if ok:
        _send_test_notice(request.app)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

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
