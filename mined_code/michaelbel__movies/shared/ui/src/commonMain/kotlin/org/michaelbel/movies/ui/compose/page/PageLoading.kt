package org.michaelbel.movies.ui.compose.page

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.plus
import androidx.compose.foundation.lazy.staggeredgrid.LazyVerticalStaggeredGrid
import androidx.compose.foundation.lazy.staggeredgrid.StaggeredGridCells
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import org.michaelbel.movies.common.appearance.FeedView
import org.michaelbel.movies.network.model.MovieResponse
import org.michaelbel.movies.persistence.database.entity.pojo.MoviePojo
import org.michaelbel.movies.ui.compose.MovieCard
import org.michaelbel.movies.ui.entity.MovieCardStyle
import org.michaelbel.movies.ui.isShortNavigationBarCompact
import org.michaelbel.movies.ui.pageStaggeredGridCells

@Composable
fun PageLoading(
    feedView: FeedView,
    modifier: Modifier = Modifier,
    contentPadding: PaddingValues = PaddingValues(),
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
        contentPadding = contentPadding + PaddingValues(8.dp),
        verticalItemSpacing = 8.dp,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        userScrollEnabled = false
    ) {
        items(
            count = MovieResponse.DEFAULT_PAGE_SIZE.div(2)
        ) {
            MovieCard(
                movie = MoviePojo.Empty,
                style = cardStyle,
                cardColor = cardColor
            )
        }
    }
}
