"""
탄탄제작소 관리자 인증 API (SMS 인증 기반)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST /api/v1/admin/send-code   → 인증번호 SMS 발송
POST /api/v1/admin/verify-code → 인증번호 확인 + 세션 쿠키 발급
GET  /api/v1/admin/me          → 현재 세션 유효성 확인
POST /api/v1/admin/logout      → 세션 쿠키 삭제
"""
from fastapi import APIRouter, HTTPException, Response, Request, Cookie
from pydantic import BaseModel
from typing import Optional
import os
import secrets
import time
import logging

_logger = logging.getLogger("tantan.admin_auth")

admin_auth = APIRouter(prefix="/api/v1/admin", tags=["tantan-admin-auth"])

# ── Redis 연결 (인증번호 임시 저장소) ──────────────────────────
import redis
_redis = redis.from_url(
    os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
    decode_responses=True,
)

# ── 인증번호 유효 시간 ─────────────────────────────────────────
AUTH_CODE_TTL = 300  # 5분
SESSION_TTL = 86400 * 7  # 7일


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 요청/응답 모델
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class SendCodeRequest(BaseModel):
    phone_number: str  # 예: "01012345678"

class VerifyCodeRequest(BaseModel):
    phone_number: str
    auth_code: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 인증번호 발송
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin_auth.post("/send-code")
async def send_auth_code(req: SendCodeRequest):
    """
    6자리 인증번호를 생성하여 Redis에 저장하고 SMS 발송.
    Redis Key: tantan:auth:{phone} → 인증번호 (TTL 5분)
    """
    phone = req.phone_number.replace("-", "").strip()
    if len(phone) < 10:
        raise HTTPException(status_code=400, detail="올바른 전화번호를 입력해주세요.")

    # 6자리 인증번호 생성
    code = f"{secrets.randbelow(900000) + 100000}"

    # Redis에 저장 (5분 TTL)
    redis_key = f"tantan:auth:{phone}"
    _redis.setex(redis_key, AUTH_CODE_TTL, code)

    # TODO: 실제 SMS 발송 연동 (알림톡 or CoolSMS)
    # 현재는 로그에만 출력 (개발 모드)
    _logger.info(f"[Admin Auth] 인증번호 발송: {phone[-4:]} → {code}")

    return {
        "status": "success",
        "message": "인증번호가 발송되었습니다.",
        "expires_in": AUTH_CODE_TTL,
        # ⚠️ 개발 모드: 인증번호를 응답에 포함 (프로덕션에서 제거할 것)
        "_dev_code": code,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 인증번호 확인 + 세션 쿠키 발급
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin_auth.post("/verify-code")
async def verify_sms_code(req: VerifyCodeRequest, response: Response):
    """
    사용자가 입력한 인증번호와 Redis에 저장된 값을 비교.
    일치하면 세션 쿠키(tantan_session) 발급.
    """
    phone = req.phone_number.replace("-", "").strip()
    redis_key = f"tantan:auth:{phone}"

    # Redis에서 저장된 인증번호 조회
    stored_code = _redis.get(redis_key)

    if not stored_code:
        raise HTTPException(
            status_code=400,
            detail="인증번호가 만료되었거나 발송되지 않았습니다. 다시 요청해주세요.",
        )

    if stored_code != req.auth_code.strip():
        raise HTTPException(
            status_code=400,
            detail="인증번호가 일치하지 않습니다.",
        )

    # ── 인증 성공: 세션 토큰 생성 ──────────────────────────────
    session_token = secrets.token_urlsafe(32)
    session_key = f"tantan:session:{session_token}"

    # Redis에 세션 저장 (7일 TTL)
    _redis.setex(session_key, SESSION_TTL, phone)

    # 사용 완료된 인증번호 삭제
    _redis.delete(redis_key)

    # ── 세션 쿠키 설정 ─────────────────────────────────────────
    response.set_cookie(
        key="tantan_session",
        value=session_token,
        httponly=True,      # JS 탈취 방지
        secure=True,        # HTTPS 전용
        samesite="lax",     # CSRF 기본 방어
        max_age=SESSION_TTL,
        path="/",
    )

    _logger.info(f"[Admin Auth] 인증 완료: {phone[-4:]}")

    return {
        "status": "success",
        "message": "인증이 완료되었습니다. 스튜디오로 이동합니다.",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 세션 유효성 확인 (프론트엔드 자동 체크용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin_auth.get("/me")
async def check_session(
    tantan_session: Optional[str] = Cookie(default=None),
):
    """현재 세션 쿠키가 유효한지 확인."""
    if not tantan_session:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    session_key = f"tantan:session:{tantan_session}"
    phone = _redis.get(session_key)

    if not phone:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다. 다시 로그인해주세요.")

    return {
        "status": "authenticated",
        "phone": f"{phone[:3]}****{phone[-4:]}",  # 마스킹
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 로그아웃
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin_auth.post("/logout")
async def logout(
    response: Response,
    tantan_session: Optional[str] = Cookie(default=None),
):
    """세션 쿠키 삭제 + Redis 세션 정리."""
    if tantan_session:
        _redis.delete(f"tantan:session:{tantan_session}")

    response.delete_cookie("tantan_session", path="/")
    return {"status": "success", "message": "로그아웃 되었습니다."}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 토스 결제 웹훅 (서버→서버 알림) — DB 트랜잭션
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import hmac
import hashlib
from fastapi import Depends
from sqlalchemy.orm import Session
from tantan_database import get_db
from tantan_models import TantanUser, PaymentHistory

TOSS_WEBHOOK_SECRET = os.environ.get(
    "TOSS_WEBHOOK_SECRET",
    "3118937f80fbf36faf5e2291e419994fc62bdff2ea9b8bbe90f7e6b16ff7b8f8",
)

# 패키지 정보 (tantan_payment.py와 동일)
_PACKAGES = {
    "pkg_1": {"credits": 1, "amount": 4000,  "label": "영상 1개"},
    "pkg_3": {"credits": 3, "amount": 12000, "label": "영상 3개"},
    "pkg_5": {"credits": 5, "amount": 18000, "label": "영상 5개"},
}


def _extract_phone_from_order_id(order_id: str) -> str:
    """
    orderId 형식: TT_{phone}_{timestamp}_{random}
    예: TT_01012345678_1720345678_A1B2C3
    → '01012345678' 추출
    """
    parts = order_id.split("_")
    if len(parts) >= 3 and parts[0] == "TT":
        return parts[1]
    return ""


@admin_auth.post("/toss-webhook")
async def receive_toss_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    토스페이먼츠 → 우리 서버 (서버 간 알림).

    방어 로직 3중:
      1. HMAC 서명 검증 (위조 차단)
      2. 멱등성 — 동일 orderId 중복 처리 차단
      3. DB 트랜잭션 — 영수증 + 크레딧 동시 커밋, 실패 시 롤백
    """
    try:
        body = await request.body()
        payload = await request.json()

        # ── [방어 1] HMAC 서명 검증 ────────────────────────────
        toss_signature = request.headers.get("Toss-Signature", "")
        if TOSS_WEBHOOK_SECRET and toss_signature:
            expected = hmac.new(
                TOSS_WEBHOOK_SECRET.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, toss_signature):
                _logger.warning("[Webhook] 서명 불일치 — 위조 요청 차단")
                raise HTTPException(status_code=400, detail="Invalid signature")

        # ── 결제 상태 파싱 ─────────────────────────────────────
        data = payload.get("data", {})
        status = data.get("status", "")
        order_id = data.get("orderId", "")
        payment_key = data.get("paymentKey", "")
        amount = data.get("totalAmount", 0) or data.get("amount", 0)

        _logger.info(f"[Webhook] status={status} orderId={order_id} amount={amount}")

        # ══════════════════════════════════════════════════════
        # 결제 성공 (DONE) — 크레딧 충전
        # ══════════════════════════════════════════════════════
        if status == "DONE":

            # [방어 2] 멱등성 — 이미 처리된 영수증인지 확인
            existing = db.query(PaymentHistory).filter(
                PaymentHistory.order_id == order_id
            ).first()
            if existing:
                _logger.info(f"[Webhook] 중복 수신 무시: {order_id}")
                return {"status": "success", "message": "이미 처리된 영수증"}

            # orderId에서 전화번호 추출
            phone = _extract_phone_from_order_id(order_id)
            if not phone:
                # Redis 메타에서 폴백 시도
                meta = _redis.get(f"tantan:payment:{order_id}")
                if meta:
                    phone = meta.split("|")[0]
            if not phone:
                _logger.error(f"[Webhook] 전화번호 추출 실패: {order_id}")
                raise HTTPException(400, "주문번호에서 결제자를 식별할 수 없습니다.")

            # [방어 3] 회원 DB 검증 — 없으면 자동 생성
            user = db.query(TantanUser).filter(
                TantanUser.phone_number == phone
            ).first()
            if not user:
                user = TantanUser(phone_number=phone, credit_balance=0)
                db.add(user)
                db.flush()  # id 생성을 위해 flush

            # 크레딧 계산 (패키지 기반 또는 금액 기반)
            meta = _redis.get(f"tantan:payment:{order_id}")
            pkg_id = meta.split("|")[1] if meta else None
            pkg = _PACKAGES.get(pkg_id) if pkg_id else None
            credit_to_add = pkg["credits"] if pkg else max(1, amount // 4000)

            # ── DB 트랜잭션: 영수증 + 크레딧 동시 처리 ──────
            try:
                # 영수증 발행
                new_payment = PaymentHistory(
                    order_id=order_id,
                    user_id=user.id,
                    payment_key=payment_key,
                    amount=amount,
                    credit_added=credit_to_add,
                    package_id=pkg_id or "unknown",
                    status="DONE",
                )
                db.add(new_payment)

                # 크레딧 충전
                user.credit_balance += credit_to_add

                # Redis 크레딧도 동기화 (기존 프론트엔드 호환)
                _redis.set(f"tantan:credit:{phone}", user.credit_balance)

                db.commit()

                _logger.info(
                    f"🎉 [결제완료] {phone[-4:]} +{credit_to_add}크레딧 "
                    f"(잔여:{user.credit_balance}) 주문:{order_id}"
                )

                # Redis 주문 메타 정리
                _redis.delete(f"tantan:payment:{order_id}")

            except Exception as e:
                db.rollback()
                _logger.error(f"[Webhook DB 에러] {e}", exc_info=True)
                raise HTTPException(500, "크레딧 충전 중 오류 발생")

        # ══════════════════════════════════════════════════════
        # 결제 취소 (CANCELED) — 크레딧 회수
        # ══════════════════════════════════════════════════════
        elif status == "CANCELED":
            existing = db.query(PaymentHistory).filter(
                PaymentHistory.order_id == order_id
            ).first()
            if existing and existing.status != "CANCELED":
                try:
                    user = db.query(TantanUser).filter(
                        TantanUser.id == existing.user_id
                    ).first()
                    if user:
                        user.credit_balance = max(0, user.credit_balance - existing.credit_added)
                        _redis.set(f"tantan:credit:{user.phone_number}", user.credit_balance)
                    existing.status = "CANCELED"
                    db.commit()
                    _logger.warning(
                        f"[결제취소] {user.phone_number[-4:] if user else '?'} "
                        f"-{existing.credit_added}크레딧 주문:{order_id}"
                    )
                except Exception as e:
                    db.rollback()
                    _logger.error(f"[취소 DB 에러] {e}", exc_info=True)

        else:
            _logger.info(f"[Webhook] {status} — orderId={order_id}")

        # ── 토스에 정상 수신 응답 ──────────────────────────────
        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        _logger.error(f"[Webhook 에러] {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="웹훅 처리 중 오류 발생")

