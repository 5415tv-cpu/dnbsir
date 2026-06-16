package com.tantan.call.pro

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

object ServiceStateManager {
    private val _isServiceActive = MutableStateFlow(false)
    val isServiceActive: StateFlow<Boolean> = _isServiceActive

    fun setServiceActive(active: Boolean) {
        _isServiceActive.value = active
    }
}
