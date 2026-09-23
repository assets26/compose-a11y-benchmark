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
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Box
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider

class PrayerTimesWidget : GlanceAppWidget() {

  override suspend fun provideGlance(
    context: Context,
    id: GlanceId
  ) {
    val state = loadPrayerWidgetState(context)

    provideContent {
      GlanceTheme {
        if (state.fajr == null) {
          WidgetPlaceholder(
            bgColor = state.palette.bgColor,
            primaryColor = state.palette.primaryColor,
            mutedColor = state.palette.textMutedColor,
            label = state.labels.placeholderLabel,
          )
        } else {
          WidgetContent(state = state)
        }
      }
    }
  }
}

@Composable
private fun WidgetPlaceholder(
  bgColor: androidx.compose.ui.graphics.Color,
  primaryColor: androidx.compose.ui.graphics.Color,
  mutedColor: androidx.compose.ui.graphics.Color,
  label: String,
) {
  Box(
    modifier = GlanceModifier
      .fillMaxSize()
      .background(bgColor)
      .padding(12.dp)
      .clickable(actionStartActivity<MainActivity>()),
    contentAlignment = Alignment.Center,
  ) {
    Column(
      horizontalAlignment = Alignment.CenterHorizontally,
    ) {
      Text(
        text = "eQuran",
        style = TextStyle(
          color = ColorProvider(primaryColor),
          fontSize = 14.sp,
          fontWeight = FontWeight.Bold
        )
      )
      Spacer(GlanceModifier.height(6.dp))
      Text(
        text = label,
        style = TextStyle(
          color = ColorProvider(mutedColor),
          fontSize = 10.sp,
        )
      )
    }
  }
}

@Composable
private fun WidgetContent(state: PrayerWidgetState) {
  val supportingLine = headerSupportingLine(
    loc = state.loc,
    updatedLabel = state.labels.updatedLabel,
    updated = state.updated,
  )
  val nextLabel = prayerLabelForId(state.next, state.labels)

  Box(
    modifier = GlanceModifier
      .fillMaxSize()
      .background(state.palette.bgColor)
      .padding(horizontal = 12.dp, vertical = 12.dp)
      .clickable(actionStartActivity<MainActivity>()),
    contentAlignment = Alignment.TopStart,
  ) {
    Column(
      modifier = GlanceModifier.fillMaxSize(),
    ) {
      Row(
        modifier = GlanceModifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
      ) {
        Column(
          modifier = GlanceModifier.defaultWeight()
        ) {
          Text(
            text = state.labels.headerLabel,
            style = TextStyle(
              color = ColorProvider(state.palette.textColor),
              fontSize = 16.sp,
              fontWeight = FontWeight.Bold
            )
          )
          if (supportingLine.isNotEmpty()) {
            Text(
              text = supportingLine,
              style = TextStyle(
                color = ColorProvider(state.palette.textSecondaryColor),
                fontSize = 11.sp
              )
            )
          }
        }
        if (nextLabel.isNotEmpty()) {
          Box(
            modifier = GlanceModifier
              .background(state.palette.primaryColor)
              .cornerRadius(6.dp)
              .padding(horizontal = 8.dp, vertical = 4.dp),
            contentAlignment = Alignment.Center,
          ) {
            Text(
              text = nextLabel,
              style = TextStyle(
                color = ColorProvider(state.palette.onPrimaryColor),
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold
              )
            )
          }
        }
      }

      Spacer(GlanceModifier.height(10.dp))

      Row(
        modifier = GlanceModifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
      ) {
        PrayerCell(
          name = state.labels.fajrLabel,
          time = state.fajr ?: "---",
          isNext = state.next == "fajr",
          palette = state.palette,
          modifier = GlanceModifier.defaultWeight()
        )
        Spacer(GlanceModifier.width(4.dp))
        PrayerCell(
          name = state.labels.sunriseLabel,
          time = state.sunrise,
          isNext = state.next == "sunrise",
          palette = state.palette,
          modifier = GlanceModifier.defaultWeight()
        )
        Spacer(GlanceModifier.width(4.dp))
        PrayerCell(
          name = state.labels.dhuhrLabel,
          time = state.dhuhr,
          isNext = state.next == "dhuhr",
          palette = state.palette,
          modifier = GlanceModifier.defaultWeight()
        )
      }

      Spacer(GlanceModifier.height(6.dp))

      Row(
        modifier = GlanceModifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
      ) {
        PrayerCell(
          name = state.labels.asrLabel,
          time = state.asr,
          isNext = state.next == "asr",
          palette = state.palette,
          modifier = GlanceModifier.defaultWeight()
        )
        Spacer(GlanceModifier.width(4.dp))
        PrayerCell(
          name = state.labels.maghribLabel,
          time = state.maghrib,
          isNext = state.next == "maghrib",
          palette = state.palette,
          modifier = GlanceModifier.defaultWeight()
        )
        Spacer(GlanceModifier.width(4.dp))
        PrayerCell(
          name = state.labels.ishaLabel,
          time = state.isha,
          isNext = state.next == "isha",
          palette = state.palette,
          modifier = GlanceModifier.defaultWeight()
        )
      }
    }
  }
}

@Composable
private fun PrayerCell(
  name: String,
  time: String,
  isNext: Boolean,
  palette: PrayerWidgetPalette,
  modifier: GlanceModifier = GlanceModifier,
) {
  val finalBg = if (isNext) palette.primaryStrongColor else palette.surfaceColor
  val nameColor = if (isNext) palette.goldColor else palette.textSecondaryColor
  val timeColor = if (isNext) palette.onPrimaryColor else palette.textColor

  Box(
    modifier = modifier
      .height(42.dp)
      .cornerRadius(8.dp)
      .background(finalBg)
      .padding(horizontal = 4.dp, vertical = 5.dp),
    contentAlignment = Alignment.Center,
  ) {
    Column(
      horizontalAlignment = Alignment.CenterHorizontally,
      verticalAlignment = Alignment.CenterVertically,
    ) {
      Text(
        text = name,
        style = TextStyle(
          color = ColorProvider(nameColor),
          fontSize = 9.sp,
          fontWeight = if (isNext)
            FontWeight.Bold
          else
            FontWeight.Normal
        )
      )
      Spacer(GlanceModifier.height(2.dp))
      Text(
        text = time,
        style = TextStyle(
          color = ColorProvider(timeColor),
          fontSize = 12.sp,
          fontWeight = FontWeight.Bold
        )
      )
    }
  }
}
