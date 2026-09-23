/* Hallmark · genre: atmospheric · macrostructure: Workbench · design-system: DESIGN.md · designed-as-app
 * pre-emit critique: P5 H5 E5 S5 R5 V5
 */
package com.zhisheng.weather.ui.components

import android.content.Context
import android.graphics.Paint
import android.graphics.Typeface
import android.provider.Settings
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import com.zhisheng.weather.data.AmbienceLevel
import com.zhisheng.weather.model.ThermalModifier
import com.zhisheng.weather.model.WeatherData
import com.zhisheng.weather.model.WeatherCondition
import com.zhisheng.weather.model.WeatherIntensity
import com.zhisheng.weather.ui.theme.LocalZhishengPalette
import com.zhisheng.weather.ui.theme.ZhishengPalette
import kotlin.math.sin

private const val TRANSITION_MS = 220
private const val STATIC_T = 4.25f
private const val MAX_STEP_SECONDS = 0.04f
private const val PARTICLES = 96
private const val STARS = 96

@Composable
fun WeatherAmbience(
    weather: WeatherData?,
    level: AmbienceLevel,
    modifier: Modifier = Modifier,
    night: Boolean = false,
) {
    if (level == AmbienceLevel.OFF) return
    // 雨天保留独立数据雨舞台，不经过通用氛围层，维持雨滴的灵动节奏。
    if (weather?.current?.condition in setOf(
            WeatherCondition.DRIZZLE,
            WeatherCondition.RAIN,
        )
    ) {
        LegacyDataRain(level, modifier)
        return
    }
    val spec = ambienceSpecOf(weather, night)
    if (spec.kind == AmbienceKind.NONE && spec.thermal == ThermalModifier.NONE) return
    AmbienceStage(spec, level, modifier)
}

@Composable
private fun AmbienceStage(spec: AmbienceSpec, level: AmbienceLevel, modifier: Modifier) {
    val context = LocalContext.current
    val density = LocalDensity.current.density
    val palette = LocalZhishengPalette.current
    val assets = remember { AmbienceAssets() }
    val fade = remember { Animatable(1f) }
    val animated = remember(context) { animatorScale(context) > 0f }
    val dynamic = animated && spec.kind.isDynamic()
    var time by remember { mutableFloatStateOf(STATIC_T) }

    LaunchedEffect(spec.kind, spec.intensity, spec.thermal) {
        if (!animated) fade.snapTo(1f) else {
            fade.snapTo(0f)
            fade.animateTo(1f, tween(TRANSITION_MS, easing = FastOutSlowInEasing))
        }
    }
    LaunchedEffect(dynamic, spec.kind) {
        if (!dynamic) {
            time = STATIC_T
            return@LaunchedEffect
        }
        var last = 0L
        while (true) {
            withFrameNanos { now ->
                if (last != 0L) time += ((now - last) / 1_000_000_000f).coerceAtMost(MAX_STEP_SECONDS)
                last = now
            }
        }
    }

    Canvas(modifier.fillMaxSize()) {
        val vivid = level.vivid
        // SettingsRepository 已为“克制/明显”定义了强度系数，旧实现却没有真正使用，
        // 导致两档差别很小。这里让设置值成为唯一强度来源。
        val gain = level.factor * fade.value * if (palette.isLight) 0.78f else 1f
        drawAmbience(spec, time * level.motionScale, gain, vivid, density, palette, assets)
    }
}

