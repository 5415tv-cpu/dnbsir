package com.tantan.call.pro

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log

class DongneSmsService : Service() {

    override fun onCreate() {
        super.onCreate()
        
        val manager = getSystemService(android.app.NotificationManager::class.java)
        // 1. 알림 채널 설정 (Android 8.0 이상 필수)
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val channel = android.app.NotificationChannel("secretary_service", "동네비서 서비스", android.app.NotificationManager.IMPORTANCE_LOW)
            manager.createNotificationChannel(channel)
        }

        // 2. 서비스 시작 시 알림 띄우기
        val notification = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            android.app.Notification.Builder(this, "secretary_service")
                .setContentTitle("동네비서가 작동 중입니다")
                .setContentText("통화 종료 후 자동으로 문자를 발송합니다.")
                .setSmallIcon(R.drawable.logo_main) // ic_secretary가 없으므로 로고 사용
                .build()
        } else {
            android.app.Notification.Builder(this)
                .setContentTitle("동네비서가 작동 중입니다")
                .setContentText("통화 종료 후 자동으로 문자를 발송합니다.")
                .setSmallIcon(R.drawable.logo_main)
                .build()
        }

        // 3. 이 코드가 핵심입니다. (서비스를 포그라운드로 승격)
        try {
            if (android.os.Build.VERSION.SDK_INT >= 34) {
                startForeground(1, notification, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
            } else {
                startForeground(1, notification)
            }
        } catch (e: Exception) {
            android.util.Log.e("DongneBiseo", "포그라운드 서비스 승격 실패 (알림 권한 거부 또는 정책 위반): ${e.message}")
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d("DongneBiseo", "SmsService 시작됨 (포그라운드 유지)")
        return START_NOT_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? {
        Log.d("DongneBiseo", "SmsService 시스템 바인딩 완료 (onBind) - 정확한 IBinder 처리")
        // RespondViaSmsService 등의 경우, 별도의 IBinder를 제공하지 않아도 시스템에서 null을 허용함.
        // 향후 확장이 필요하면 여기에 custom IBinder 반환.
        return null
    }

    override fun onUnbind(intent: Intent?): Boolean {
        Log.d("DongneBiseo", "SmsService 시스템 바인딩 해제 (onUnbind)")
        return super.onUnbind(intent)
    }
}
