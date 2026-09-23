package com.nevoit.cresto.ui.components.glasense

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.LinearOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.Orientation
import androidx.compose.foundation.gestures.draggable
import androidx.compose.foundation.gestures.rememberDraggableState
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.Stable
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.painter.Painter
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalWindowInfo
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.nevoit.cresto.theme.AppButtonColors
import com.nevoit.glasense.core.component.Icon
import com.nevoit.glasense.theme.tokens.Springs
import kotlinx.collections.immutable.ImmutableList
import kotlinx.collections.immutable.persistentListOf
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.random.Random
import kotlin.time.Duration.Companion.milliseconds

enum class SwipeState {
    /**
     * The initial state where the to-do item is not swiped.
     */
    IDLE,

    /**
     * The state where the to-do item is swiped to reveal the delete button.
     */
    REVEALED
}

private enum class SwipeDirection(val sign: Float) {
    LEFT(-1f),
    RIGHT(1f)
}

@Stable
class SwipeableListState {
    var currentOpenKey: Any? by mutableStateOf(null)
        private set

    fun setOpen(key: Any) {
        currentOpenKey = key
    }

    fun close() {
        currentOpenKey = null
    }
}

@Composable
fun rememberSwipeableListState(): SwipeableListState {
    return remember { SwipeableListState() }
}

/**
 * @param rightActions rightActions revealed by swiping the content to the left.
 * @param leftActions rightActions revealed by swiping the content to the right.
 */
