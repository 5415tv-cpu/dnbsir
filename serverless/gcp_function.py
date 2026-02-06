import json
import os

import sms_manager as sms


def _get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _extract_value(payload: dict, keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    return ""


def _normalize_payload(payload: dict) -> dict:
    virtual_number = _extract_value(
        payload,
        ["virtual_number", "virtualNumber", "called", "callee", "to", "dn", "called_number"],
    )
    caller_phone = _extract_value(
        payload,
        ["caller_phone", "caller", "from", "ani", "src", "callerNumber"],
    )
    store_id = _extract_value(payload, ["store_id", "storeId", "merchant_id"])
    store_name = _extract_value(payload, ["store_name", "storeName", "merchant_name"])
    order_link = _extract_value(payload, ["order_link", "orderLink", "link"])
    if not order_link and store_id:
        base_url = _get_env("APP_BASE_URL", "https://dnbsir.com").rstrip("/")
        order_link = f"{base_url}/?id={store_id}"

    return {
        "virtual_number": virtual_number,
        "caller_phone": caller_phone,
        "store_id": store_id,
        "store_name": store_name,
        "order_link": order_link,
    }


def _validate_token(request) -> bool:
    expected = _get_env("WEBHOOK_TOKEN", "")
    if not expected:
        return True
    token = request.headers.get("X-Webhook-Token") or request.args.get("token")
    if token and token.startswith("Bearer "):
        token = token.replace("Bearer ", "").strip()
    return token == expected


def missed_call_webhook(request):
    if not _validate_token(request):
        return ("Unauthorized", 401)

    payload = request.get_json(silent=True) or {}
    if not payload:
        payload = request.form.to_dict() if request.form else {}
    if "data" in payload and isinstance(payload["data"], str):
        try:
            payload = json.loads(payload["data"])
        except Exception:
            pass

    normalized = _normalize_payload(payload)
    ok, msg = sms.process_missed_call_webhook(normalized)
    if not ok:
        return (msg, 500)
    return ("OK", 200)