private fun DrawScope.drawAmbience(
    spec: AmbienceSpec,
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    palette: ZhishengPalette,
    assets: AmbienceAssets,
) {
    if (gain <= 0.001f) return
    val colors = AmbienceColors(palette)
    when (spec.kind) {
        AmbienceKind.NONE -> Unit
        AmbienceKind.CLEAR_DAY -> drawClearGrid(time, gain, vivid, density, colors, assets)
        AmbienceKind.STARFIELD -> drawPixelStars(time, gain, vivid, density, colors, assets)
        AmbienceKind.PARTLY_CLOUDY -> drawCloudBuffers(spec, time, gain, vivid, density, colors, assets, dense = false)
        AmbienceKind.OVERCAST -> drawCloudBuffers(spec, time, gain, vivid, density, colors, assets, dense = true)
        AmbienceKind.DRIZZLE -> drawDataRain(time, gain, vivid, density, colors, assets)
        AmbienceKind.RAIN -> drawDataRain(time, gain, vivid, density, colors, assets)
        AmbienceKind.SLEET -> {
            drawDataRain(time, gain * 0.9f, vivid, density, colors, assets)
            drawSnow(spec, time, gain * 0.72f, vivid, density, colors, assets, 0.48f)
        }
        AmbienceKind.SNOW -> drawSnow(spec, time, gain, vivid, density, colors, assets, 1f)
        AmbienceKind.STORM -> drawStorm(spec, time, gain, vivid, density, colors, assets)
        AmbienceKind.HAIL -> drawHail(spec, time, gain, vivid, density, colors, assets)
        AmbienceKind.FREEZING_RAIN -> drawFreezingRain(spec, time, gain, vivid, density, colors, assets)
        AmbienceKind.FOG -> drawVisibilityLines(spec, time, gain, vivid, density, colors)
        AmbienceKind.HAZE -> drawHazeDither(spec, time, gain, vivid, density, colors, assets)
        AmbienceKind.SAND -> drawWindField(spec, time, gain, vivid, density, colors, assets, sand = true)
        AmbienceKind.WIND -> drawWindField(spec, time, gain, vivid, density, colors, assets, sand = false)
    }
    drawThermalModifier(spec.thermal, gain, vivid, density, colors)
}

private fun DrawScope.drawClearGrid(
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    c: AmbienceColors,
    a: AmbienceAssets,
) {
    // 晴天不再画一张静态工程网格。它沿用数据雨的成功逻辑：每束光都有独立相位、
    // 速度和长度，只是运动轴改成斜向的光子时钟脉冲，既有生命感又不像降水。
    val count = if (vivid) 58 else 34
    val pad = 72f * density
    val span = size.width + pad * 2f
    for (i in 0 until count) {
        val speed = 7f + a.speed[i] * 18f
        val x = (time * speed + a.phase[i] * span) % span - pad
        val ySpan = size.height + pad * 2f
        val y = (a.y[i] * ySpan + x * 0.16f + a.phase[i] * 34f * density) % ySpan - pad
        val length = (3.5f + a.length[i] * 9f) * density
        val pulse = 0.62f + 0.38f * (0.5f + 0.5f * sin(time * (0.35f + a.speed[i] * 0.25f) + a.phase[i] * 6.283f))
        val hot = a.hot[i]
        val color = if (hot) c.cyan else c.orange
        val alpha = clampAlpha((if (hot) 0.050f else 0.034f) * gain * pulse)
        drawLine(
            color.copy(alpha = alpha * 0.36f),
            Offset(x - length * 1.8f, y - length * 0.29f),
            Offset(x - length * 0.42f, y - length * 0.07f),
            density * 0.55f,
        )
        drawLine(
            color.copy(alpha = alpha),
            Offset(x, y),
            Offset(x + length, y + length * 0.16f),
            density * if (hot) 1.05f else 0.72f,
        )
        if (hot && pulse > 0.88f) {
            val r = 2.8f * density
            drawLine(color.copy(alpha = alpha * 0.72f), Offset(x - r, y), Offset(x + r, y), density * 0.55f)
            drawLine(color.copy(alpha = alpha * 0.72f), Offset(x, y - r), Offset(x, y + r), density * 0.55f)
        }
    }

    // 一条极慢的曝光基准线把散开的脉冲组织起来；只占边缘，不穿过核心读数。
    val exposureY = size.height * (0.13f + ((time * 0.009f) % 0.12f))
    val exposureX = size.width * 0.68f
    drawLine(
        c.orange.copy(alpha = clampAlpha(0.040f * gain)),
        Offset(exposureX, exposureY),
        Offset(size.width * 0.94f, exposureY),
        density * 0.62f,
    )
    repeat(4) { tick ->
        val tx = exposureX + (size.width * 0.26f / 3f) * tick
        drawLine(
            c.orange.copy(alpha = clampAlpha(0.055f * gain)),
            Offset(tx, exposureY - 2.2f * density),
            Offset(tx, exposureY + 2.2f * density),
            density * 0.62f,
        )
    }
}

