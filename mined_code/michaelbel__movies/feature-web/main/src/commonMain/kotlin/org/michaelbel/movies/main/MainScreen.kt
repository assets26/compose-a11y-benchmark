@file:OptIn(ExperimentalMaterial3ExpressiveApi::class)

package org.michaelbel.movies.main

import androidx.compose.material3.ExperimentalMaterial3ExpressiveApi
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.ui.unit.Dp
import org.koin.compose.KoinApplication
import org.koin.compose.koinInject
import org.koin.dsl.koinConfiguration
import org.michaelbel.movies.common.ThemeData
import org.michaelbel.movies.detailsweb.DetailsWebScreen
import org.michaelbel.movies.interactor.Interactor
import org.michaelbel.movies.interactor.di.interactorKoinModule
import org.michaelbel.movies.main.tabs.MainWebTabsScreen
import org.michaelbel.movies.persistence.database.typealiases.MovieId
import org.michaelbel.movies.persistence.database.typealiases.PagingKey
import org.michaelbel.movies.ui.theme.AppTheme

@Composable
fun MainScreen() {
    KoinApplication(
        configuration = koinConfiguration {
            modules(interactorKoinModule)
        }
    ) {
        MainScreenContent()
    }
}

@Composable
private fun MainScreenContent() {
    val interactor: Interactor = koinInject()
    val themeData by interactor.themeData.collectAsState(initial = ThemeData.Default)

    var destination by remember { mutableStateOf<MainWebDestination>(MainWebDestination.Feed) }

    AppTheme(
        themeData = themeData
    ) {
        when (val currentDestination = destination) {
            MainWebDestination.Feed,
            MainWebDestination.Settings -> {
                MainWebTabsScreen(
                    currentDestination = currentDestination,
                    onDestinationChange = { destination = it },
                    onMovieClick = { pagingKey, movieId ->
                        destination = MainWebDestination.Details(
                            pagingKey = pagingKey,
                            movieId = movieId
                        )
                    }
                )
            }
            is MainWebDestination.Details -> {
                DetailsWebScreen(
                    pagingKey = currentDestination.pagingKey,
                    movieId = currentDestination.movieId,
                    onBackClick = { destination = MainWebDestination.Feed }
                )
            }
        }
    }
}



sealed interface MainWebDestination {
    data object Feed: MainWebDestination
    data object Settings: MainWebDestination
    data class Details(
        val pagingKey: PagingKey,
        val movieId: MovieId
    ): MainWebDestination
}

val mainWebWindowWidth: Dp
    @Composable get() = with(LocalDensity.current) { LocalWindowInfo.current.containerSize.width.toDp() }
