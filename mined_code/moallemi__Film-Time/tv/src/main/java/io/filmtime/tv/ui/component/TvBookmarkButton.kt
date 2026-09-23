package io.filmtime.tv.ui.component

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.layout.wrapContentSize
import androidx.compose.material.icons.Icons.Rounded
import androidx.compose.material.icons.rounded.Bookmark
import androidx.compose.material.icons.rounded.BookmarkBorder
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.tv.material3.Button
import androidx.tv.material3.Icon
import androidx.tv.material3.Text
import androidx.tv.material3.WideButtonDefaults
import io.filmtime.tv.R

@Composable
fun TvBookmarkButton(
  modifier: Modifier = Modifier,
  isBookmark: Boolean,
  onRemove: () -> Unit,
  onAdd: () -> Unit,
) {
  Button(
    shape = WideButtonDefaults.shape(),
    modifier = modifier,
    onClick = {
      if (isBookmark) {
        onRemove()
      } else {
        onAdd()
      }
    },
    content = {
      AnimatedContent(
        targetState = isBookmark,
        label = "",
      ) { isBookmarkState ->
        if (isBookmarkState) {
          Icon(
            imageVector = Rounded.Bookmark,
            contentDescription = stringResource(R.string.cd_bookmarked_icon),
          )
        } else {
          Icon(
            imageVector = Rounded.BookmarkBorder,
            contentDescription = stringResource(R.string.cd_bookmark_icon),
          )
        }
      }
      Text(
        text = if (isBookmark) {
          stringResource(R.string.bookmarked)
        } else {
          stringResource(R.string.bookmark)
        },
        modifier = Modifier
          .wrapContentSize()
          .animateContentSize(),
      )
    },
  )
}