private fun DrawScope.drawPixelStars(time: Float, gain: Float, vivid: Boolean, density: Float, c: AmbienceColors, a: AmbienceAssets) {
    val count = if (vivid) STARS else 58
    for (i in 0 until count) {
        val x = a.x[i] * size.width
        val y = a.y[i] * size.height
        val px = (if (a.hot[i]) 1.8f else 1.05f) * density
        val pulse = 0.20f + 0.80f * (0.5f + 0.5f * sin(time * (0.18f + a.speed[i] * 0.48f) + a.phase[i] * 6.283f))
        val starColor = if (a.hot[i]) c.cyan else c.text
        drawRect(starColor.copy(alpha = clampAlpha((if (a.hot[i]) 0.095f else 0.047f) * gain * pulse)), Offset(x, y), Size(px, px))
        if (a.hot[i] && pulse > 0.78f) {
            val r = (3.2f + a.length[i] * 4.5f) * density
            val lock = c.cyan.copy(alpha = clampAlpha(0.050f * gain * pulse))
            drawLine(lock, Offset(x - r, y + px / 2f), Offset(x - px, y + px / 2f), density * 0.48f)
            drawLine(lock, Offset(x + px * 2f, y + px / 2f), Offset(x + r, y + px / 2f), density * 0.48f)
            drawLine(lock, Offset(x + px / 2f, y - r), Offset(x + px / 2f, y - px), density * 0.48f)
            drawLine(lock, Offset(x + px / 2f, y + px * 2f), Offset(x + px / 2f, y + r), density * 0.48f)
        }
    }

    // 星图只连一组稳定锚点，避免整屏变成常见的“星座连线”模板。
    val constellation = intArrayOf(2, 17, 41, 63)
    for (i in 0 until constellation.lastIndex) {
        val from = constellation[i]
        val to = constellation[i + 1]
        drawLine(
            c.cyan.copy(alpha = clampAlpha(0.018f * gain)),
            Offset(a.x[from] * size.width, a.y[from] * size.height),
            Offset(a.x[to] * size.width, a.y[to] * size.height),
            density * 0.42f,
        )
    }
}

private fun DrawScope.drawCloudBuffers(
    spec: AmbienceSpec,
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    c: AmbienceColors,
    a: AmbienceAssets,
    dense: Boolean,
) {
    val cover = (spec.cloudCover ?: if (dense) 90f else 55f).coerceIn(0f, 100f)
    val count = ((if (dense) 34 else 20) + cover / 5f + if (vivid) 10 else 0).toInt().coerceAtMost(PARTICLES)
    val paint = a.paint.apply {
        textAlign = Paint.Align.LEFT
        textSize = (if (dense) 9.2f else 8.7f) * density
    }
    val canvas = drawContext.canvas.nativeCanvas
    val pad = 118f * density
    val span = size.width + pad * 2f
    for (i in 0 until count) {
        val direction = if (i % 5 == 0) -1f else 1f
        val speed = (3.8f + a.speed[i] * if (dense) 9f else 13f) * direction
        val rawX = a.phase[i] * span + time * speed
        val x = ((rawX % span) + span) % span - pad
        // 云层保留上下呼吸空间，不覆盖状态栏和底部操作区；每条缓存流独立漂移。
        val y = size.height * (0.13f + a.y[i] * if (dense) 0.72f else 0.61f)
        val pulse = 0.58f + 0.42f * (0.5f + 0.5f * sin(time * (0.12f + a.speed[i] * 0.18f) + a.phase[i] * 6.283f))
        val hot = a.hot[i] && i % 3 == 0
        val color = if (hot) c.cyan else c.textTertiary
        val alpha = clampAlpha((if (hot) 0.042f else if (dense) 0.040f else 0.034f) * gain * pulse)
        paint.color = color.copy(alpha = alpha).toArgb()
        val token = when (i % 7) {
            0 -> "00110"
            1 -> "00000000"
            2 -> "1110"
            3 -> "// //"
            4 -> "010011"
            5 -> "0001"
            else -> "0111110"
        }
        canvas.drawText(token, x, y, paint)

        // 每个字符云团带一段更淡的尾部，形成类似数据雨的“流”，不再是僵硬方框。
        val tail = (18f + a.length[i] * 38f) * density
        drawLine(
            color.copy(alpha = alpha * 0.32f),
            Offset(x - tail * direction, y - 3.2f * density),
            Offset(x - 4f * density * direction, y - 3.2f * density),
            density * 0.48f,
        )
    }
}

