package com.tantan.call.pro

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager
import android.util.Log

class DongnePhoneStateReceiver : BroadcastReceiver() {
    
    companion object {
        var lastState: String = TelephonyManager.EXTRA_STATE_IDLE
        var activeNumber: String = ""
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == TelephonyManager.ACTION_PHONE_STATE_CHANGED) {
            val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE) ?: return
            val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
            
            Log.d("DongneBiseo", "PHONE_STATE 감지: 상태=$state, 번호=$number, 이전번호=$activeNumber")
            
            if (!number.isNullOrEmpty()) {
                activeNumber = number
            }

            if (activeNumber.isNotEmpty()) {
                val prefs = context.getSharedPreferences("DongneBiseoPrefs", Context.MODE_PRIVATE)
                val prefIncoming = prefs.getBoolean("pref_incoming", true)
                
                if (prefIncoming) {
                    WebhookManager.processCallState(context, activeNumber, state)
                }
            }
            
            if (state == TelephonyManager.EXTRA_STATE_IDLE) {
                activeNumber = "" // 통화 종료 시 활성 번호 초기화
            }
            lastState = state
        }
    }
}
