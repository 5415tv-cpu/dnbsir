"""
탄탄제작소 결제 & 크레딧 & SMS OTP API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
엔드포인트:
  POST /api/tantan/otp/send      SMS OTP 발송
  POST /api/tantan/otp/verify    OTP 인증 → 세션 토큰 발급
  GET  /api/tantan/credit        잔여 크레딧 조회
  POST /api/tantan/credit/use    영상 제작 시 1크레딧 차감
  POST /api/tantan/payment/prepare  토스 결제 준비
  GET  /api/tantan/payment/success  토스 성공 콜백
  GET  /api/tantan/payment/fail     토스 실패 콜백
  GET  /api/tantan/admin/credits    관리자: 전체 크레딧 현황
  POST /api/tantan/admin/grant      관리자: 수동 크레딧 지급
"""
from __future__ import annotations

import base64, logging, os, random, string, uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import redis

logger = logging.getLogger("tantan.payment")

router = APIRouter(prefix="/api/tantan", tags=["tantan-payment"])

# ── Redis 연결 ──────────────────────────────────────────────────
_redis: Optional[redis.Redis] = None

def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        url = os.environ.get("CELERY_RESULT_BACKEND",
                             os.environ.get("REDIS_URL", "redis://localhost:6379/1"))
        _redis = redis.from_url(url, decode_responses=True)
    return _redis

# ── 상수 ────────────────────────────────────────────────────────
PACKAGES = {
    "pkg_1": {"credits": 1, "amount": 4000,  "label": "영상 1개"},
    "pkg_3": {"credits": 3, "amount": 12000, "label": "영상 3개"},
    "pkg_5": {"credits": 5, "amount": 18000, "label": "영상 5개"},
}
OTP_EXPIRE    = 300   # OTP 5분
SESSION_EXPIRE = 86400 # 세션 24시간

TOSS_SK  = os.environ.get("TOSS_SECRET_KEY", "")
TOSS_CK  = os.environ.get("TOSS_CLIENT_KEY", "")
SOLAPI_API_KEY    = os.environ.get("SOLAPI_API_KEY", "")
SOLAPI_API_SECRET = os.environ.get("SOLAPI_API_SECRET", "")
SOLAPI_FROM       = os.environ.get("SOLAPI_SENDER_NUMBER",
                    os.environ.get("SENDER_PHONE", ""))
ADMIN_SECRET      = os.environ.get("TANTAN_ADMIN_SECRET", "tantan-admin-2024")

BASE_URL = os.environ.get("TANTAN_BASE_URL", "https://tantanfab.com")


