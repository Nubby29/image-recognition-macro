package com.nubby29.imagemacro

// Image Recognition Macro v0.1.0

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.view.accessibility.AccessibilityEvent

class MacroAccessibilityService : AccessibilityService() {
    companion object {
        var instance: MacroAccessibilityService? = null
            private set
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) = Unit
    override fun onInterrupt() = Unit

    override fun onDestroy() {
        instance = null
        super.onDestroy()
    }

    fun tap(x: Int, y: Int, durationMs: Long = 50L): Boolean {
        val path = Path().apply { moveTo(x.toFloat(), y.toFloat()) }
        val stroke = GestureDescription.StrokeDescription(path, 0, durationMs)
        return dispatchGesture(
            GestureDescription.Builder().addStroke(stroke).build(), null, null
        )
    }
}
