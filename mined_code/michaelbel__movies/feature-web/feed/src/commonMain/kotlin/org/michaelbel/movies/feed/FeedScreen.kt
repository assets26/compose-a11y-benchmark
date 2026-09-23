package org.michaelbel.movies.feed

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import org.koin.compose.koinInject
import org.michaelbel.movies.common.appearance.FeedView
import org.michaelbel.movies.common.list.MovieList
import org.michaelbel.movies.feed.ktx.toUserMessage
import org.michaelbel.movies.feed.model.FeedState
import org.michaelbel.movies.interactor.Interactor
import org.michaelbel.movies.persistence.database.typealiases.MovieId
import org.michaelbel.movies.persistence.database.typealiases.PagingKey
import org.michaelbel.movies.ui.compose.page.PageContent
import org.michaelbel.movies.ui.compose.page.PageFailure
import org.michaelbel.movies.ui.compose.page.PageLoading

@Composable
fun FeedScreen(
    onMovieClick: (PagingKey, MovieId) -> Unit = { _, _ -> },
    interactor: Interactor = koinInject()
) {
    val feedView by interactor.currentFeedView.collectAsState(initial = FeedView.FeedList)

    var reloadToken by remember { mutableIntStateOf(0) }
    val state by produceState<FeedState>(
        initialValue = FeedState.Loading,
        key1 = interactor,
        key2 = reloadToken
    ) {
        value = try {
            FeedState.Ready(
                movies = interactor.moviesResult(MovieList.name(MovieList.NowPlaying()))
            )
        } catch (exception: Exception) {
            FeedState.Error(exception.toUserMessage())
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.primaryContainer
    ) {
        when (val currentState = state) {
            FeedState.Loading -> {
                PageLoading(
                    modifier = Modifier.fillMaxSize()
                )
            }
            is FeedState.Ready -> {
                PageContent(
                    movies = currentState.movies,
                    feedView = feedView,
                    onMovieClick = onMovieClick,
                    modifier = Modifier.fillMaxSize()
                )
            }
            is FeedState.Error -> {
                PageFailure(
                    message = currentState.message,
                    modifier = Modifier.fillMaxSize()
                )
            }
        }
    }
}
