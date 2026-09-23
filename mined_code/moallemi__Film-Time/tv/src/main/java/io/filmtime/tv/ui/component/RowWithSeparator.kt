package io.filmtime.tv.ui.component

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.ProvideTextStyle
import androidx.tv.material3.Text
import io.filmtime.tv.R

@Composable
fun TextsRowWithSeparator(
  modifier: Modifier = Modifier,
  color: Color = MaterialTheme.colorScheme.onSurfaceVariant,
  space: Dp = 4.dp,
  textStyle: TextStyle = MaterialTheme.typography.bodyMedium,
  texts: List<String>,
  separator: @Composable () -> Unit = { Text(text = stringResource(R.string.bullet_point)) },
) {
  Row(
    modifier = modifier,
    horizontalArrangement = Arrangement.spacedBy(space),
    verticalAlignment = Alignment.CenterVertically,
  ) {
    ProvideTextStyle(textStyle.copy(color = color)) {
      texts.forEachIndexed { index, text ->
        Text(text = text)
        if (index != texts.lastIndex) {
          separator()
        }
      }
    }
  }
}
