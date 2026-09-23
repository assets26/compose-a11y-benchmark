package org.michaelbel.movies.ui.compose

import androidx.activity.compose.BackHandler as AndroidBackHandler
import androidx.compose.runtime.Composable

@Composable
actual fun PlatformBackHandler(
    enabled: Boolean,
    onBack: () -> Unit
) {
    AndroidBackHandler(
        enabled = enabled,
        onBack = onBack
    )
}
