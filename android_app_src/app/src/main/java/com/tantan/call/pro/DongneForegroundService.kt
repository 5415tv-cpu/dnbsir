package com.tantan.call.pro

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat

class DongneForegroundService : Service() {

    private val CHANNEL_ID = "DongneBiseoForegroundChannel"
    private var telephonyManager: android.telephony.TelephonyManager? = null
    private var phoneStateListener: android.telephony.PhoneStateListener? = null
    // Android 12+ TelephonyCallback
    private var telephonyCallback: Any? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        registerPhoneStateListener()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("동네비서")
            .setContentText("동네비서가 실행 중입니다")
            .setSmallIcon(android.R.drawable.ic_menu_call)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= 34) {
            try {
                startForeground(1004, notification, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
                android.util.Log.i("DongneBiseo", "포그라운드 서비스 시작 성공 (Android 14+)")
            } catch (e: SecurityException) {
                android.util.Log.e("DongneBiseo", "포그라운드 권한 거부 (Permission Denial): ${e.message}")
            } catch (e: Exception) {
                android.util.Log.e("DongneBiseo", "포그라운드 진입 실패 (Android 14+): ${e.message}")
            }
        } else {
            try {
                startForeground(1004, notification)
                android.util.Log.i("DongneBiseo", "포그라운드 서비스 시작 성공 (Android 13 이하)")
            } catch (e: Exception) {
                android.util.Log.e("DongneBiseo", "포그라운드 진입 실패: ${e.message}")
            }
        }
        
        // 메모리 부족으로 죽어도 OS가 다시 깨우도록 START_STICKY 반환 (불사조 모드)
        ServiceStateManager.setServiceActive(true)
        return START_STICKY
    }


    override fun onBind(intent: Intent?): IBinder? {
        return null // 바인딩 되는 서비스가 아님
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                CHANNEL_ID,
                "동네비서 실시간 에이전트",
                NotificationManager.IMPORTANCE_HIGH 
            )
            val manager: NotificationManager? = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(serviceChannel)
        }
    }

    private fun registerPhoneStateListener() {
        try {
            telephonyManager = getSystemService(Context.TELEPHONY_SERVICE) as android.telephony.TelephonyManager

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                // Android 12+ : TelephonyCallback (PhoneStateListener deprecated)
                val callback = object : android.telephony.TelephonyCallback(),
                    android.telephony.TelephonyCallback.CallStateListener {
                    private var lastState = android.telephony.TelephonyManager.CALL_STATE_IDLE
                    override fun onCallStateChanged(state: Int) {
                        android.util.Log.d("DongneBiseo", "TelephonyCallback: state=$state")
                        val number = DongnePhoneStateReceiver.activeNumber
                        val stateStr = when (state) {
                            android.telephony.TelephonyManager.CALL_STATE_RINGING -> "RINGING"
                            android.telephony.TelephonyManager.CALL_STATE_OFFHOOK -> "OFFHOOK"
                            else -> "IDLE"
                        }
                        if (number.isNotEmpty() && state != lastState) {
                            val prefs = getSharedPreferences("DongneBiseoPrefs", Context.MODE_PRIVATE)
                            if (prefs.getBoolean("pref_incoming", true)) {
                                WebhookManager.processCallState(this@DongneForegroundService, number, stateStr)
                            }
                        }
                        lastState = state
                    }
                }
                telephonyCallback = callback
                telephonyManager?.registerTelephonyCallback(
                    mainExecutor,
                    callback
                )
                android.util.Log.d("DongneBiseo", "TelephonyCallback 등록 성공 (Android 12+)")
            } else {
                // Android 11 이하 : 레거시 PhoneStateListener
                phoneStateListener = object : android.telephony.PhoneStateListener() {
                    var lastState = android.telephony.TelephonyManager.CALL_STATE_IDLE
                    override fun onCallStateChanged(state: Int, phoneNumber: String?) {
                        super.onCallStateChanged(state, phoneNumber)
                        android.util.Log.d("DongneBiseo", "PhoneStateListener: state=$state, number=$phoneNumber")
                        
                        var number = phoneNumber ?: ""
                        if (number.isEmpty()) {
                            number = DongnePhoneStateReceiver.activeNumber
                        }
                        
                        val stateStr = when (state) {
                            android.telephony.TelephonyManager.CALL_STATE_RINGING -> "RINGING"
                            android.telephony.TelephonyManager.CALL_STATE_OFFHOOK -> "OFFHOOK"
                            else -> "IDLE"
                        }
                        
                        if (number.isNotEmpty() && state != lastState) {
                            val prefs = getSharedPreferences("DongneBiseoPrefs", Context.MODE_PRIVATE)
                            if (prefs.getBoolean("pref_incoming", true)) {
                                WebhookManager.processCallState(this@DongneForegroundService, number, stateStr)
                            }
                        }
                        lastState = state
                    }
                }
                @Suppress("DEPRECATION")
                telephonyManager?.listen(phoneStateListener, android.telephony.PhoneStateListener.LISTEN_CALL_STATE)
                android.util.Log.d("DongneBiseo", "PhoneStateListener 등록 성공 (Android 11 이하)")
            }
        } catch (e: Exception) {
            android.util.Log.e("DongneBiseo", "전화 상태 리스너 등록 실패: ${e.message}")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        // 리스너 해제
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                (telephonyCallback as? android.telephony.TelephonyCallback)?.let {
                    telephonyManager?.unregisterTelephonyCallback(it)
                }
            } else {
                @Suppress("DEPRECATION")
                telephonyManager?.listen(phoneStateListener, android.telephony.PhoneStateListener.LISTEN_NONE)
            }
        } catch (e: Exception) { }
        ServiceStateManager.setServiceActive(false)
    }
}
