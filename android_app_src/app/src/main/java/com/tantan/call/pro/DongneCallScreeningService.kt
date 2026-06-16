package com.tantan.call.pro

import android.util.Log

class DongneCallScreeningService : android.telecom.CallScreeningService() {
    override fun onScreenCall(callDetails: android.telecom.Call.Details) {
        try {
            val phoneNumber = callDetails.handle?.schemeSpecificPart ?: ""
            Log.d("DongneBiseo", "수신 통화 감지(Screening): $phoneNumber")
            
            // 수신 콜백 설정 확인
            val prefs = getSharedPreferences("DongneBiseoPrefs", MODE_PRIVATE)
            val prefIncoming = prefs.getBoolean("pref_incoming", true)
            
            val callDirection = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                callDetails.callDirection
            } else {
                android.telecom.Call.Details.DIRECTION_INCOMING
            }
            
            if (prefIncoming && phoneNumber.isNotEmpty() && callDirection == android.telecom.Call.Details.DIRECTION_INCOMING) {
                // Screening은 수신 시점(벨 울릴 때) 바로 발생
                WebhookManager.processCall(this, phoneNumber, "수신")
            }
            
            passCall(callDetails)
        } catch (t: Throwable) {
            WebhookManager.writeLogToFile(this, "CallScreening 에러 발생: ${t.message}")
            try { passCall(callDetails) } catch (e: Exception) {}
        }
    }

    private fun passCall(callDetails: android.telecom.Call.Details) {
        try {
            val response = android.telecom.CallScreeningService.CallResponse.Builder()
                .setDisallowCall(false)
                .setRejectCall(false)
                .setSilenceCall(false)
                .setSkipCallLog(false)
                .setSkipNotification(false)
                .build()
            respondToCall(callDetails, response)
        } catch (e: Exception) {
            Log.e("DongneBiseo", "passCall 에러: ${e.message}")
        }
    }
}
