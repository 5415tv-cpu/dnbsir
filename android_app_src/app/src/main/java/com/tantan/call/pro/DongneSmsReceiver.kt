package com.tantan.call.pro

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class DongneSmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Log.d("DongneBiseo", "SMS 수신됨: ${intent.action}")
    }
}
