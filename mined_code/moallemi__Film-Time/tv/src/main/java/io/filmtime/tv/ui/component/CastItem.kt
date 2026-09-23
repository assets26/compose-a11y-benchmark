package io.filmtime.tv.ui.component

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.tv.material3.Border
import androidx.tv.material3.ClickableSurfaceDefaults
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.StandardCardContainer
import androidx.tv.material3.Surface
import androidx.tv.material3.Text
import coil.compose.AsyncImage
import io.filmtime.data.model.Person
import io.filmtime.tv.R

@Composable
fun CastItem(
  modifier: Modifier = Modifier,
  item: Person,
  onClick: () -> Unit,
) {
  StandardCardContainer(
    modifier = modifier,
    imageCard = {
      Surface(
        onClick = onClick,
        shape = ClickableSurfaceDefaults.shape(CircleShape),
        border = ClickableSurfaceDefaults.border(
          focusedBorder = Border(
            BorderStroke(
              3.dp,
              MaterialTheme.colorScheme.onSurface,
            ),
            inset = 6.dp,
          ),
        ),
      ) {
        AsyncImage(
          modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .clip(CircleShape),
          contentScale = ContentScale.Crop,
          model = item.imageUrl,
          contentDescription = stringResource(R.string.cd_cast_profile),
        )
      }
    },
    title = {
      Column(
        verticalArrangement = Arrangement.spacedBy(
          4.dp,
          Alignment.CenterVertically,
        ),
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.padding(top = 20.dp),
      ) {
        Text(
          modifier = Modifier
            .fillMaxWidth(),
          text = item.name,
          style = MaterialTheme.typography.bodyMedium,
          textAlign = TextAlign.Center,
        )
        Text(
          modifier = Modifier
            .fillMaxWidth(),
          text = item.role,
          style = MaterialTheme.typography.bodyMedium.copy(
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
          ),
          textAlign = TextAlign.Center,
          maxLines = 1,
          overflow = TextOverflow.Ellipsis,
        )
      }
    },
  )
}
