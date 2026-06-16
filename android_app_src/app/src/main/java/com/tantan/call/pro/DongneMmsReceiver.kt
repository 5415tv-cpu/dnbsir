package com.tantan.call.pro

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class DongneMmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        Log.d("DongneBiseo", "MMS 수신됨: ${intent.action}")
    }
}
