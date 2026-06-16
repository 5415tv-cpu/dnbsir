package com.tantan.call.pro

import android.net.Uri
import android.telecom.CallRedirectionService
import android.telecom.PhoneAccountHandle
import android.util.Log

class DongneCallRedirectionService : CallRedirectionService() {

    override fun onPlaceCall(
        handle: Uri,
        initialPhoneAccount: PhoneAccountHandle,
        allowInteractiveResponse: Boolean
    ) {
        val phoneNumber = handle.schemeSpecificPart
        Log.d("DongneBiseo", "발신 통화 감지(Redirection): $phoneNumber")
        WebhookManager.writeLogToFile(this, "발신 통화 감지됨: $phoneNumber")

        // 발신 통화를 그대로 진행시킴 (시스템이 정상 처리하도록 위임)
        placeCallUnmodified()

        val prefs = getSharedPreferences("DongneBiseoPrefs", MODE_PRIVATE)
        val prefBusinessOnly = prefs.getBoolean("pref_business_only", false)

        if (prefBusinessOnly) {
            val isBusiness = ContactManager.isBusinessContact(this, phoneNumber)
            if (!isBusiness) {
                Log.d("DongneBiseo", "비즈니스 연락처가 아니므로 콜백 건너뜀 (개인 용무 보호): $phoneNumber")
                return
            }
        }

        val prefOutgoing = prefs.getBoolean("pref_outgoing", true)
        if (!prefOutgoing) {
            Log.d("DongneBiseo", "발신 콜백 옵션이 꺼져 있어 건너뜀")
            return
        }

        WebhookManager.processCall(this, phoneNumber, "발신(자동)")
    }
}