@Composable
fun GlasenseSwipeable(
    modifier: Modifier = Modifier,
    key: Any,
    listState: SwipeableListState,
    rightActions: ImmutableList<SwipeableActionButton> = persistentListOf(),
    onAction: (Int) -> Unit,
    leftActions: ImmutableList<SwipeableActionButton> = persistentListOf(),
    content: @Composable () -> Unit
) {
    val haptic = LocalHapticFeedback.current

    var swipeState by remember(key) { mutableStateOf(SwipeState.IDLE) }
    var initialSwipeState by remember(key) { mutableStateOf(SwipeState.IDLE) }
    var revealedDirection by remember(key) { mutableStateOf<SwipeDirection?>(null) }
    var initialRevealedDirection by remember(key) { mutableStateOf<SwipeDirection?>(null) }
    val coroutineScope = rememberCoroutineScope()

    val density = LocalDensity.current

    val actionButtonWidthPx = with(density) { SwipeActionButtonWidth.toPx() }
    val gapPx = with(density) { SwipeActionsGap.toPx() }

    val leftActionsWidth = rightActions.actionsWidth()
    val rightActionsWidth = leftActions.actionsWidth()
    val leftActionsWidthPx = with(density) { leftActionsWidth.toPx() }
    val rightActionsWidthPx = with(density) { rightActionsWidth.toPx() }

    val velocityThreshold = with(density) { 500.dp.toPx() }

    val screenWidthPx = LocalWindowInfo.current.containerSize.width

    val flingOffset = remember(key) { Animatable(0f) }
    val deleteFlingOffset = remember(key) { Animatable(0f) }
    val leftDeepSwipeAction = remember(rightActions) { rightActions.deepSwipeAction("left") }
    val rightDeepSwipeAction = remember(leftActions) {
        leftActions.deepSwipeAction("right")
    }

    fun actionsWidthPx(direction: SwipeDirection): Float = when (direction) {
        SwipeDirection.LEFT -> leftActionsWidthPx
        SwipeDirection.RIGHT -> rightActionsWidthPx
    }

    fun deepSwipeAction(direction: SwipeDirection): SwipeableActionButton? = when (direction) {
        SwipeDirection.LEFT -> leftDeepSwipeAction
        SwipeDirection.RIGHT -> rightDeepSwipeAction
    }

    val shouldIntercept = listState.currentOpenKey != null && listState.currentOpenKey == key
    var shouldComposeActions by remember(key) { mutableStateOf(false) }

    val leftRevealedThresholds = remember(rightActions, actionButtonWidthPx, gapPx) {
        rightActions.indices.map { index ->
            val trueIndex = rightActions.size - index - 1
            gapPx + actionButtonWidthPx * trueIndex + actionButtonWidthPx / 2
        }
    }
    val rightRevealedThresholds = remember(leftActions, actionButtonWidthPx, gapPx) {
        leftActions.indices.map { index ->
            gapPx + actionButtonWidthPx * index + actionButtonWidthPx / 2
        }
    }
    val leftRevealedCount by remember(key, leftRevealedThresholds) {
        derivedStateOf {
            leftRevealedThresholds.count { -flingOffset.value >= it }
        }
    }
    val rightRevealedCount by remember(key, rightRevealedThresholds) {
        derivedStateOf {
            rightRevealedThresholds.count { flingOffset.value >= it }
        }
    }

    var isFlyingOut by remember(key) { mutableStateOf(false) }

    suspend fun resetVisualState() {
        isFlyingOut = false
        deleteFlingOffset.snapTo(0f)
    }

    fun executeAction(action: SwipeableActionButton, direction: SwipeDirection) {
        if (action.isDestructive) {
            coroutineScope.launch {
                repeat(5) {
                    haptic.performHapticFeedback(HapticFeedbackType.SegmentFrequentTick)
                    delay(Random.nextLong(50, 70).milliseconds)
                }
            }
            coroutineScope.launch {
                val flyOutExtraPx = actionsWidthPx(direction) + with(density) { 8.dp.toPx() }
                isFlyingOut = true
                deleteFlingOffset.animateTo(
                    targetValue =
                        direction.sign * (screenWidthPx + flyOutExtraPx) - flingOffset.value,
                    animationSpec = tween(
                        100,
                        easing = CubicBezierEasing(
                            0.2f,
                            0f,
                            0.56f,
                            0.48f
                        )
                    )
                )
                swipeState = SwipeState.IDLE
                revealedDirection = null
                listState.close()
                onAction(action.index)
            }
        } else {
            onAction(action.index)
            coroutineScope.launch {
                haptic.performHapticFeedback(HapticFeedbackType.Confirm)
            }
            coroutineScope.launch {
                swipeState = SwipeState.IDLE
                revealedDirection = null
                flingOffset.animateTo(0f)
                shouldComposeActions = false
                listState.close()
                resetVisualState()
            }
        }
    }

    LaunchedEffect(listState.currentOpenKey) {
        if (listState.currentOpenKey != key) {
            coroutineScope.launch {
                swipeState = SwipeState.IDLE
                revealedDirection = null
                flingOffset.animateTo(0f)
                shouldComposeActions = false
                resetVisualState()
            }
        }
    }

    val interactionSource = remember { MutableInteractionSource() }

    Box(
        modifier = modifier
            .fillMaxWidth()
    ) {
        if (shouldComposeActions) {
            if (leftActions.isNotEmpty()) {
                SwipeableActionsRow(
                    modifier = Modifier.align(Alignment.CenterStart),
                    actions = leftActions,
                    totalActionsWidth = rightActionsWidth,
                    direction = SwipeDirection.RIGHT,
                    revealedCount = rightRevealedCount,
                    isFlyingOut = isFlyingOut,
                    interactionSource = interactionSource,
                    onAction = { action -> executeAction(action, SwipeDirection.RIGHT) }
                )
            }
            if (rightActions.isNotEmpty()) {
                SwipeableActionsRow(
                    modifier = Modifier.align(Alignment.CenterEnd),
                    actions = rightActions,
                    totalActionsWidth = leftActionsWidth,
                    direction = SwipeDirection.LEFT,
                    revealedCount = leftRevealedCount,
                    isFlyingOut = isFlyingOut,
                    interactionSource = interactionSource,
                    onAction = { action -> executeAction(action, SwipeDirection.LEFT) }
                )
            }
        }

        val deepSwipeDirection by remember(
            key,
            leftActionsWidthPx,
            rightActionsWidthPx,
            actionButtonWidthPx
        ) {
            derivedStateOf {
                when {
                    flingOffset.value < -(leftActionsWidthPx + actionButtonWidthPx) -> {
                        SwipeDirection.LEFT
                    }

                    flingOffset.value > rightActionsWidthPx + actionButtonWidthPx -> {
                        SwipeDirection.RIGHT
                    }

                    else -> null
                }
            }
        }

        LaunchedEffect(deepSwipeDirection) {
            val direction = deepSwipeDirection
            if (
                direction != null &&
                initialSwipeState == SwipeState.REVEALED &&
                initialRevealedDirection == direction &&
                deepSwipeAction(direction) != null
            ) {
                haptic.performHapticFeedback(HapticFeedbackType.GestureThresholdActivate)
            }
        }
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .graphicsLayer {
                    translationX = flingOffset.value + deleteFlingOffset.value
                }
                .draggable(
                    enabled = rightActions.isNotEmpty() || leftActions.isNotEmpty(),
                    orientation = Orientation.Horizontal,
                    state = rememberDraggableState { delta ->
                        coroutineScope.launch {
                            val newOffset = rubberBandSwipeOffset(
                                currentOffset = flingOffset.value,
                                delta = delta,
                                leftRevealOffsetPx = leftActionsWidthPx,
                                rightRevealOffsetPx = rightActionsWidthPx,
                                viewportWidthPx = screenWidthPx.toFloat()
                            )
                            flingOffset.snapTo(newOffset)
                            val direction = newOffset.swipeDirection()
                            swipeState = if (
                                direction != null &&
                                abs(newOffset) > actionsWidthPx(direction) / 2
                            ) {
                                SwipeState.REVEALED
                            } else {
                                SwipeState.IDLE
                            }
                        }
                    },
                    onDragStarted = {
                        initialSwipeState = swipeState
                        initialRevealedDirection = revealedDirection
                        coroutineScope.launch { resetVisualState() }
                        shouldComposeActions = true
                        listState.setOpen(key)
                    },
                    onDragStopped = { velocity ->
                        coroutineScope.launch {
                            val currentOffset = flingOffset.value
                            val direction = currentOffset.swipeDirection()
                            val directionSign = direction?.sign ?: 0f
                            val directedVelocity = velocity * directionSign
                            val isFastSwipe = directedVelocity > velocityThreshold
                            val startedRevealed =
                                initialSwipeState == SwipeState.REVEALED &&
                                        initialRevealedDirection == direction
                            val deepSwipeAction = direction?.let(::deepSwipeAction)
                            val canDeepSwipe = deepSwipeAction != null && startedRevealed
                            val isDeepSwipe = deepSwipeDirection == direction
                            val isMovingTowardReveal = directedVelocity >= 0f
                            val revealWidthPx = direction?.let(::actionsWidthPx) ?: 0f

                            val shouldExecuteDeepSwipe =
                                canDeepSwipe &&
                                        isMovingTowardReveal &&
                                        (isDeepSwipe || isFastSwipe)

                            val shouldReveal =
                                direction != null &&
                                        (
                                                (canDeepSwipe && isDeepSwipe && !isMovingTowardReveal) ||
                                                        (
                                                                (abs(currentOffset) > revealWidthPx / 2 || isFastSwipe) &&
                                                                        isMovingTowardReveal
                                                                )
                                                )

                            when {
                                shouldExecuteDeepSwipe -> {
                                    executeAction(deepSwipeAction, direction)
                                }

                                shouldReveal -> {
                                    swipeState = SwipeState.REVEALED
                                    revealedDirection = direction
                                    flingOffset.animateTo(
                                        targetValue = directionSign * revealWidthPx,
                                        animationSpec = Springs.bouncy(400),
                                        initialVelocity = velocity
                                    )
                                }

                                else -> {
                                    if (listState.currentOpenKey == key) {
                                        listState.close()
                                    }
                                    swipeState = SwipeState.IDLE
                                    revealedDirection = null
                                    val finalVelocity =
                                        if (currentOffset == 0f) 0f else velocity
                                    flingOffset.animateTo(
                                        targetValue = 0f,
                                        animationSpec = Springs.bouncy(400),
                                        initialVelocity = finalVelocity
                                    )
                                    shouldComposeActions = false
                                    resetVisualState()
                                }
                            }
                        }
                    }
                )
        ) {
            content()

            if (shouldIntercept) {
                Box(
                    modifier = Modifier
                        .matchParentSize()
                        .clickable(
                            interactionSource = interactionSource,
                            indication = null,
                            onClick = {
                                listState.close()
                            }
                        )
                )
            }
        }
    }
}

