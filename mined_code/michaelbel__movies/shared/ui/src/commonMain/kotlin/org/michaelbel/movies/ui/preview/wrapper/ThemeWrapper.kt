package org.michaelbel.movies.ui.preview.wrapper

import androidx.compose.runtime.Composable
import androidx.compose.ui.tooling.preview.PreviewWrapperProvider
import org.michaelbel.movies.ui.theme.AppTheme

class ThemeWrapper: PreviewWrapperProvider {

    @Composable
    override fun Wrap(content: @Composable () -> Unit) {
        AppTheme(
            content = content
        )
    }
}
