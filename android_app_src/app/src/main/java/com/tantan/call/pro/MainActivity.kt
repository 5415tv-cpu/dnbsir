package com.tantan.call.pro

import android.Manifest
import android.app.DownloadManager
import android.app.role.RoleManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.PowerManager
import android.provider.Settings
import android.provider.CallLog
import android.widget.Button
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import android.widget.CheckBox
import android.widget.ImageButton
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import com.tantan.call.pro.R
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import android.app.AlertDialog
import android.content.DialogInterface
import android.content.ClipData
import android.content.ClipboardManager
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import android.view.LayoutInflater
import android.view.ViewGroup
import android.graphics.Color
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var tvStatusMessage: TextView
    private lateinit var etDialNumber: EditText
    private lateinit var layoutDialer: LinearLayout
    private lateinit var layoutSettings: LinearLayout
    private var isPopupActive = false

    private val requestRoleLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            Toast.makeText(this, "스팸 차단 및 발신번호 확인 기본 앱 등록 완료!", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "기본 앱 등록이 취소되었습니다. 발신번호 인식이 제한될 수 있습니다.", Toast.LENGTH_LONG).show()
        }
        updateStatusText()
        loadHistory()
    }

    override fun onResume() {
        super.onResume()
        loadHistory()
        if (::tvStatusMessage.isInitialized) {
            updateStatusText()
        }
        if (hasRequiredPermissions()) {
            startPersistentService()
        }
    }

    private fun loadHistory() {
        val rvHistoryMain = findViewById<RecyclerView>(R.id.rvHistoryMain)
        if (rvHistoryMain != null) {
            lifecycleScope.launch(kotlinx.coroutines.Dispatchers.IO) {
                try {
                    val url = java.net.URL("https://dongnebiseo.com/api/comm/history?limit=30")
                    val conn = url.openConnection() as java.net.HttpURLConnection
                    if (conn.responseCode == 200) {
                        val response = conn.inputStream.bufferedReader().readText()
                        val jsonObject = org.json.JSONObject(response)
                        val historyArray = jsonObject.getJSONArray("history")
                        val serverHistory = mutableListOf<CallbackHistory>()

                        for (i in 0 until historyArray.length()) {
                            val obj = historyArray.getJSONObject(i)
                            // Mapping server logs to app history model
                            val number = obj.optString("customer_phone", "알 수 없음")
                            val type = obj.optString("call_type", "발신")
                            val status = obj.optString("status", "완료")
                            val dateStr = obj.optString("received_at", "")
                            
                            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
                            val timestamp = try { sdf.parse(dateStr)?.time ?: 0L } catch(e: Exception) { 0L }

                            serverHistory.add(CallbackHistory(number, type, status, timestamp))
                        }

                        launch(kotlinx.coroutines.Dispatchers.Main) {
                            rvHistoryMain.layoutManager = LinearLayoutManager(this@MainActivity)
                            rvHistoryMain.adapter = HistoryAdapter(serverHistory)
                        }
                    }
                } catch (e: Exception) {
                    android.util.Log.e("DongneBiseo", "서버 내역 로드 실패: ${e.message}")
                }
            }
        }
    }

    inner class HistoryAdapter(private val items: List<CallbackHistory>) : RecyclerView.Adapter<HistoryAdapter.ViewHolder>() {
        inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val tvPhone: TextView = view.findViewById(R.id.tvPhoneNumber)
            val tvType: TextView = view.findViewById(R.id.tvCallType)
            val tvStatus: TextView = view.findViewById(R.id.tvStatus)
            val tvTime: TextView = view.findViewById(R.id.tvTimestamp)
            val btnCall: View = view.findViewById(R.id.btnHistoryCall)
            val btnSms: View = view.findViewById(R.id.btnHistorySms)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_callback_history, parent, false)
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val item = items[position]
            holder.tvPhone.text = item.phoneNumber
            holder.tvType.text = item.callType
            
            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
            holder.tvTime.text = sdf.format(Date(item.timestamp))
            
            holder.tvStatus.text = item.status
            if (item.status.contains("성공") || item.status.contains("완료")) {
                holder.tvStatus.setTextColor(Color.parseColor("#4CAF50"))
            } else if (item.status.contains("차단") || item.status.contains("방지")) {
                holder.tvStatus.setTextColor(Color.parseColor("#FF9800"))
            } else {
                holder.tvStatus.setTextColor(Color.parseColor("#F44336"))
            }

            // 히스토리에서 바로 전화 걸기
            holder.btnCall.setOnClickListener {
                if (item.phoneNumber.isNotEmpty()) {
                    val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:${item.phoneNumber}"))
                    if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                        startActivity(intent)
                        reportCallEventToServer(item.phoneNumber)
                    } else {
                        ActivityCompat.requestPermissions(this@MainActivity, arrayOf(Manifest.permission.CALL_PHONE), 1002)
                    }
                }
            }

            // 히스토리에서 바로 문자 보내기 (SMS 앱으로 바로 이동)
            holder.btnSms.setOnClickListener {
                if (item.phoneNumber.isNotEmpty()) {
                    val smsIntent = Intent(Intent.ACTION_SENDTO).apply {
                        data = Uri.parse("smsto:${item.phoneNumber}")
                        putExtra("sms_body", "[동네비서] 안녕하세요, 연락 드립니다.")
                    }
                    startActivity(smsIntent)
                }
            }
        }

        override fun getItemCount() = items.size
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
            setContentView(R.layout.activity_main)

            // View 초기화
            tvStatusMessage = findViewById(R.id.tvStatusMessage)
            etDialNumber = findViewById<EditText>(R.id.etDialNumber)
            layoutDialer = findViewById(R.id.layoutDialer)
            layoutSettings = findViewById(R.id.layoutSettings)

            val webViewDashboard = findViewById<android.webkit.WebView>(R.id.webViewDashboard)
            val layoutLocalFeatures = findViewById<LinearLayout>(R.id.layoutLocalFeatures)

            // 웹뷰 설정 및 로드
            webViewDashboard.settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                useWideViewPort = true
                loadWithOverviewMode = true
                databaseEnabled = true
                setSupportZoom(true)
                builtInZoomControls = true
                displayZoomControls = false
                
                // Customize User-Agent to bypass Google OAuth WebView blocks and deep-link loops
                var defaultUserAgent = userAgentString
                defaultUserAgent = defaultUserAgent.replace("Version/4.0 ", "")
                defaultUserAgent = defaultUserAgent.replace("; wv", "")
                userAgentString = "$defaultUserAgent DongneBiseoApp"
            }
            
            webViewDashboard.webViewClient = object : android.webkit.WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    view: android.webkit.WebView?,
                    request: android.webkit.WebResourceRequest?
                ): Boolean {
                    val url = request?.url?.toString() ?: return false
                    
                    if (url.startsWith("http://") || url.startsWith("https://")) {
                        return false // standard web links load in webview
                    }
                    
                    try {
                        val intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME)
                        if (intent != null) {
                            view?.context?.startActivity(intent)
                            return true
                        }
                    } catch (e: Exception) {
                        e.printStackTrace()
                        // Fallback URL (e.g. Kakao web page fallback if KakaoTalk app is not installed)
                        try {
                            val intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME)
                            val fallbackUrl = intent.getStringExtra("browser_fallback_url")
                            if (fallbackUrl != null) {
                                view?.loadUrl(fallbackUrl)
                                return true
                            }
                        } catch (ex: Exception) {
                            ex.printStackTrace()
                        }
                    }
                    return true
                }
            }
            webViewDashboard.webChromeClient = android.webkit.WebChromeClient()
            webViewDashboard.loadUrl("https://dongnebiseo.com/admin/dashboard")
            
            // [토글] 전화번호 입력 버튼 → 다이얼패드 표시/숨기기
            val btnToggleDialer = findViewById<Button>(R.id.btnToggleDialer)
            btnToggleDialer.setOnClickListener {
                if (layoutDialer.visibility == View.VISIBLE) {
                    layoutDialer.visibility = View.GONE
                    layoutSettings.visibility = View.GONE
                    btnToggleDialer.text = "📞 전화번호 입력"
                } else {
                    layoutDialer.visibility = View.VISIBLE
                    layoutSettings.visibility = View.GONE
                    btnToggleDialer.text = "▼ 닫기"
                }
            }

            // [토글] 설정 버튼
            val btnToggleSettings = findViewById<Button>(R.id.btnToggleSettings)
            btnToggleSettings.setOnClickListener {
                if (layoutSettings.visibility == View.VISIBLE) {
                    layoutSettings.visibility = View.GONE
                } else {
                    layoutSettings.visibility = View.VISIBLE
                    layoutDialer.visibility = View.GONE
                    btnToggleDialer.text = "📞 전화번호 입력"
                }
            }

            // 숫자 패드 버튼 연결 (0-9, *, #)
            val buttonIds = arrayOf(
                R.id.btn0, R.id.btn1, R.id.btn2, R.id.btn3, R.id.btn4,
                R.id.btn5, R.id.btn6, R.id.btn7, R.id.btn8, R.id.btn9,
                R.id.btnStar, R.id.btnHash
            )
            buttonIds.forEach { id ->
                findViewById<Button>(id)?.setOnClickListener {
                    val btn = it as Button
                    val currentText = etDialNumber.text.toString()
                    etDialNumber.setText(currentText + btn.text.toString())
                }
            }

            // 기능 버튼 연결
            val btnCall = findViewById<ImageButton>(R.id.btnCall)
            val btnSms = findViewById<ImageButton>(R.id.btnSms)
            val btnDelete = findViewById<ImageButton>(R.id.btnDelete)

            btnDelete?.setOnClickListener {
                val text = etDialNumber.text.toString()
                if (text.isNotEmpty()) {
                    etDialNumber.setText(text.substring(0, text.length - 1))
                }
            }

            btnCall?.setOnClickListener {
                val number = etDialNumber.text.toString()
                if (number.isNotEmpty()) {
                    val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:$number"))
                    if (ContextCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                        startActivity(intent)
                        // 서버에 통화 이벤트 보고 (여기서 콜백 발송 유도)
                        reportCallEventToServer(number)
                    } else {
                        ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CALL_PHONE), 1001)
                    }
                }
            }

            btnSms?.setOnClickListener {
                val number = etDialNumber.text.toString()
                if (number.isNotEmpty()) {
                    val smsIntent = Intent(Intent.ACTION_SENDTO).apply {
                        data = Uri.parse("smsto:$number")
                        putExtra("sms_body", "[동네비서] 비즈니스 관련하여 연락 드립니다.")
                    }
                    startActivity(smsIntent)
                }
            }

            // 스마트 설정 (체크박스)
            val cbOutgoing = findViewById<CheckBox>(R.id.cbOutgoing)
            val cbIncoming = findViewById<CheckBox>(R.id.cbIncoming)
            val cbBusinessOnly = findViewById<CheckBox>(R.id.cbBusinessOnly)
            
            val prefs = getSharedPreferences("DongneBiseoPrefs", Context.MODE_PRIVATE)
            cbOutgoing?.isChecked = prefs.getBoolean("pref_outgoing", true)
            cbIncoming?.isChecked = prefs.getBoolean("pref_incoming", true)
            cbBusinessOnly?.isChecked = prefs.getBoolean("pref_business_only", false)

            cbOutgoing?.setOnCheckedChangeListener { _, isChecked -> prefs.edit().putBoolean("pref_outgoing", isChecked).apply() }
            cbIncoming?.setOnCheckedChangeListener { _, isChecked -> prefs.edit().putBoolean("pref_incoming", isChecked).apply() }
            cbBusinessOnly?.setOnCheckedChangeListener { _, isChecked -> prefs.edit().putBoolean("pref_business_only", isChecked).apply() }

            // 앱 시작 시 권한 체크 및 내역 로드
            startWaterfallPermissions()
            loadHistory()
            updateStatusText()
            checkForUpdates()

        } catch (e: Exception) {
            android.util.Log.e("DongneBiseo", "초기화 에러: ${e.message}")
        }
    }

    private fun startWaterfallPermissions() {
        if (isPopupActive) return
        isPopupActive = true
        
        if (!hasRequiredPermissions()) {
            val permissions = mutableListOf(
                Manifest.permission.CALL_PHONE,
                Manifest.permission.READ_CONTACTS,
                Manifest.permission.READ_CALL_LOG,
                Manifest.permission.READ_PHONE_STATE
            )
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                permissions.add(Manifest.permission.POST_NOTIFICATIONS)
            }
            ActivityCompat.requestPermissions(this, permissions.toTypedArray(), 1001)
        } else {
            isPopupActive = false
            updateStatusText()
            loadHistory()
            requestBatteryOptimization()
            startPersistentService()
            requestCallScreeningRole() // 권한 허용 완료 시 기본 앱 설정 팝업 자동 실행
        }
    }

    private fun requestCallScreeningRole() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val roleManager = getSystemService(Context.ROLE_SERVICE) as RoleManager
            if (!roleManager.isRoleHeld(RoleManager.ROLE_CALL_SCREENING)) {
                val intent = roleManager.createRequestRoleIntent(RoleManager.ROLE_CALL_SCREENING)
                requestRoleLauncher.launch(intent)
            }
        }
    }

    private fun hasRequiredPermissions(): Boolean {
        val callPhone = ContextCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED
        val readContacts = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED
        val readCallLog = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_CALL_LOG) == PackageManager.PERMISSION_GRANTED
        val readPhoneState = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_STATE) == PackageManager.PERMISSION_GRANTED
        var notifications = true
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notifications = ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        }
        return callPhone && notifications && readContacts && readCallLog && readPhoneState
    }

    private fun reportCallEventToServer(phoneNumber: String) {
        lifecycleScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val url = java.net.URL("https://dongnebiseo.com/api/comm/call-event")
                val conn = url.openConnection() as java.net.HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true

                val json = org.json.JSONObject()
                json.put("customer_phone", phoneNumber)
                json.put("call_type", "발신")
                json.put("auth_token", "DONGNE_BISEO_APP_SECRET_2026_!@")

                val os = conn.outputStream
                os.write(json.toString().toByteArray())
                os.flush()
                os.close()

                if (conn.responseCode == 200) {
                    launch(kotlinx.coroutines.Dispatchers.Main) {
                        Toast.makeText(this@MainActivity, "콜백 문자가 발송되었습니다.", Toast.LENGTH_SHORT).show()
                        loadHistory()
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("DongneBiseo", "API 보고 실패: ${e.message}")
            }
        }
    }

    private fun updateStatusText() {
        val areNotificationsEnabled = androidx.core.app.NotificationManagerCompat.from(this).areNotificationsEnabled()
        if (!areNotificationsEnabled) {
            tvStatusMessage.text = "⚠ 알림 허용 필요"
            tvStatusMessage.setTextColor(android.graphics.Color.RED)
        } else if (!hasRequiredPermissions()) {
            tvStatusMessage.text = "⚠ 권한 허용 필요"
            tvStatusMessage.setTextColor(android.graphics.Color.parseColor("#FF9800"))
        } else {
            tvStatusMessage.text = "✅ 대시보드 활성화"
            tvStatusMessage.setTextColor(android.graphics.Color.parseColor("#4CAF50"))
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1001) {
            loadHistory()
            updateStatusText()
            requestBatteryOptimization()
            startPersistentService()
            requestCallScreeningRole() // 권한 요청 종료 시 기본앱 요청 팝업 유도
        }
    }

    override fun onBackPressed() {
        val webViewDashboard = findViewById<android.webkit.WebView>(R.id.webViewDashboard)
        if (webViewDashboard != null && webViewDashboard.visibility == android.view.View.VISIBLE && webViewDashboard.canGoBack()) {
            webViewDashboard.goBack()
        } else {
            super.onBackPressed()
        }
    }

    private fun showSettingsDialog() {
        AlertDialog.Builder(this)
            .setTitle("권한 설정 안내")
            .setMessage("앱을 정상적으로 사용하려면 [설정] > [권한]에서 모든 권한을 허용해 주세요.")
            .setPositiveButton("설정으로 이동") { _, _ ->
                val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                val uri = Uri.fromParts("package", packageName, null)
                intent.data = uri
                startActivity(intent)
            }
            .setNegativeButton("취소", null)
            .show()
    }

    private fun requestBatteryOptimization() {
        continueToBatteryOptimization()
    }

    private fun continueToBatteryOptimization() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
            if (!pm.isIgnoringBatteryOptimizations(packageName)) {
                try {
                    val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                    intent.data = Uri.parse("package:$packageName")
                    startActivity(intent)
                } catch (e: Exception) {}
            }
        }
    }

    private fun startPersistentService() {
        val serviceIntent = Intent(this, DongneForegroundService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }

    private fun createWebShortcut() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val shortcutManager = getSystemService(android.content.pm.ShortcutManager::class.java)
            if (shortcutManager != null && shortcutManager.isRequestPinShortcutSupported) {
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://dongnebiseo.com/admin/dashboard"))
                val shortcutInfo = android.content.pm.ShortcutInfo.Builder(this, "dongnebiseo_web")
                    .setShortLabel("동네비서")
                    .setLongLabel("동네비서 대시보드")
                    .setIcon(android.graphics.drawable.Icon.createWithResource(this, R.drawable.logo_main))
                    .setIntent(intent)
                    .build()
                shortcutManager.requestPinShortcut(shortcutInfo, null)
            }
        }
    }

    private fun checkForUpdates() {
        lifecycleScope.launch(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val url = java.net.URL("https://dongnebiseo.com/api/app_version")
                val connection = url.openConnection() as java.net.HttpURLConnection
                connection.connectTimeout = 5000
                connection.readTimeout = 5000
                if (connection.responseCode == 200) {
                    val response = connection.inputStream.bufferedReader().readText()
                    val jsonObject = org.json.JSONObject(response)
                    val latestVersion = jsonObject.optString("latest_version", "1.0.0")
                    val updateUrl = jsonObject.optString("update_url", "https://dongnebiseo.com/static/DongneBiseo.apk")
                    val currentVersion = packageManager.getPackageInfo(packageName, 0).versionName ?: "1.0.0"

                    android.util.Log.d("DongneBiseo", "버전 체크: 현재=$currentVersion, 최신=$latestVersion")

                    if (latestVersion != currentVersion) {
                        launch(kotlinx.coroutines.Dispatchers.Main) {
                            showUpdateDialog(updateUrl)
                        }
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e("DongneBiseo", "버전 체크 실패: ${e.message}")
            }
        }
    }

    private fun showUpdateDialog(updateUrl: String) {
        AlertDialog.Builder(this)
            .setTitle("🔔 업데이트 안내")
            .setMessage("더 안정적인 동네비서 최신 버전이 출시되었습니다.\n지금 업데이트하시겠습니까?")
            .setPositiveButton("지금 업데이트") { _, _ ->
                downloadAndInstallApk(updateUrl)
            }
            .setNegativeButton("나중에") { dialog, _ ->
                dialog.dismiss()
            }
            .setCancelable(false)
            .show()
    }

    /**
     * DownloadManager로 APK를 내려받고 완료 후 자동으로 설치 화면을 띄웁니다.
     * Android 7.0+에서 FileProvider, Android 8.0+에서 REQUEST_INSTALL_PACKAGES 처리 포함.
     */
    private fun downloadAndInstallApk(apkUrl: String) {
        try {
            // Android 8+: 알 수 없는 앱 설치 권한 확인
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (!packageManager.canRequestPackageInstalls()) {
                    Toast.makeText(this, "설정 > 앱 > 동네비서 > 알 수 없는 앱 설치를 허용해 주세요", Toast.LENGTH_LONG).show()
                    val intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
                        .setData(Uri.parse("package:$packageName"))
                    startActivity(intent)
                    return
                }
            }

            val apkName = "DongneBiseo_update.apk"
            val destFile = File(getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), apkName)
            if (destFile.exists()) destFile.delete()

            Toast.makeText(this, "⬇️ 업데이트 다운로드 중...", Toast.LENGTH_LONG).show()

            val request = DownloadManager.Request(Uri.parse(apkUrl))
                .setTitle("동네비서 업데이트")
                .setDescription("최신 버전을 다운로드 중입니다")
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationUri(Uri.fromFile(destFile))
                .setMimeType("application/vnd.android.package-archive")

            val dm = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            val downloadId = dm.enqueue(request)

            // 다운로드 완료 수신기
            val receiver = object : BroadcastReceiver() {
                override fun onReceive(ctx: Context, intent: Intent) {
                    val id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1)
                    if (id == downloadId) {
                        unregisterReceiver(this)
                        installApk(destFile)
                    }
                }
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                registerReceiver(receiver, IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE), RECEIVER_NOT_EXPORTED)
            } else {
                @Suppress("UnspecifiedRegisterReceiverFlag")
                registerReceiver(receiver, IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE))
            }
        } catch (e: Exception) {
            android.util.Log.e("DongneBiseo", "다운로드 실패: ${e.message}")
            Toast.makeText(this, "다운로드 실패. 수동으로 설치해 주세요: dongnebiseo.com/download", Toast.LENGTH_LONG).show()
        }
    }

    private fun installApk(apkFile: File) {
        try {
            val apkUri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                FileProvider.getUriForFile(this, "${packageName}.provider", apkFile)
            } else {
                Uri.fromFile(apkFile)
            }
            val install = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(apkUri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(install)
        } catch (e: Exception) {
            android.util.Log.e("DongneBiseo", "설치 실패: ${e.message}")
            Toast.makeText(this, "설치 화면을 열지 못했습니다. 파일 관리자에서 DongneBiseo_update.apk를 실행해 주세요.", Toast.LENGTH_LONG).show()
        }
    }
}
