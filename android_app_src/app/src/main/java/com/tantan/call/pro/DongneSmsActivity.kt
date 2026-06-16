package com.tantan.call.pro

import android.app.Activity
import android.os.Bundle

class DongneSmsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 화면 없이 기본 SMS 앱 인텐트를 처리하고 종료
        finish()
    }
}
