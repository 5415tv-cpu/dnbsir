package com.tantan.call.pro

import android.content.Context
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.*

object WebhookManager {
    private val scope = CoroutineScope(Dispatchers.IO)
    private const val webhookUrl = "https://dongnebiseo.com/webhook"  // HTTPS 직접 (301 리다이렉트 회피)
    private const val apiBaseUrl = "https://dongnebiseo.com/api/comm"
    
    // 중복 및 스팸 방지용 저장소 (메모리상 보관)
    private val processedNumbers = mutableMapOf<String, Long>()
    private const val REPOST_INTERVAL = 30_000L // 30초 쿨다운 (동일 번호 중복 차단)

    // 발신 통화 종료 감지용 (마지막 발신 번호 추적)
    private var lastOutgoingNumber: String = ""
    private var lastOutgoingTime: Long = 0L

    fun processCall(context: Context, phoneNumber: String, callTypeStr: String) {
        // "unknown" 번호는 CallScreeningService 결과를 기다림 (중복 방지)
        if (phoneNumber.isEmpty() || phoneNumber == "unknown") {
            writeLogToFile(context, "번호 미확인 통화 감지($callTypeStr) — CallScreeningService 결과 대기 중")
            return
        }
        val currentTime = System.currentTimeMillis()

        writeLogToFile(context, "--- 콜백 프로세스 시작 ($callTypeStr): $phoneNumber ---")

        // 1. 발송 횟수 제한 (동일 번호 30초 이내 재발송 금지)
        val lastTime = processedNumbers[phoneNumber] ?: 0L
        if (currentTime - lastTime < REPOST_INTERVAL) {
            val remaining = (REPOST_INTERVAL - (currentTime - lastTime)) / 1000
            writeLogToFile(context, "차단: 쿨다운 중 ($phoneNumber) — ${remaining}초 후 재허용")
            CallbackHistoryDBHelper(context).insertHistory(phoneNumber, callTypeStr, "쿨다운 차단(${remaining}초)")
            return
        }

        // 2. 비즈니스 전용 모드 체크
        val prefs = context.getSharedPreferences("DongneBiseoPrefs", Context.MODE_PRIVATE)
        val businessOnly = prefs.getBoolean("pref_business_only", false)
        
        if (businessOnly) {
            val isBusiness = ContactManager.isBusinessContact(context, phoneNumber)
            if (!isBusiness) {
                writeLogToFile(context, "차단: 비즈니스 번호 아님 (필터 작동 중)")
                CallbackHistoryDBHelper(context).insertHistory(phoneNumber, callTypeStr, "개인번호 차단")
                return
            } else {
                writeLogToFile(context, "통과: 비즈니스 번호 확인됨")
            }
        } else {
            writeLogToFile(context, "통과: 비즈니스 필터 꺼짐 (모든 번호 허용)")
        }

        processedNumbers[phoneNumber] = currentTime
        sendWebhookToVultr(context, phoneNumber, callTypeStr)
    }

    fun processCallState(context: Context, phoneNumber: String, callStateStr: String) {
        if (phoneNumber.isEmpty() || phoneNumber == "unknown") return
        writeLogToFile(context, "--- 콜백 상태 변경 감지 ($callStateStr): $phoneNumber ---")
        // CallFilter를 통해 발신전화 상태(OFFHOOK 직후 IDLE)는
        // 서버의 State Machine이 RINGING 미감지로 판단하여 차단합니다.
        sendWebhookToVultrWithState(context, phoneNumber, callStateStr)
    }

    /**
     * 공통 POST 헬퍼 - 리다이렉트 차단 + HTTPS 직접 POST
     * Android HttpURLConnection은 301 리다이렉트를 받으면 GET으로 자동 변환하므로
     * 리다이렉트를 반드시 비활성화하고 HTTPS를 직접 사용해야 함.
     */
    private fun sendPost(url: String, json: org.json.JSONObject): Int {
        val conn = java.net.URL(url).openConnection() as javax.net.ssl.HttpsURLConnection
        conn.requestMethod = "POST"
        conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
        conn.doOutput = true
        conn.instanceFollowRedirects = false  // 핵심: 301 리다이렉트 자동으로 따르지 않음
        conn.connectTimeout = 10_000
        conn.readTimeout = 10_000
        val writer = java.io.OutputStreamWriter(conn.outputStream, "UTF-8")
        writer.write(json.toString())
        writer.flush()
        writer.close()
        return conn.responseCode
    }

