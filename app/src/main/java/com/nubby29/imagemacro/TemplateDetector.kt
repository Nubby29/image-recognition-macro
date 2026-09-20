package com.nubby29.imagemacro

// Image Recognition Macro v0.1.0

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

data class DetectionResult(val x: Int, val y: Int, val confidence: Double)

object TemplateDetector {
    fun find(screen: Bitmap?, templatePath: String, threshold: Double): DetectionResult? {
        if (screen == null) return null
        val template = BitmapFactory.decodeFile(templatePath) ?: return null
        if (template.width > screen.width || template.height > screen.height) {
            template.recycle()
            return null
        }

        val step = max(2, min(template.width, template.height) / 12)
        val points = ArrayList<Pair<Int, Int>>()
        var y = 0
        while (y < template.height) {
            var x = 0
            while (x < template.width) {
                points.add(x to y)
                x += step
            }
            y += step
        }

        var bestScore = Double.NEGATIVE_INFINITY
        var bestX = 0
        var bestY = 0
        val maxX = screen.width - template.width
        val maxY = screen.height - template.height
        val scanStep = max(1, min(template.width, template.height) / 8)

        var sy = 0
        while (sy <= maxY) {
            var sx = 0
            while (sx <= maxX) {
                var error = 0.0
                for ((tx, ty) in points) {
                    error += colorDistance(screen.getPixel(sx + tx, sy + ty), template.getPixel(tx, ty))
                }
                val score = 1.0 - error / (points.size * 765.0)
                if (score > bestScore) {
                    bestScore = score
                    bestX = sx
                    bestY = sy
                }
                sx += scanStep
            }
            sy += scanStep
        }

        val centerX = bestX + template.width / 2
        val centerY = bestY + template.height / 2
        template.recycle()
        return if (bestScore >= threshold) DetectionResult(centerX, centerY, bestScore) else null
    }

    private fun colorDistance(a: Int, b: Int): Int {
        return abs((a shr 16 and 255) - (b shr 16 and 255)) +
            abs((a shr 8 and 255) - (b shr 8 and 255)) +
            abs((a and 255) - (b and 255))
    }
}