@Composable
private fun SwipeableActionsRow(
    modifier: Modifier,
    actions: ImmutableList<SwipeableActionButton>,
    totalActionsWidth: Dp,
    direction: SwipeDirection,
    revealedCount: Int,
    isFlyingOut: Boolean,
    interactionSource: MutableInteractionSource,
    onAction: (SwipeableActionButton) -> Unit
) {
    Row(
        modifier = modifier
            .width(totalActionsWidth)
            .clickable(
                interactionSource = interactionSource,
                indication = null,
                onClick = {}
            )
            .then(
                if (direction == SwipeDirection.LEFT) {
                    Modifier.padding(end = SwipeActionsGap)
                } else {
                    Modifier.padding(start = SwipeActionsGap)
                }
            ),
        horizontalArrangement = if (direction == SwipeDirection.LEFT) {
            Arrangement.End
        } else {
            Arrangement.Start
        },
        verticalAlignment = Alignment.CenterVertically
    ) {
        actions.forEachIndexed { index, action ->
            Box(
                modifier = Modifier
                    .width(SwipeActionButtonWidth)
                    .fillMaxHeight(),
                contentAlignment = Alignment.Center,
            ) {
                val revealIndex = if (direction == SwipeDirection.LEFT) {
                    actions.size - index - 1
                } else {
                    index
                }
                val isVisible = revealIndex < revealedCount && !isFlyingOut

                val animation = remember(action.index) { Animatable(0.6f) }
                val alphaAnimation = remember(action.index) { Animatable(0f) }
                LaunchedEffect(isVisible) {
                    if (isVisible) {
                        launch {
                            alphaAnimation.animateTo(
                                1f,
                                tween(300, easing = LinearOutSlowInEasing)
                            )
                        }
                        animation.animateTo(1f, tween(300, easing = LinearOutSlowInEasing))
                    } else {
                        launch {
                            alphaAnimation.animateTo(
                                0f,
                                tween(100, easing = LinearOutSlowInEasing)
                            )
                        }
                        animation.animateTo(
                            0.6f,
                            tween(200, easing = LinearOutSlowInEasing)
                        )
                    }
                }
                GlasenseButton(
                    enabled = true,
                    shape = CircleShape,
                    onClick = { onAction(action) },
                    modifier = Modifier
                        .graphicsLayer {
                            scaleX = animation.value
                            scaleY = animation.value
                            alpha = alphaAnimation.value
                        }
                        .size(48.dp),
                    colors = AppButtonColors.solid(
                        color = action.color,
                        contentColor = Color.White
                    ),
                    animated = true
                ) {
                    Box(
                        modifier = Modifier
                            .glasenseHighlight(100.dp)
                            .fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            painter = action.icon,
                            contentDescription = action.contentDescription,
                            tint = action.iconColor,
                            modifier = Modifier
                                .width(28.dp)
                                .height(28.dp)
                        )
                    }
                }
            }
        }
    }
}