private fun intensityFactor(intensity: WeatherIntensity): Float = when (intensity) {
    WeatherIntensity.LIGHT -> 0.58f
    WeatherIntensity.MODERATE -> 0.82f
    WeatherIntensity.HEAVY -> 1f
    WeatherIntensity.EXTREME -> 1.18f
}

private fun particleCount(spec: AmbienceSpec, vivid: Boolean, scale: Float = 1f): Int {
    val base = 18f + 30f * intensityFactor(spec.intensity)
    return (base * (if (vivid) 1.15f else 0.78f) * scale).toInt().coerceIn(8, PARTICLES)
}

private fun DrawScope.drawDataRain(
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    c: AmbienceColors,
    a: AmbienceAssets,
) {
    // 完整恢复 0.0.8 的视觉参数：46/88 条流、22 列、11dp 字符、3~7 字拖尾。
    // 这里只把 Paint 提升为复用对象，不改变旧版构图、亮度与运动节奏。
    val count = if (vivid) 88 else 46
    val glyph = 11f * density
    val cols = 22
    val colWidth = size.width / cols
    val motion = if (vivid) 1.32f else 1f
    val canvas = drawContext.canvas.nativeCanvas
    val paint = a.paint.apply { textSize = glyph }
    val headAlpha = 0.052f * gain
    for (i in 0 until count) {
        val seed = i * 7919 + 13
        val col = Math.floorMod(seed, cols)
        val streamSpeed = 0.35f + Math.floorMod(seed * 37, 100) / 100f * 0.75f
        val phase = Math.floorMod(seed * 61, 100) / 100f
        val tail = 3 + Math.floorMod(seed * 13, 5)
        val cycle = size.height + tail * glyph * 1.4f
        val y = (time * streamSpeed * 190f * motion + phase * cycle) % cycle
        val x = col * colWidth + colWidth * 0.28f
        for (k in 0 until tail) {
            val yy = y - k * glyph * 1.4f
            if (yy < -glyph || yy > size.height) continue
            val fade = 1f - k.toFloat() / tail
            // 旧版的关键是同色、线性渐隐；不再单独点亮青色字头。
            val alpha = clampAlpha(headAlpha * fade)
            paint.color = c.mint.copy(alpha = alpha).toArgb()
            val bit = if (((col * 31 + k * 17 + (y / glyph).toInt()) and 1) == 0) "0" else "1"
            canvas.drawText(bit, x, yy, paint)
        }
    }
}

private fun DrawScope.drawSnow(
    spec: AmbienceSpec,
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    c: AmbienceColors,
    a: AmbienceAssets,
    scale: Float,
) {
    val count = particleCount(spec, vivid, scale)
    val paint = a.paint.apply { textAlign = Paint.Align.CENTER }
    val canvas = drawContext.canvas.nativeCanvas
    for (i in 0 until count) {
        val glyph = (8f + a.length[i] * 8f) * density
        paint.textSize = glyph
        val cycle = size.height + glyph * 3f
        val y = (time * (24f + a.speed[i] * 34f) + a.phase[i] * cycle) % cycle
        val sway = sin(time * 0.5f + a.phase[i] * 6.283f) * 17f * density * (a.speed[i] * 2f - 1f)
        val x = a.x[i] * size.width + sway
        paint.color = c.text.copy(alpha = clampAlpha((0.062f + a.speed[i] * 0.040f) * gain)).toArgb()
        val glyphText = when (i % 5) {
            0 -> "*"
            1 -> "·"
            2 -> "A"
            3 -> "F"
            else -> "*"
        }
        canvas.drawText(glyphText, x, y, paint)
    }
}

private fun DrawScope.drawStorm(
    spec: AmbienceSpec,
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    c: AmbienceColors,
    a: AmbienceAssets,
) {
    drawDataRain(time, gain * 0.88f, vivid, density, c, a)
    val local = time % 5.4f
    if (local < 0.13f || local in 0.23f..0.29f) {
        val path = Path().apply {
            moveTo(size.width * 0.72f, size.height * 0.08f)
            lineTo(size.width * 0.60f, size.height * 0.32f)
            lineTo(size.width * 0.69f, size.height * 0.32f)
            lineTo(size.width * 0.54f, size.height * 0.61f)
        }
        drawPath(path, c.cyan.copy(alpha = clampAlpha((if (vivid) 0.18f else 0.09f) * gain)), style = Stroke(width = 1.6f * density))
    }
    val scanY = ((time * 0.17f) % 1f) * size.height
    drawLine(c.cyan.copy(alpha = clampAlpha(0.045f * gain)), Offset(0f, scanY), Offset(size.width, scanY), 1f)
}

