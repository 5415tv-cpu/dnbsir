package com.tantan.call.pro

import android.telecom.Call
import android.telecom.InCallService
import android.util.Log

/**
 * 최신 안드로이드 규격에 맞춘 인콜 서비스.
 * 통화 종료(STATE_DISCONNECTED) 시 서버 웹훅을 전송합니다.
 */
class DongneInCallService : InCallService() {

    private val callCallback = object : Call.Callback() {
        override fun onStateChanged(call: Call, state: Int) {
            super.onStateChanged(call, state)
            if (state == Call.STATE_DISCONNECTED) {
                val number = call.details.handle?.schemeSpecificPart ?: ""
                val direction = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                    call.details.callDirection
                } else {
                    Call.Details.DIRECTION_UNKNOWN
                }
                Log.d("DongneBiseo", "통화 종료 감지 — 번호: $number, 방향: $direction")

                if (number.isNotEmpty()) {
                    val prefs = applicationContext.getSharedPreferences("DongneBiseoPrefs", MODE_PRIVATE)
                    when (direction) {
                        Call.Details.DIRECTION_OUTGOING -> {
                            // 발신 통화 종료 → 서버 콜백 문자 트리거
                            if (prefs.getBoolean("pref_outgoing", true)) {
                                Log.d("DongneBiseo", "발신 통화 종료 → 웹훅 발송: $number")
                                WebhookManager.processOutgoingCallEnded(applicationContext, number)
                            }
                        }
                        Call.Details.DIRECTION_INCOMING -> {
                            // 수신 통화는 벨 울릴 때 이미 처리됨 (중복 방지)
                            Log.d("DongneBiseo", "수신 통화 종료 (벨 단계에서 이미 처리됨): $number")
                        }
                        else -> {
                            // 방향 미확인 → 발신으로 간주 처리
                            Log.d("DongneBiseo", "통화 방향 미확인 → 발신으로 처리: $number")
                            WebhookManager.processOutgoingCallEnded(applicationContext, number)
                        }
                    }
                }
            }
        }
    }

    override fun onBind(intent: android.content.Intent?): android.os.IBinder? {
        Log.d("DongneBiseo", "InCallService 바인딩 완료")
        return super.onBind(intent)
    }

    override fun onUnbind(intent: android.content.Intent?): Boolean {
        Log.d("DongneBiseo", "InCallService 바인딩 해제")
        return super.onUnbind(intent)
    }

    override fun onCallAdded(call: Call) {
        super.onCallAdded(call)
        try {
            Log.d("DongneBiseo", "통화 추가 감지: ${call.details.handle?.schemeSpecificPart}")
            call.registerCallback(callCallback)
        } catch (e: Exception) {
            Log.e("DongneBiseo", "InCallService 오류: ${e.message}")
        }
    }

    override fun onCallRemoved(call: Call) {
        super.onCallRemoved(call)
        try {
            call.unregisterCallback(callCallback)
        } catch (e: Exception) {
            Log.e("DongneBiseo", "Callback 해제 오류: ${e.message}")
        }
        Log.d("DongneBiseo", "통화 종료 처리 완료")
    }
}
