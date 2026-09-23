package com.zhisheng.weather.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalDensity
import com.zhisheng.weather.data.AmbienceLevel
import com.zhisheng.weather.ui.theme.LocalZhishengPalette

// 从 0.0.8 原文件直接恢复的数据雨实现。除函数名外不改绘制参数与运动公式。
private class LegacyRainParticle(seed: Int, val cols: Int) {
    val col = seed % cols
    val speed = 0.35f + (seed * 37 % 100) / 100f * 0.75f
    val phase = (seed * 61 % 100) / 100f
    val len = 3 + (seed * 13 % 5)
    val drift = ((seed * 29 % 100) / 100f - 0.5f) * 2f
}

@Composable
internal fun LegacyDataRain(
    level: AmbienceLevel,
    modifier: Modifier = Modifier,
) {
    var t by remember { mutableFloatStateOf(0f) }
    LaunchedEffect(Unit) {
        var last = 0L
        while (true) {
            withFrameNanos { now ->
                if (last != 0L) t += (now - last) / 1_000_000_000f
                last = now
            }
        }
    }

    val density = LocalDensity.current
    val f = level.factor
    val vivid = level.vivid
    val motion = level.motionScale
    val particleCount = if (vivid) 88 else 46
    val particles = remember(level) {
        List(particleCount) { LegacyRainParticle(it * 7919 + 13, 22) }
    }
    val monoTypeface = remember { android.graphics.Typeface.MONOSPACE }
    val rainMint = LocalZhishengPalette.current.mint

    Canvas(modifier = modifier.fillMaxSize()) {
        drawLegacyDataRain(t, f, motion, particles, density.density, monoTypeface, rainMint)
    }
}

private fun DrawScope.drawLegacyDataRain(
    t: Float,
    f: Float,
    motion: Float,
    particles: List<LegacyRainParticle>,
    densityScale: Float,
    typeface: android.graphics.Typeface,
    mintColor: Color,
) {
    val colW = size.width / 22f
    val glyph = 11f * densityScale
    val paint = android.graphics.Paint().apply {
        this.typeface = typeface
        textSize = glyph
        isAntiAlias = true
    }
    val baseAlpha = 0.052f * f
    particles.forEach { p ->
        val cycle = size.height + p.len * glyph * 1.4f
        val y = ((t * p.speed * 190f * motion + p.phase * cycle) % cycle)
        val x = p.col * colW + colW * 0.28f
        for (i in 0 until p.len) {
            val yy = y - i * glyph * 1.4f
            if (yy < -glyph || yy > size.height) continue
            val a = baseAlpha * (1f - i.toFloat() / p.len)
            paint.color = mintColor.copy(alpha = a.coerceIn(0f, 1f)).toArgb()
            val ch = if (((p.col * 31 + i * 17 + (y / glyph).toInt()) % 2) == 0) "0" else "1"
            drawContext.canvas.nativeCanvas.drawText(ch, x, yy, paint)
        }
    }
}