private fun DrawScope.drawHail(
    spec: AmbienceSpec,
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    c: AmbienceColors,
    a: AmbienceAssets,
) {
    val count = particleCount(spec, vivid, 0.74f)
    val paint = a.paint.apply {
        textAlign = Paint.Align.CENTER
        textSize = 10.5f * density
    }
    val canvas = drawContext.canvas.nativeCanvas
    for (i in 0 until count) {
        val cycle = size.height + 40f * density
        val y = (time * (150f + a.speed[i] * 190f) + a.phase[i] * cycle) % cycle
        val x = a.x[i] * size.width
        paint.color = c.cyan.copy(alpha = clampAlpha((0.080f + a.speed[i] * 0.060f) * gain)).toArgb()
        canvas.drawText(if (i % 3 == 0) "##" else "[]", x, y, paint)
    }
}

private fun DrawScope.drawFreezingRain(
    spec: AmbienceSpec,
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    c: AmbienceColors,
    a: AmbienceAssets,
) {
    drawDataRain(time, gain * 0.78f, vivid, density, c, a)
    val paint = a.paint.apply {
        textAlign = Paint.Align.CENTER
        textSize = 10f * density
    }
    val canvas = drawContext.canvas.nativeCanvas
    repeat(if (vivid) 24 else 14) { i ->
        val x = a.x[i] * size.width
        // 字符下落到各自冻结线后停住，形成被锁死的终端游标。
        val freezeLine = size.height * (0.54f + a.y[i] * 0.38f)
        val fall = (time * (55f + a.speed[i] * 70f) + a.phase[i] * size.height) % size.height
        val y = minOf(fall, freezeLine)
        paint.color = c.cyan.copy(alpha = clampAlpha((if (fall >= freezeLine) 0.11f else 0.065f) * gain)).toArgb()
        canvas.drawText(if (fall >= freezeLine) "#" else "|", x, y, paint)
    }
}

private fun DrawScope.drawVisibilityLines(spec: AmbienceSpec, time: Float, gain: Float, vivid: Boolean, density: Float, c: AmbienceColors) {
    val visibility = spec.visibilityKm ?: 8f
    val rows = (4 + ((12f - visibility).coerceIn(0f, 10f) / 2f).toInt() + if (vivid) 2 else 0).coerceIn(4, 11)
    for (row in 0 until rows) {
        val y = size.height * (0.18f + row * 0.64f / rows)
        val segment = (28f + row % 3 * 12f) * density
        val drift = ((time * (3f + row % 3) * density + row * segment * 0.37f) % (segment * 1.8f))
        var x = -segment * 1.8f + drift
        while (x < size.width + segment) {
            drawLine(c.text.copy(alpha = clampAlpha(0.040f * gain)), Offset(x, y), Offset((x + segment).coerceAtMost(size.width), y), density * 0.55f)
            x += segment * 1.8f
        }
    }
    val cursorY = size.height * (0.2f + ((time * 0.025f) % 0.62f))
    drawLine(c.cyan.copy(alpha = clampAlpha(0.038f * gain)), Offset(0f, cursorY), Offset(size.width * 0.22f, cursorY), density * 0.65f)
}

private fun DrawScope.drawHazeDither(spec: AmbienceSpec, time: Float, gain: Float, vivid: Boolean, density: Float, c: AmbienceColors, a: AmbienceAssets) {
    val aqi = spec.aqi ?: 100
    val count = (if (vivid) 54 else 34) + if (aqi >= 200) 12 else 0
    val paint = a.paint.apply {
        textAlign = Paint.Align.LEFT
        textSize = 8.5f * density
    }
    val canvas = drawContext.canvas.nativeCanvas
    for (i in 0 until count.coerceAtMost(PARTICLES)) {
        val span = size.width + 80f * density
        val x = (a.x[i] * span + time * (4f + a.speed[i] * 8f)) % span - 40f * density
        val y = a.y[i] * size.height
        paint.color = c.orange.copy(alpha = clampAlpha((0.025f + a.speed[i] * 0.025f) * gain)).toArgb()
        val token = when (i % 4) { 0 -> "CRC"; 1 -> "!"; 2 -> "ERR"; else -> "?" }
        canvas.drawText(token, x, y, paint)
    }
}

