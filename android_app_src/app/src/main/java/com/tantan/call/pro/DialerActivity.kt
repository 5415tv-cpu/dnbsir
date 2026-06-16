package com.tantan.call.pro

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.CallLog
import android.util.Log
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.ImageButton
import android.widget.RelativeLayout
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import android.widget.Toast
import android.graphics.Color
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class DialerActivity : AppCompatActivity() {

    private lateinit var etPhoneNumber: EditText

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_dialer)

        etPhoneNumber = findViewById(R.id.etPhoneNumber)
        val btnDial = findViewById<ImageButton>(R.id.btnDial)
        val btnDelete = findViewById<ImageButton>(R.id.btnDelete)

        val rvHistory = findViewById<RecyclerView>(R.id.rvHistory)
        val rvContacts = findViewById<RecyclerView>(R.id.rvContacts)
        val btnTabHistory = findViewById<Button>(R.id.btnTabHistory)
        val btnTabContacts = findViewById<Button>(R.id.btnTabContacts)

        // 탭 전환 로직
        btnTabHistory.setOnClickListener {
            rvHistory.visibility = View.VISIBLE
            rvContacts.visibility = View.GONE
            btnTabHistory.setBackgroundResource(R.drawable.tab_selected)
            btnTabHistory.setTextColor(Color.WHITE)
            btnTabContacts.setBackgroundResource(R.drawable.tab_unselected)
            btnTabContacts.setTextColor(Color.parseColor("#888888"))
        }

        btnTabContacts.setOnClickListener {
            rvHistory.visibility = View.GONE
            rvContacts.visibility = View.VISIBLE
            btnTabContacts.setBackgroundResource(R.drawable.tab_selected)
            btnTabContacts.setTextColor(Color.WHITE)
            btnTabHistory.setBackgroundResource(R.drawable.tab_unselected)
            btnTabHistory.setTextColor(Color.parseColor("#888888"))
            loadContacts()
        }

        // 인텐트 데이터 처리 (tel:010...)
        intent.data?.let { uri ->
            if (uri.scheme == "tel") {
                etPhoneNumber.setText(uri.schemeSpecificPart)
            }
        }

        // 숫자 패드 버튼 리스트 및 리스너 연결
        val buttonMap = mapOf(
            R.id.btn0 to "0", R.id.btn1 to "1", R.id.btn2 to "2",
            R.id.btn3 to "3", R.id.btn4 to "4", R.id.btn5 to "5",
            R.id.btn6 to "6", R.id.btn7 to "7", R.id.btn8 to "8",
            R.id.btn9 to "9", R.id.btnStar to "*", R.id.btnHash to "#"
        )

        buttonMap.forEach { (id, value) ->
            findViewById<Button>(id).setOnClickListener {
                etPhoneNumber.append(value)
            }
        }

        findViewById<Button>(R.id.btnOpenSettings).setOnClickListener {
            startActivity(Intent(this, MainActivity::class.java))
        }

        // [신규] 체크박스 설정 연동
        val cbBusinessOnly = findViewById<CheckBox>(R.id.cbDialerBusinessOnly)
        val cbOutgoing = findViewById<CheckBox>(R.id.cbDialerOutgoing)
        val cbIncoming = findViewById<CheckBox>(R.id.cbDialerIncoming)
        
        val prefs = getSharedPreferences("DongneBiseoPrefs", Context.MODE_PRIVATE)
        cbBusinessOnly?.isChecked = prefs.getBoolean("pref_business_only", false)
        cbOutgoing?.isChecked = prefs.getBoolean("pref_outgoing", true)
        cbIncoming?.isChecked = prefs.getBoolean("pref_incoming", true)

        cbBusinessOnly?.setOnCheckedChangeListener { _, isChecked ->
            prefs.edit().putBoolean("pref_business_only", isChecked).apply()
        }
        cbOutgoing?.setOnCheckedChangeListener { _, isChecked ->
            prefs.edit().putBoolean("pref_outgoing", isChecked).apply()
        }
        cbIncoming?.setOnCheckedChangeListener { _, isChecked ->
            prefs.edit().putBoolean("pref_incoming", isChecked).apply()
        }

        loadHistory()

        btnDelete.setOnClickListener {
            val currentText = etPhoneNumber.text.toString()
            if (currentText.isNotEmpty()) {
                etPhoneNumber.setText(currentText.substring(0, currentText.length - 1))
            }
        }

        btnDial.setOnClickListener {
            val number = etPhoneNumber.text.toString()
            if (number.isNotEmpty()) {
                makeCall(number)
            }
        }
    }

    private fun makeCall(number: String) {
        // [핵심] 인앱 다이얼러에서 발신 시 명시적으로 콜백 웹훅 실행
        android.util.Log.d("DongneBiseo", "인앱 다이얼러 발신 감지: $number")
        WebhookManager.processCall(this, number, "발신(인앱)")

        val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:$number"))
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
            startActivity(intent)
        } else {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.CALL_PHONE), 1002)
        }
    }

    override fun onResume() {
        super.onResume()
        loadHistory()
        if (findViewById<RecyclerView>(R.id.rvContacts).visibility == View.VISIBLE) {
            loadContacts()
        }
    }

    private fun loadHistory() {
        val rvHistory = findViewById<RecyclerView>(R.id.rvHistory)
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.READ_CALL_LOG) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.READ_CALL_LOG), 1005)
            return
        }

        val systemHistory = mutableListOf<CallbackHistory>()
        try {
            val cursor = contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.TYPE, CallLog.Calls.DATE, CallLog.Calls.DURATION),
                null, null, "${CallLog.Calls.DATE} DESC LIMIT 50"
            )

            cursor?.use {
                val numberIdx = it.getColumnIndex(CallLog.Calls.NUMBER)
                val typeIdx = it.getColumnIndex(CallLog.Calls.TYPE)
                val dateIdx = it.getColumnIndex(CallLog.Calls.DATE)

                while (it.moveToNext()) {
                    val number = it.getString(numberIdx) ?: "알 수 없음"
                    val typeInt = it.getInt(typeIdx)
                    val date = it.getLong(dateIdx)
                    
                    val typeStr = when (typeInt) {
                        CallLog.Calls.INCOMING_TYPE -> "수신"
                        CallLog.Calls.OUTGOING_TYPE -> "발신"
                        CallLog.Calls.MISSED_TYPE -> "부재중"
                        else -> "기타"
                    }
                    
                    // 기존 CallbackHistory 모델 재활용
                    systemHistory.add(CallbackHistory(number, typeStr, "통화완료", date))
                }
            }
        } catch (e: Exception) {
            Log.e("DongneBiseo", "통화 내역 읽기 실패: ${e.message}")
        }

        rvHistory.layoutManager = LinearLayoutManager(this)
        rvHistory.adapter = HistoryAdapter(systemHistory)
    }

    private fun loadContacts() {
        val rvContacts = findViewById<RecyclerView>(R.id.rvContacts)
        rvContacts.layoutManager = LinearLayoutManager(this)
        val contactList = ContactManager.getBusinessContactsFromSystem(this)
        rvContacts.adapter = ContactAdapter(contactList)
    }

    inner class ContactAdapter(private val items: List<BusinessContact>) : RecyclerView.Adapter<ContactAdapter.ViewHolder>() {
        inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val tvName: TextView = view.findViewById(R.id.tvContactName)
            val tvPhone: TextView = view.findViewById(R.id.tvContactPhone)
            val btnCall: View = view.findViewById(R.id.btnCallAction)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_business_contact, parent, false)
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val item = items[position]
            holder.tvName.text = item.name
            holder.tvPhone.text = item.phone
            holder.itemView.setOnClickListener {
                etPhoneNumber.setText(item.phone)
            }
            holder.btnCall.setOnClickListener {
                makeCall(item.phone)
            }
        }

        override fun getItemCount() = items.size
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

            // [기능 추가] 히스토리에서 바로 전화 걸기
            holder.btnCall.setOnClickListener {
                makeCall(item.phoneNumber)
            }

            // [기능 추가] 히스토리에서 바로 문자 보내기 (다이얼러 입력창에 번호 세팅)
            holder.btnSms.setOnClickListener {
                etPhoneNumber.setText(item.phoneNumber)
                Toast.makeText(this@DialerActivity, "번호가 입력창에 복사되었습니다.", Toast.LENGTH_SHORT).show()
                // 탭을 다이얼러로 변경 (선택 사항)
            }
        }

        override fun getItemCount() = items.size
    }
}
