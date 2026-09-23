package com.zhisheng.weather.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.res.painterResource
import com.zhisheng.weather.model.WeatherCondition
import com.zhisheng.weather.model.conditionIconRes
import com.zhisheng.weather.ui.theme.LocalZhishengPalette

// 天气图标组件。资源映射收敛在 model/ConditionIcons.kt（与小组件共用同一真源，v0.0.4）。
// 图标为平面双色调 PNG，颜色已内置于位图，不统一染色。
// v0.0.5 浅色模式：位图是深底亮线设计，直接放纸白底会发白看不清——
// 用 SrcIn 把线条统一染成钢青，呈单色青线（清冷翡翠质感；此前染成墨黑太硬）。
@Composable
fun WeatherIcon(
    condition: WeatherCondition?,
    modifier: Modifier = Modifier,
) {
    val res = conditionIconRes(condition)
    if (res != null) {
        val palette = LocalZhishengPalette.current
        Box(modifier = modifier) {
            Image(
                painter = painterResource(res),
                contentDescription = condition?.label,
                modifier = Modifier.fillMaxSize(),
                colorFilter = if (palette.isLight) ColorFilter.tint(palette.cyan, BlendMode.SrcIn) else null,
            )
            if (condition == WeatherCondition.HAIL || condition == WeatherCondition.FREEZING_RAIN ||
                condition == WeatherCondition.FREEZING_DRIZZLE
            ) {
                Canvas(Modifier.fillMaxSize()) {
                    val color = if (condition == WeatherCondition.HAIL) palette.orange else palette.cyan
                    val cx = size.width * 0.78f
                    val cy = size.height * 0.24f
                    val r = size.minDimension * 0.10f
                    if (condition == WeatherCondition.HAIL) {
                        val diamond = Path().apply {
                            moveTo(cx, cy - r)
                            lineTo(cx + r, cy)
                            lineTo(cx, cy + r)
                            lineTo(cx - r, cy)
                            close()
                        }
                        drawPath(diamond, color, style = Stroke(width = size.minDimension * 0.018f))
                    } else {
                        drawLine(color, androidx.compose.ui.geometry.Offset(cx - r, cy), androidx.compose.ui.geometry.Offset(cx + r, cy), size.minDimension * 0.018f)
                        drawLine(color, androidx.compose.ui.geometry.Offset(cx, cy - r), androidx.compose.ui.geometry.Offset(cx, cy + r), size.minDimension * 0.018f)
                    }
                }
            }
        }
    }
}
