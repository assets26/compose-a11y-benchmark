package io.filmtime.tv.ui.component

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.tv.material3.Button
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Text
import io.filmtime.core.ui.common.UiMessage

@Composable
fun ErrorScreen(
  modifier: Modifier = Modifier,
  message: UiMessage,
  actionTitle: String,
  onActionClick: () -> Unit,
) {
  Column(
    modifier = modifier,
    horizontalAlignment = Alignment.CenterHorizontally,
    verticalArrangement = Arrangement.Center,
  ) {
    Text(
      text = message.string(),
      color = MaterialTheme.colorScheme.error,
    )
    Spacer(modifier = Modifier.height(12.dp))
    Button(onClick = onActionClick) {
      Text(text = actionTitle)
    }
  }
}