@Immutable
data class SwipeableActionButton(
    val index: Int,
    val color: Color,
    val icon: Painter,
    val iconColor: Color = Color.White,
    val contentDescription: String? = null,
    val isDestructive: Boolean = false,
    val triggerOnDeepSwipe: Boolean = false
)

private const val SwipeRubberBandConstant = 0.55f
private val SwipeActionButtonWidth = 60.dp
private val SwipeActionsGap = 6.dp

private fun ImmutableList<SwipeableActionButton>.actionsWidth(): Dp {
    return if (isEmpty()) 0.dp else SwipeActionButtonWidth * size + SwipeActionsGap * 2
}

private fun ImmutableList<SwipeableActionButton>.deepSwipeAction(
    directionName: String
): SwipeableActionButton? {
    var selectedAction: SwipeableActionButton? = null
    forEach { action ->
        if (action.triggerOnDeepSwipe) {
            require(selectedAction == null) {
                "Only one $directionName-swipe SwipeableActionButton can set triggerOnDeepSwipe."
            }
            selectedAction = action
        }
    }
    return selectedAction
}

private fun Float.swipeDirection(): SwipeDirection? = when {
    this < 0f -> SwipeDirection.LEFT
    this > 0f -> SwipeDirection.RIGHT
    else -> null
}

internal fun rubberBandSwipeOffset(
    currentOffset: Float,
    delta: Float,
    leftRevealOffsetPx: Float,
    rightRevealOffsetPx: Float,
    viewportWidthPx: Float
): Float {
    val leftRevealOffset = leftRevealOffsetPx.coerceAtLeast(0f)
    val rightRevealOffset = rightRevealOffsetPx.coerceAtLeast(0f)
    val nextOffset = currentOffset + delta
    val direction = nextOffset.swipeDirection() ?: return 0f
    val revealOffset = when (direction) {
        SwipeDirection.LEFT -> leftRevealOffset
        SwipeDirection.RIGHT -> rightRevealOffset
    }
    if (revealOffset == 0f) return 0f

    val directedOffset = nextOffset * direction.sign
    if (directedOffset <= revealOffset || viewportWidthPx <= 0f) return nextOffset

    val directedCurrentOffset = currentOffset * direction.sign
    val overscroll = directedOffset - revealOffset
    val previousOverscroll = (directedCurrentOffset - revealOffset).coerceAtLeast(0f)
    val dimension = viewportWidthPx.coerceAtLeast(revealOffset)
    val resistance = dimension / (dimension + SwipeRubberBandConstant * previousOverscroll)
    val resistedOverscroll = previousOverscroll + (overscroll - previousOverscroll) * resistance

    return direction.sign * (revealOffset + resistedOverscroll.coerceAtLeast(0f))
}