private fun DrawScope.drawWindField(
    spec: AmbienceSpec,
    time: Float,
    gain: Float,
    vivid: Boolean,
    density: Float,
    c: AmbienceColors,
    a: AmbienceAssets,
    sand: Boolean,
) {
    val count = particleCount(spec, vivid, if (sand) 1f else 0.72f)
    val speedBoost = 0.75f + spec.windSpeedKmh.coerceAtMost(90f) / 90f
    val color = if (sand) c.orange else c.cyan
    val paint = a.paint.apply {
        textAlign = Paint.Align.LEFT
        textSize = (if (sand) 9f else 11f) * density
    }
    val canvas = drawContext.canvas.nativeCanvas
    for (i in 0 until count) {
        val pad = 90f * density
        val span = size.width + pad * 2f
        val speed = (48f + a.speed[i] * 105f) * speedBoost
        val x = span - ((time * speed + a.phase[i] * span) % span) - pad
        val y = a.y[i] * size.height
        paint.color = color.copy(alpha = clampAlpha((0.045f + a.speed[i] * 0.055f) * gain)).toArgb()
        val token = if (sand) {
            when (i % 4) { 0 -> "FF"; 1 -> "7E"; 2 -> "//"; else -> "00" }
        } else {
            when (i % 3) { 0 -> "<"; 1 -> "<<"; else -> "<<<" }
        }
        canvas.drawText(token, x, y, paint)
    }
}

private fun DrawScope.drawThermalModifier(thermal: ThermalModifier, gain: Float, vivid: Boolean, density: Float, c: AmbienceColors) {
    if (thermal == ThermalModifier.NONE) return
    val color = if (thermal == ThermalModifier.HOT) c.orange else c.cyan
    val count = if (vivid) 9 else 6
    repeat(count) { i ->
        val y = size.height * (0.18f + i * 0.64f / count)
        val len = (if (i % 2 == 0) 14f else 8f) * density
        drawLine(color.copy(alpha = clampAlpha(0.09f * gain)), Offset(0f, y), Offset(len, y), 1.4f)
        drawLine(color.copy(alpha = clampAlpha(0.09f * gain)), Offset(size.width - len, y), Offset(size.width, y), 1.4f)
    }
}

private class AmbienceColors(p: ZhishengPalette) {
    val mint: Color = p.mint
    val cyan: Color = p.cyan
    val orange: Color = p.orange
    val text: Color = p.text
    val textTertiary: Color = p.textTertiary
}

private class AmbienceAssets {
    val paint: Paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        typeface = Typeface.MONOSPACE
        textAlign = Paint.Align.LEFT
    }
    val x = FloatArray(maxOf(PARTICLES, STARS))
    val y = FloatArray(maxOf(PARTICLES, STARS))
    val phase = FloatArray(maxOf(PARTICLES, STARS))
    val speed = FloatArray(maxOf(PARTICLES, STARS))
    val length = FloatArray(maxOf(PARTICLES, STARS))
    val hot = BooleanArray(maxOf(PARTICLES, STARS))

    init {
        val random = StableRandom(0x5A17)
        for (i in x.indices) {
            x[i] = random.next()
            y[i] = random.next()
            phase[i] = random.next()
            speed[i] = random.next()
            length[i] = random.next()
            hot[i] = random.next() > 0.86f
        }
    }
}

private class StableRandom(private var state: Int) {
    fun next(): Float {
        state = state * 1664525 + 1013904223
        return ((state ushr 8) and 0xFFFF) / 65535f
    }
}

private fun clampAlpha(value: Float): Float = value.coerceIn(0f, 1f)

private fun animatorScale(context: Context): Float = runCatching {
    Settings.Global.getFloat(context.contentResolver, Settings.Global.ANIMATOR_DURATION_SCALE, 1f)
}.getOrDefault(1f)
