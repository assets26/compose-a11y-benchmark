package org.michaelbel.movies.ui.compose.page

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.plus
import androidx.compose.foundation.lazy.staggeredgrid.LazyStaggeredGridState
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridItemSpan
import androidx.compose.foundation.lazy.staggeredgrid.rememberLazyStaggeredGridState
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.paging.compose.LazyPagingItems
import androidx.paging.compose.itemContentType
import androidx.paging.compose.itemKey
import org.michaelbel.movies.common.appearance.FeedView
import org.michaelbel.movies.persistence.database.entity.pojo.MoviePojo
import org.michaelbel.movies.ui.compose.MovieCard
import org.michaelbel.movies.ui.entity.MovieCardStyle
import org.michaelbel.movies.ui.isPagingFailure
import org.michaelbel.movies.ui.isPagingLoading
import org.michaelbel.movies.ui.isShortNavigationBarCompact
import org.michaelbel.movies.ui.pageStaggeredGridCells

@Composable
fun PageContent(
    feedView: FeedView,
    lazyStaggeredGridState: LazyStaggeredGridState = rememberLazyStaggeredGridState(),
    pagingItems: LazyPagingItems<MoviePojo>,
    onMovieClick: (String, Int) -> Unit,
    contentPadding: PaddingValues = PaddingValues(),
    modifier: Modifier = Modifier,
    cardColor: Color = MaterialTheme.colorScheme.inversePrimary
) {
    val cardStyle = when (feedView) {
        is FeedView.FeedList -> MovieCardStyle.Row
        is FeedView.FeedGrid -> MovieCardStyle.Column
    }
    val columns = when (feedView) {
        is FeedView.FeedList -> if (isShortNavigationBarCompact) StaggeredGridCells.Fixed(1) else pageStaggeredGridCells(cardStyle)
        is FeedView.FeedGrid -> pageStaggeredGridCells(cardStyle)
    }

    LazyVerticalStaggeredGrid(
        columns = columns,
        modifier = modifier,
        state = lazyStaggeredGridState,
        contentPadding = contentPadding + PaddingValues(8.dp),
        verticalItemSpacing = 8.dp,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(
            count = pagingItems.itemCount,
            key = pagingItems.itemKey(),
            contentType = pagingItems.itemContentType()
        ) { index ->
            val movieDb = pagingItems[index]
            if (movieDb != null) {
                MovieCard(
                    movie = movieDb,
                    style = cardStyle,
                    onClick = { onMovieClick(it.movieList, it.movieId) },
                    cardColor = cardColor
                )
            }
        }
        when {
            pagingItems.isPagingLoading -> {
                item(
                    span = StaggeredGridItemSpan.FullLine
                ) {
                    PagingLoadingBox()
                }
            }
            pagingItems.isPagingFailure -> {
                item(
                    span = StaggeredGridItemSpan.FullLine
                ) {
                    PagingFailureBox(onClick = pagingItems::retry)
                }
            }
        }
    }
}
