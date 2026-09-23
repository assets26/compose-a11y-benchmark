package io.filmtime.tv.ui.component

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.tv.material3.MaterialTheme
import coil.compose.AsyncImage
import coil.request.ImageRequest

@Composable
fun DetailPoster(
  coverUrl: String,
  modifier: Modifier = Modifier,
  scrimColor: Color = MaterialTheme.colorScheme.surface,
) {
  AsyncImage(
    model = ImageRequest.Builder(LocalContext.current)
      .data(coverUrl).crossfade(true).build(),
    contentDescription = "Poster Image",
    contentScale = ContentScale.Crop,
    modifier = modifier.drawWithContent {
      drawContent()
      drawRect(
        Brush.verticalGradient(
          colors = listOf(Color.Transparent, scrimColor),
          startY = 600f,
        ),
      )
      drawRect(
        Brush.horizontalGradient(
          colors = listOf(scrimColor, Color.Transparent),
          endX = 1000f,
          startX = 300f,
        ),
      )
      drawRect(
        Brush.linearGradient(
          colors = listOf(scrimColor, Color.Transparent),
          start = Offset(x = 500f, y = 500f),
          end = Offset(x = 1000f, y = 0f),
        ),
      )
    },
  )
}
