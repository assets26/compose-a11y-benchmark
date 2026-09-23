package io.filmtime.tv.ui.component

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.tv.material3.MaterialTheme
import androidx.tv.material3.Text
import io.filmtime.data.model.Ratings
import io.filmtime.data.model.VideoDetail
import io.filmtime.tv.R

@Composable
fun MovieInformation(
  modifier: Modifier = Modifier,
  ratings: Ratings?,
  videoDetail: VideoDetail,
) {
  val genreNames = remember(videoDetail.genres) {
    videoDetail.genres.map { it.name }
  }
  Column(
    modifier = modifier,
  ) {
    Text(
      text = stringResource(R.string.information),
      style = MaterialTheme.typography.titleLarge,
      modifier = Modifier.padding(
        start = 50.dp,
        bottom = 20.dp,
      ),
    )
    Row(
      modifier = Modifier.fillMaxWidth(),
      horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
      Column {
        InfoItem(
          title = stringResource(R.string.genres),
          content = {
            TextsRowWithSeparator(
              texts = genreNames,
              textStyle = MaterialTheme.typography.bodyMedium,
            )
          },
        )
        Spacer(modifier = Modifier.height(10.dp))
        ratings?.let {
          InfoItem(
            title = stringResource(R.string.imdb),
            value = it.imdb?.rating ?: stringResource(R.string.not_applicable),
          )
        }
      }
      Column {
        InfoItem(
          title = stringResource(R.string.release_date),
          value = videoDetail.releaseDate,
        )
        Spacer(modifier = Modifier.height(10.dp))
        ratings?.let {
          InfoItem(
            title = stringResource(R.string.rotten_tomatoes),
            value = it.rottenTomatoes?.rating ?: stringResource(id = R.string.not_applicable),
          )
        }
      }
      Column {
        InfoItem(
          title = stringResource(R.string.spoken_languages),
          content = {
            TextsRowWithSeparator(
              texts = videoDetail.spokenLanguages,
              textStyle = MaterialTheme.typography.bodyMedium,
            )
          },
        )
        Spacer(modifier = Modifier.height(10.dp))
        ratings?.let {
          InfoItem(
            title = stringResource(R.string.trakt),
            value = it.trakt?.rating ?: stringResource(id = R.string.not_applicable),
          )
        }
      }
      Column {
        InfoItem(
          title = stringResource(R.string.status),
          value = videoDetail.status ?: stringResource(id = R.string.not_applicable),
        )
        Spacer(modifier = Modifier.height(10.dp))
        ratings?.let {
          InfoItem(
            title = stringResource(id = R.string.tmdb),
            value =
            it.tmdb?.rating ?: stringResource(id = R.string.not_applicable),
          )
        }
      }
    }
  }
}

@Composable
private fun InfoItem(
  title: String,
  content: @Composable () -> Unit,
) {
  Column {
    Text(
      text = title,
      style = MaterialTheme.typography.titleMedium,
    )
    Spacer(modifier = Modifier.height(10.dp))
    content()
  }
}

@Composable
private fun InfoItem(
  title: String,
  value: String,
) {
  Column {
    Text(
      text = title,
      style = MaterialTheme.typography.titleMedium,
    )
    Spacer(modifier = Modifier.height(10.dp))
    Text(
      text = value,
      style = MaterialTheme.typography.bodyMedium,
    )
  }
}
