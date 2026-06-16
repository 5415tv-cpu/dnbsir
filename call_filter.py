"""
call_filter.py — 동네비서 수신/발신 판별 모듈
=============================================
이 모듈은 동네비서의 핵심 로직입니다.
"수신 전화일 때만 SMS를 보낸다"는 원칙을 단일 진실 공급원(Single Source of Truth)으로 관리합니다.

절대 수정하지 마십시오. 변경이 필요한 경우 이 파일만 수정하십시오.
"""

# ── 발신 전화로 판단하는 call_type 값 (앱이 어떻게 보내든 대응) ──────────────
OUTGOING_CALL_TYPES = frozenset([
    "발신", "OUTGOING", "outgoing", "발신전화",
])

# ── 수신 전화로 확정하는 call_type 값 (이 값일 때만 SMS 허용) ────────────────
INCOMING_CALL_TYPES = frozenset([
    "수신", "부재중", "통화종료",
])

# ── Android TelephonyManager 상태 상수 ──────────────────────────────────────
STATE_RINGING = "RINGING"   # 수신 전화가 울리는 중 (발신전화에는 절대 발생 안 함)
STATE_OFFHOOK = "OFFHOOK"   # 통화 중 (수신/발신 모두 가능)
STATE_IDLE    = "IDLE"      # 통화 종료


def is_outgoing(call_type: str) -> bool:
    """call_type이 발신 전화이면 True."""
    return call_type.strip() in OUTGOING_CALL_TYPES


def is_incoming_by_type(call_type: str) -> bool:
    """call_type이 명시적으로 수신 전화이면 True."""
    return call_type.strip() in INCOMING_CALL_TYPES


def should_send_sms_state_machine(
    prev_state: str | None,
    current_state: str,
    has_ringing: bool,
) -> tuple[bool, str]:
    """
    Android call_state 시퀀스로 수신/발신을 판별합니다.

    핵심 원칙:
      - RINGING 상태는 수신 전화에만 발생합니다 (Android OS 보장).
      - has_ringing=True 없이 IDLE에 도달하면 발신 전화입니다.

    Returns:
        (should_send: bool, reason: str)
    """
    if current_state != STATE_IDLE:
        return False, f"대기 중 ({current_state})"

    # 수신 후 부재중: RINGING → IDLE
    is_missed = (prev_state == STATE_RINGING)

    # 수신 후 통화완료: RINGING → OFFHOOK → IDLE
    is_completed = (prev_state == STATE_OFFHOOK and has_ringing)

    if is_missed:
        return True, "부재중 수신전화"
    if is_completed:
        return True, "통화완료 수신전화"

    # RINGING 없이 IDLE → 발신전화
    return False, "발신전화 종료 (RINGING 미감지)"


def should_send_sms_legacy(call_type: str, call_state: str) -> tuple[bool, str]:
    """
    GET(구버전 앱) 레거시 경로 판별.
    call_type이 명시적으로 수신 전화여야만 허용합니다.
    call_state == IDLE 단독은 발신전화와 구별이 불가능하므로 허용하지 않습니다.

    Returns:
        (should_send: bool, reason: str)
    """
    if is_outgoing(call_type):
        return False, "발신전화"

    if is_incoming_by_type(call_type):
        return True, f"수신전화 ({call_type})"

    return False, f"call_type 미확인 ({call_type!r}) — 발신으로 간주"
