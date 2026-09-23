package org.michaelbel.movies.ui.compose

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color

@Composable
expect fun PasswordVisibilityIcon(
    passwordVisible: Boolean,
    contentDescription: String,
    modifier: Modifier = Modifier,
    tint: Color
)
