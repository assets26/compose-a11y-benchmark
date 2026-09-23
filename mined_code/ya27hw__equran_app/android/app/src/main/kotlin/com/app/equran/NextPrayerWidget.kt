package com.app.equran

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider

class NextPrayerWidget : GlanceAppWidget() {

  override suspend fun provideGlance(
    context: Context,
    id: GlanceId
  ) {
    val state = loadPrayerWidgetState(context)

    provideContent {
      GlanceTheme {
        if (state.fajr == null) {
          CompactPlaceholder(
            bgColor = state.palette.bgColor,
            primaryColor = state.palette.primaryColor,
            mutedColor = state.palette.textMutedColor,
            label = state.labels.headerLabel,
          )
        } else {
          CompactWidgetContent(state = state)
        }
      }
    }
  }
}

@Composable
private fun CompactPlaceholder(
  bgColor: androidx.compose.ui.graphics.Color,
  primaryColor: androidx.compose.ui.graphics.Color,
  mutedColor: androidx.compose.ui.graphics.Color,
  label: String,
) {
  Box(
    modifier = GlanceModifier
      .fillMaxSize()
      .background(bgColor)
      .padding(10.dp)
      .clickable(actionStartActivity<MainActivity>()),
    contentAlignment = Alignment.Center,
  ) {
    Column(
      horizontalAlignment = Alignment.CenterHorizontally,
      verticalAlignment = Alignment.CenterVertically,
    ) {
      Text(
        text = "eQuran",
        style = TextStyle(
          color = ColorProvider(primaryColor),
          fontSize = 13.sp,
          fontWeight = FontWeight.Bold,
        )
      )
      Spacer(GlanceModifier.height(4.dp))
      Text(
        text = label,
        style = TextStyle(
          color = ColorProvider(mutedColor),
          fontSize = 9.sp,
        )
      )
    }
  }
}

@Composable
private fun CompactWidgetContent(state: PrayerWidgetState) {
  val nextLabel = prayerLabelForId(state.next, state.labels)
  val nextTime = if (state.nextTime.isNotEmpty()) {
    state.nextTime
  } else {
    prayerTimeForId(state, state.next)
  }
  val supportingLine = compactSupportingLine(state.loc, state.updated)

  Box(
    modifier = GlanceModifier
      .fillMaxSize()
      .background(state.palette.primaryStrongColor)
      .padding(10.dp)
      .clickable(actionStartActivity<MainActivity>()),
    contentAlignment = Alignment.CenterStart,
  ) {
    Column(
      modifier = GlanceModifier.fillMaxSize(),
      verticalAlignment = Alignment.CenterVertically,
    ) {
      Text(
        text = if (nextLabel.isNotEmpty()) nextLabel else state.labels.headerLabel,
        style = TextStyle(
          color = ColorProvider(state.palette.goldColor),
          fontSize = 10.sp,
          fontWeight = FontWeight.Bold,
        )
      )
      Spacer(GlanceModifier.height(2.dp))
      Text(
        text = if (nextTime.isNotEmpty()) nextTime else "---",
        style = TextStyle(
          color = ColorProvider(state.palette.onPrimaryColor),
          fontSize = 18.sp,
          fontWeight = FontWeight.Bold,
        )
      )
      if (supportingLine.isNotEmpty()) {
        Spacer(GlanceModifier.height(2.dp))
        Text(
          text = supportingLine,
          style = TextStyle(
            color = ColorProvider(state.palette.onPrimaryColor),
            fontSize = 8.sp,
          )
        )
      }
    }
  }
}