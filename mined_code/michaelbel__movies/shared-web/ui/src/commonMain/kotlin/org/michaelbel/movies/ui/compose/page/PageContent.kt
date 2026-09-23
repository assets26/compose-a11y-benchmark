package org.michaelbel.movies.ui.compose.page

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.staggeredgrid.LazyStaggeredGridState
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.foundation.lazy.staggeredgrid.items
import androidx.compose.foundation.lazy.staggeredgrid.rememberLazyStaggeredGridState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.michaelbel.movies.common.appearance.FeedView
import org.michaelbel.movies.network.config.formatBackdropImage
import org.michaelbel.movies.network.config.formatPosterImage
import org.michaelbel.movies.persistence.database.entity.pojo.MoviePojo
import org.michaelbel.movies.persistence.database.typealiases.MovieId
import org.michaelbel.movies.persistence.database.typealiases.PagingKey
import org.michaelbel.movies.ui.compose.MovieCard
import org.michaelbel.movies.ui.compose.plus

@Composable
fun PageContent(
    movies: List<MoviePojo>,
    feedView: FeedView,
    onMovieClick: (PagingKey, MovieId) -> Unit,
    lazyStaggeredGridState: LazyStaggeredGridState = rememberLazyStaggeredGridState(),
    contentPadding: PaddingValues = PaddingValues(),
    modifier: Modifier = Modifier
) {
    LazyVerticalStaggeredGrid(
        columns = StaggeredGridCells.Adaptive(minSize = 280.dp),
        modifier = modifier,
        state = lazyStaggeredGridState,
        contentPadding = contentPadding + PaddingValues(8.dp),
        verticalItemSpacing = 8.dp,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(
            items = movies,
            key = { it.movieId }
        ) { movie ->
            val imageUrl = when (feedView) {
                is FeedView.FeedList -> movie.backdropPath.formatBackdropImage
                is FeedView.FeedGrid -> movie.posterPath.formatPosterImage
            }
            MovieCard(
                imageUrl = imageUrl,
                title = movie.title,
                feedView = feedView,
                onClick = { onMovieClick(movie.movieList, movie.movieId) }
            )
        }
    }
}
