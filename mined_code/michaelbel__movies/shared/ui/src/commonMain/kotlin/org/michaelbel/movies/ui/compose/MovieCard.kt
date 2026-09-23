package org.michaelbel.movies.ui.compose

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.tooling.preview.PreviewParameter
import androidx.compose.ui.tooling.preview.PreviewWrapper
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import coil3.compose.LocalPlatformContext
import coil3.request.ImageRequest
import coil3.request.crossfade
import org.michaelbel.movies.network.config.formatMovieColumnPosterImage
import org.michaelbel.movies.network.config.formatMovieRowBackdropImage
import org.michaelbel.movies.persistence.database.entity.pojo.MoviePojo
import org.michaelbel.movies.persistence.database.ktx.isEmpty
import org.michaelbel.movies.persistence.database.ktx.isNotEmpty
import org.michaelbel.movies.ui.accessibility.MoviesContentDescription
import org.michaelbel.movies.ui.entity.MovieCardStyle
import org.michaelbel.movies.ui.placeholder.PlaceholderHighlight
import org.michaelbel.movies.ui.placeholder.material3.fade
import org.michaelbel.movies.ui.placeholder.placeholder
import org.michaelbel.movies.ui.preview.MoviePreviewParameterProvider
import org.michaelbel.movies.ui.preview.wrapper.ThemeWrapper

@Composable
fun MovieCard(
    movie: MoviePojo,
    style: MovieCardStyle,
    modifier: Modifier = Modifier,
    onClick: (MoviePojo) -> Unit = {},
    cardColor: Color = MaterialTheme.colorScheme.inversePrimary
) {
    val imageData = when (style) {
        MovieCardStyle.Row -> movie.backdropPath.formatMovieRowBackdropImage
        MovieCardStyle.Column -> movie.posterPath.formatMovieColumnPosterImage
    }
    val aspectRatio = when (style) {
        MovieCardStyle.Row -> 16F / 9F
        MovieCardStyle.Column -> 3F / 4F
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.large)
            .background(cardColor)
            .clickable(
                enabled = movie.isNotEmpty,
                onClick = { onClick(movie) }
            )
            .placeholder(
                visible = movie.isEmpty,
                color = cardColor,
                shape = MaterialTheme.shapes.large,
                highlight = PlaceholderHighlight.fade()
            )
    ) {
        AsyncImage(
            model = ImageRequest.Builder(LocalPlatformContext.current)
                .data(imageData)
                .crossfade(true)
                .build(),
            contentDescription = MoviesContentDescription.None,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(aspectRatio),
            contentScale = ContentScale.Crop
        )

        Text(
            text = movie.title,
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            maxLines = 10,
            overflow = TextOverflow.Ellipsis,
            style = MaterialTheme.typography.bodyLarge.copy(
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
        )
    }
}

@PreviewWrapper(ThemeWrapper::class)
@Preview
@Composable
private fun MovieCardRowPreview(
    @PreviewParameter(MoviePreviewParameterProvider::class) movie: MoviePojo
) {
    MovieCard(
        movie = movie,
        style = MovieCardStyle.Row
    )
}

@PreviewWrapper(ThemeWrapper::class)
@Preview
@Composable
private fun MovieCardColumnPreview(
    @PreviewParameter(MoviePreviewParameterProvider::class) movie: MoviePojo
) {
    MovieCard(
        movie = movie,
        style = MovieCardStyle.Column
    )
}
