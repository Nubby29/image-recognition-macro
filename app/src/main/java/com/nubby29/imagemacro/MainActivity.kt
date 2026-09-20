package com.nubby29.imagemacro

// Image Recognition Macro v0.1.0

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import java.io.File

class MainActivity : AppCompatActivity() {
    private lateinit var status: TextView
    private val pickTemplate = 1001
    private val captureRequest = 1002

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        status = findViewById(R.id.status)

        findViewById<Button>(R.id.accessibilityButton).setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        findViewById<Button>(R.id.captureButton).setOnClickListener { requestScreenCapture() }
        findViewById<Button>(R.id.testButton).setOnClickListener { pickTemplateImage() }
    }

    private fun requestScreenCapture() {
        val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as android.media.projection.MediaProjectionManager
        startActivityForResult(manager.createScreenCaptureIntent(), captureRequest)
    }

    private fun pickTemplateImage() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            type = "image/*"
            addCategory(Intent.CATEGORY_OPENABLE)
        }
        startActivityForResult(intent, pickTemplate)
    }

    @Deprecated("Use Activity Result API in a later UI pass")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == captureRequest && resultCode == Activity.RESULT_OK && data != null) {
            val serviceIntent = Intent(this, ScreenCaptureService::class.java).apply {
                putExtra(ScreenCaptureService.EXTRA_RESULT_CODE, resultCode)
                putExtra(ScreenCaptureService.EXTRA_DATA, data)
            }
            startForegroundService(serviceIntent)
            status.text = "Screen capture running. Pick a template to test detection."
        }

        if (requestCode == pickTemplate && resultCode == Activity.RESULT_OK && data?.data != null) {
            val file = File(filesDir, "template.png")
            contentResolver.openInputStream(data.data!!)?.use { input ->
                file.outputStream().use { output -> input.copyTo(output) }
            }
            status.text = "Template saved. Testing..."
            val result = TemplateDetector.find(ScreenCaptureService.latestFrame, file.absolutePath, 0.80)
            if (result != null) {
                status.text = "FOUND at (" + result.x + ", " + result.y + ") confidence=" +
                    String.format("%.2f", result.confidence)
                MacroAccessibilityService.instance?.tap(result.x, result.y)
            } else {
                status.text = "Image not found at confidence 0.80."
            }
        }
    }
}