# ── SMS OTP 발송 (솔라피) ──────────────────────────────────
def _send_sms(phone: str, code: str) -> bool:
    """솔라피 SMS로 OTP 발송. 키 없으면 개발 모드(로그 출력)."""
    if not SOLAPI_API_KEY:
        logger.warning(f"[DEV MODE] {phone} OTP={code} (SOLAPI_API_KEY 미설정)")
        return True  # 개발 모드: 항상 성공
    try:
        import hashlib, hmac as _hmac, time
        from datetime import datetime, timezone
        # 솔라피는 ISO 8601 날짜 형식 필요 (밀리초 타임스탬프 아님)
        date_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        salt     = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        signature = _hmac.new(
            SOLAPI_API_SECRET.encode(),
            (date_iso + salt).encode(),
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "Authorization": (
                f"HMAC-SHA256 apiKey={SOLAPI_API_KEY}, "
                f"date={date_iso}, salt={salt}, signature={signature}"
            ),
            "Content-Type": "application/json",
        }
        phone_clean = phone.replace("-", "")
        payload = {
            "message": {
                "to":   phone_clean,
                "from": SOLAPI_FROM.replace("-", ""),
                "text": f"[탄탄제작소] 인증번호 {code}\n5분 이내 입력해 주세요.",
            }
        }
        import requests as req
        r = req.post(
            "https://api.solapi.com/messages/v4/send",
            json=payload, headers=headers, timeout=10
        )
        # SMS 로그 저장
        try:
            from routers.tantan_admin import record_sms_log
            record_sms_log(
                phone=phone,
                code=code,
                status="success" if r.status_code == 200 else "failed",
                response=r.text[:300],
            )
        except Exception:
            pass
        if r.status_code == 200:
            return True
        logger.error(f"솔라피 응답 {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        logger.error(f"SMS 발송 실패: {e}")
        return False


def _redis_key_otp(phone: str)     -> str: return f"tantan:otp:{phone}"
def _redis_key_credit(phone: str)  -> str: return f"tantan:credit:{phone}"
def _redis_key_session(token: str) -> str: return f"tantan:session:{token}"
def _redis_key_payment(oid: str)   -> str: return f"tantan:payment:{oid}"


def _verify_session(token: str) -> Optional[str]:
    """세션 토큰 → 전화번호 반환. 유효하지 않으면 None."""
    if not token:
        return None
    rdb = _get_redis()
    return rdb.get(_redis_key_session(token))


# ── 요청 모델 ────────────────────────────────────────────────────
class OtpSendReq(BaseModel):
    phone: str = Field(..., pattern=r"^01[016789]\d{7,8}$")

class OtpVerifyReq(BaseModel):
    phone: str
    code:  str

class PaymentPrepareReq(BaseModel):
    package_id: str
    phone:      str


# ─────────────────────────────────────────────────────────────────
# 1. OTP 발송
# ─────────────────────────────────────────────────────────────────
@router.post("/otp/send")
async def otp_send(req: OtpSendReq):
    rdb  = _get_redis()
    code = f"{random.randint(100000, 999999)}"
    rdb.setex(_redis_key_otp(req.phone), OTP_EXPIRE, code)
    ok = _send_sms(req.phone, code)
    if not ok:
        raise HTTPException(503, "SMS 발송 실패. 잠시 후 다시 시도해주세요.")
    dev_mode = not bool(SOLAPI_API_KEY)
    resp = {"success": True, "expires_in": OTP_EXPIRE}
    if dev_mode:
        resp["dev_code"] = code  # 개발 모드에서만 코드 노출
    return resp


# ─────────────────────────────────────────────────────────────────
# 2. OTP 검증 → 세션 발급
# ─────────────────────────────────────────────────────────────────
@router.post("/otp/verify")
async def otp_verify(req: OtpVerifyReq):
    rdb      = _get_redis()
    stored   = rdb.get(_redis_key_otp(req.phone))
    if not stored or stored != req.code.strip():
        raise HTTPException(401, "인증번호가 올바르지 않거나 만료됐습니다.")

    rdb.delete(_redis_key_otp(req.phone))  # 1회 사용 후 삭제

    token = str(uuid.uuid4())
    rdb.setex(_redis_key_session(token), SESSION_EXPIRE, req.phone)

    credits = int(rdb.get(_redis_key_credit(req.phone)) or 0)
    return {"success": True, "session_token": token, "credits": credits}


# ─────────────────────────────────────────────────────────────────
# 3. 크레딧 조회
# ─────────────────────────────────────────────────────────────────
@router.get("/credit")
async def get_credit(x_session_token: str = Header(default="")):
    phone = _verify_session(x_session_token)
    if not phone:
        raise HTTPException(401, "인증이 필요합니다.")
    rdb     = _get_redis()
    credits = int(rdb.get(_redis_key_credit(phone)) or 0)
    return {"phone": phone[-4:], "credits": credits}


# ─────────────────────────────────────────────────────────────────
# 4. 크레딧 차감 (영상 제작 시 호출)
# ─────────────────────────────────────────────────────────────────
@router.post("/credit/use")
async def use_credit(x_session_token: str = Header(default="")):
    phone = _verify_session(x_session_token)
    if not phone:
        raise HTTPException(401, "인증이 필요합니다.")
    rdb     = _get_redis()
    credits = int(rdb.get(_redis_key_credit(phone)) or 0)
    if credits <= 0:
        raise HTTPException(402, "크레딧이 부족합니다. 먼저 구매해주세요.")
    new_credits = rdb.decr(_redis_key_credit(phone))
    logger.info(f"크레딧 차감: {phone} → 잔여 {new_credits}개")
    return {"success": True, "remaining": new_credits}


# ─────────────────────────────────────────────────────────────────
# 5. 토스 결제 준비
# ─────────────────────────────────────────────────────────────────
@router.post("/payment/prepare")
async def payment_prepare(req: PaymentPrepareReq,
                           x_session_token: str = Header(default="")):
    phone = _verify_session(x_session_token)
    if not phone:
        raise HTTPException(401, "인증이 필요합니다.")
    if req.package_id not in PACKAGES:
        raise HTTPException(400, "유효하지 않은 패키지입니다.")

    pkg      = PACKAGES[req.package_id]
    order_id = f"TT-{uuid.uuid4().hex[:12].upper()}"

    rdb = _get_redis()
    rdb.setex(_redis_key_payment(order_id), 3600, f"{phone}|{req.package_id}")

    return {
        "order_id":    order_id,
        "amount":      pkg["amount"],
        "label":       pkg["label"],
        "client_key":  TOSS_CK,
        "success_url": f"{BASE_URL}/api/tantan/payment/success",
        "fail_url":    f"{BASE_URL}/api/tantan/payment/fail",
    }


# ─────────────────────────────────────────────────────────────────
# 6. 토스 결제 성공 콜백
# ─────────────────────────────────────────────────────────────────
@router.get("/payment/success", response_class=HTMLResponse)
async def payment_success(
    paymentKey: str = Query(...),
    orderId:    str = Query(...),
    amount:     int = Query(...),
):
    rdb      = _get_redis()
    meta     = rdb.get(_redis_key_payment(orderId))
    if not meta:
        return _result_html(False, "주문 정보를 찾을 수 없습니다.")

    phone, pkg_id = meta.split("|")
    pkg = PACKAGES.get(pkg_id)
    if not pkg or pkg["amount"] != amount:
        return _result_html(False, "결제 금액이 맞지 않습니다.")

    # 토스 결제 확인
    enc = base64.b64encode(f"{TOSS_SK}:".encode()).decode()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.tosspayments.com/v1/payments/confirm",
                json={"paymentKey": paymentKey, "orderId": orderId, "amount": amount},
                headers={"Authorization": f"Basic {enc}",
                         "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            msg = resp.json().get("message", "결제 승인 실패")
            return _result_html(False, msg)
    except Exception as e:
        return _result_html(False, str(e))

    # 크레딧 지급
    new_credits = rdb.incrby(_redis_key_credit(phone), pkg["credits"])
    rdb.delete(_redis_key_payment(orderId))
    logger.info(f"결제 완료: {phone} +{pkg['credits']}크레딧 (주문:{orderId})")

    return _result_html(True, f"{pkg['label']} 구매 완료! 잔여 크레딧: {new_credits}개",
                        credits=new_credits)


# ─────────────────────────────────────────────────────────────────
# 7. 토스 결제 실패 콜백
# ─────────────────────────────────────────────────────────────────
@router.get("/payment/fail", response_class=HTMLResponse)
async def payment_fail(code: str = "", message: str = ""):
    return _result_html(False, message or "결제가 취소됐습니다.")


# ─────────────────────────────────────────────────────────────────
# 8. 관리자: 크레딧 현황
# ─────────────────────────────────────────────────────────────────
@router.get("/admin/credits")
async def admin_credits(secret: str = Query(...)):
    if secret != ADMIN_SECRET:
        raise HTTPException(403, "관리자 권한 없음")
    rdb  = _get_redis()
    keys = rdb.keys("tantan:credit:*")
    data = []
    for k in sorted(keys):
        phone   = k.replace("tantan:credit:", "")
        credits = int(rdb.get(k) or 0)
        data.append({"phone": phone, "credits": credits})
    return {"total_users": len(data), "users": data}


# ─────────────────────────────────────────────────────────────────
# 9. 관리자: 수동 크레딧 지급
# ─────────────────────────────────────────────────────────────────
class GrantReq(BaseModel):
    phone:   str
    credits: int = Field(..., ge=1, le=100)
    secret:  str

@router.post("/admin/grant")
async def admin_grant(req: GrantReq):
    if req.secret != ADMIN_SECRET:
        raise HTTPException(403, "관리자 권한 없음")
    rdb         = _get_redis()
    new_credits = rdb.incrby(_redis_key_credit(req.phone), req.credits)
    logger.info(f"[관리자] {req.phone} +{req.credits}크레딧 수동 지급 → 잔여 {new_credits}")
    return {"success": True, "phone": req.phone, "total_credits": new_credits}


# ─────────────────────────────────────────────────────────────────
# 공통: 결제 결과 HTML (팝업 → 부모창 postMessage)
# ─────────────────────────────────────────────────────────────────
def _result_html(success: bool, message: str, credits: int = 0) -> HTMLResponse:
    msg_type = "TANTAN_SUCCESS" if success else "TANTAN_FAIL"
    color    = "#2ecc71" if success else "#e74c3c"
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{font-family:'Noto Sans KR',sans-serif;display:flex;align-items:center;
        justify-content:center;height:100vh;margin:0;background:#f8f9fa}}
  .box{{text-align:center;padding:2rem}}
  .icon{{font-size:3rem}}
  p{{color:{color};font-weight:700;font-size:1.1rem}}
</style></head><body>
<div class="box">
  <div class="icon">{'✅' if success else '❌'}</div>
  <p>{message}</p>
  <small>자동으로 닫힙니다...</small>
</div>
<script>
  const payload = {{type:'{msg_type}',message:'{message}',credits:{credits}}};
  if(window.opener){{
    window.opener.postMessage(payload,'*');
    setTimeout(()=>window.close(),1500);
  }} else {{
    setTimeout(()=>window.location.href='https://tantanfab.com/studio/',2000);
  }}
</script>
</body></html>""")
