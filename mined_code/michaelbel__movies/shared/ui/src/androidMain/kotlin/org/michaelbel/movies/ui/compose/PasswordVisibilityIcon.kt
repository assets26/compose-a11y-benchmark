package org.michaelbel.movies.ui.compose

import android.content.res.ColorStateList
import android.widget.ImageView
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.viewinterop.AndroidView
import org.michaelbel.movies.ui.R

@Composable
actual fun PasswordVisibilityIcon(
    passwordVisible: Boolean,
    contentDescription: String,
    modifier: Modifier,
    tint: Color
) {
    AndroidView(
        factory = { context ->
            ImageView(context).apply {
                setImageResource(R.drawable.asl_password_eye)
                scaleType = ImageView.ScaleType.FIT_CENTER
                tag = passwordVisible
                setImageState(passwordVisibilityState(passwordVisible), false)
            }
        },
        update = { view ->
            view.imageTintList = ColorStateList.valueOf(tint.toArgb())
            view.contentDescription = contentDescription
            if (view.tag != passwordVisible) {
                view.tag = passwordVisible
                view.setImageState(passwordVisibilityState(passwordVisible), true)
            }
        },
        modifier = modifier
    )
}

private fun passwordVisibilityState(passwordVisible: Boolean): IntArray {
    return intArrayOf(android.R.attr.state_checked * if (passwordVisible) 1 else -1)
}
