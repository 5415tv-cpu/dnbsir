package com.tantan.call.pro

/**
 * CallFilter — 동네비서 수신/발신 판별 전용 클래스
 * ================================================
 * 이 클래스는 동네비서의 핵심 로직입니다.
 * "수신 전화일 때만 SMS를 보낸다"는 원칙을 단일 진실 공급원으로 관리합니다.
 *
 * 절대 수정하지 마십시오. 변경이 필요한 경우 이 파일만 수정하십시오.
 */
object CallFilter {

    /** 발신 전화로 판단하는 call_type 문자열 목록 */
    private val OUTGOING_TYPES = setOf("발신", "OUTGOING", "outgoing", "발신전화")

    /** 수신 전화로 확정하는 call_type 문자열 목록 */
    private val INCOMING_TYPES = setOf("수신", "부재중", "통화종료")

    // Android TelephonyManager 상태 상수
    const val STATE_RINGING = "RINGING"  // 수신 전화가 울리는 중 (발신전화에는 절대 발생 안 함)
    const val STATE_OFFHOOK = "OFFHOOK"  // 통화 중
    const val STATE_IDLE    = "IDLE"     // 통화 종료

    /**
     * call_type이 발신 전화이면 true.
     * 발신 전화는 어떤 경우에도 SMS를 보내지 않는다.
     */
    fun isOutgoing(callType: String): Boolean = callType.trim() in OUTGOING_TYPES

    /**
     * call_type이 명시적으로 수신 전화이면 true.
     */
    fun isIncoming(callType: String): Boolean = callType.trim() in INCOMING_TYPES

    /**
     * Android call_state 시퀀스로 수신/발신을 판별합니다.
     *
     * 핵심 원칙:
     *   - RINGING 상태는 수신 전화에만 발생합니다 (Android OS 보장).
     *   - hasRinging=false 상태로 IDLE에 도달하면 발신 전화입니다.
     *
     * @return Pair(보낼지 여부, 이유 설명)
     */
    fun shouldSendSms(
        prevState: String?,
        currentState: String,
        hasRinging: Boolean
    ): Pair<Boolean, String> {
        if (currentState != STATE_IDLE) {
            return Pair(false, "대기 중 ($currentState)")
        }

        // 수신 후 부재중: RINGING → IDLE
        val isMissed = (prevState == STATE_RINGING)

        // 수신 후 통화완료: RINGING → OFFHOOK → IDLE
        val isCompleted = (prevState == STATE_OFFHOOK && hasRinging)

        return when {
            isMissed    -> Pair(true,  "부재중 수신전화")
            isCompleted -> Pair(true,  "통화완료 수신전화")
            else        -> Pair(false, "발신전화 종료 (RINGING 미감지)")
        }
    }
}