    private fun sendWebhookToVultrWithState(context: Context, phoneNumber: String, callStateStr: String) {
        scope.launch {
            try {
                val jsonParam = org.json.JSONObject()
                jsonParam.put("customer_number", phoneNumber)
                jsonParam.put("my_number", "010-0000-0000")
                jsonParam.put("call_state", callStateStr)  // RINGING, OFFHOOK, IDLE
                jsonParam.put("timestamp", System.currentTimeMillis().toString())
                jsonParam.put("auth_token", "DONGNE_BISEO_APP_SECRET_2026_!@")

                val responseCode = sendPost(webhookUrl, jsonParam)
                writeLogToFile(context, "웹훅 전송 성공($phoneNumber, $callStateStr): 코드 $responseCode")
            } catch (e: Exception) {
                writeLogToFile(context, "웹훅 전송 실패($phoneNumber, $callStateStr): ${e.message}")
            }
        }
    }

    /**
     * 발신 통화 종료 시 호출 — InCallService.onCallRemoved() 에서 사용
     * 통화가 완전히 끊긴 후 서버로 웹훅을 보내 콜백 문자 발송 트리거
     */
    fun processOutgoingCallEnded(context: Context, phoneNumber: String) {
        if (phoneNumber.isEmpty()) return
        val prefs = context.getSharedPreferences("DongneBiseoPrefs", Context.MODE_PRIVATE)
        // 기본값 false — 발신전화는 명시적으로 켜야만 웹훅 발송 (콜백은 수신전화 전용)
        if (!prefs.getBoolean("pref_outgoing", false)) {
            writeLogToFile(context, "발신전화 무시 (기본 OFF): $phoneNumber")
            return
        }
        writeLogToFile(context, "발신 통화 종료 감지 → 웹훅 발송: $phoneNumber")
        processCall(context, phoneNumber, "발신")
    }

    private fun sendWebhookToVultr(context: Context, phoneNumber: String, callTypeStr: String) {
        scope.launch {
            try {
                val jsonParam = org.json.JSONObject()
                jsonParam.put("customer_number", phoneNumber)
                jsonParam.put("my_number", "010-0000-0000")
                jsonParam.put("call_type", callTypeStr)  // 발신/수신 구분
                jsonParam.put("footer", "\n\n[수신거부] 동네비서 앱 설정에서 차단 가능")
                jsonParam.put("timestamp", System.currentTimeMillis().toString())
                jsonParam.put("auth_token", "DONGNE_BISEO_APP_SECRET_2026_!@")

                val responseCode = sendPost(webhookUrl, jsonParam)
                writeLogToFile(context, "웹훅 전송 성공($phoneNumber): 코드 $responseCode")
                CallbackHistoryDBHelper(context).insertHistory(phoneNumber, callTypeStr, "웹훅 발송 완료")
                Log.d("DongneBiseo", "웹훅 전송 성공: $phoneNumber")
            } catch (e: Exception) {
                writeLogToFile(context, "웹훅 전송 실패($phoneNumber): ${e.message}")
                CallbackHistoryDBHelper(context).insertHistory(phoneNumber, callTypeStr, "웹훅 발송 실패")
            }
        }
    }

    private fun isNightTime(): Boolean {
        val calendar = Calendar.getInstance()
        val hour = calendar.get(Calendar.HOUR_OF_DAY)
        return hour >= 21 || hour < 8
    }

    fun writeLogToFile(context: Context, message: String) {
        try {
            val timeStamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.KOREA).format(Date())
            val logEntry = "[WebhookManager] [$timeStamp] $message\n"
            val logFile = File(context.getExternalFilesDir(null), "logs.txt")
            FileOutputStream(logFile, true).use { it.write(logEntry.toByteArray()) }
        } catch (e: Exception) { }
    }
}
