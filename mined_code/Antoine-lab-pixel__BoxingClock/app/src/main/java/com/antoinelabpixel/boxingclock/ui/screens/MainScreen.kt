package com.antoinelabpixel.boxingclock.ui.screens

import android.app.Activity
import android.content.res.Configuration
import android.view.WindowManager
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.VolumeOff
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.antoinelabpixel.boxingclock.model.Phase
import com.antoinelabpixel.boxingclock.model.TimerState
import com.antoinelabpixel.boxingclock.ui.theme.PhasePreparationColor
import com.antoinelabpixel.boxingclock.ui.theme.PhaseRestColor
import com.antoinelabpixel.boxingclock.ui.theme.PhaseWorkColor

@Composable
fun MainScreen(
    timerState: TimerState,
    totalRounds: Int,
    workTime: Int,
    restTime: Int,
    isMuted: Boolean,
    onStartClick: () -> Unit,
    onPauseClick: () -> Unit,
    onResetClick: () -> Unit,
    onMuteToggle: () -> Unit,
    onSettingsClick: () -> Unit
) {
    val configuration = LocalConfiguration.current
    val isLandscape = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE

    val backgroundColor = when (timerState.currentPhase) {
        Phase.PREPARATION -> PhasePreparationColor
        Phase.WORK -> PhaseWorkColor
        Phase.REST -> PhaseRestColor
    }

    val isInitialState = !timerState.hasStarted

    // Keep screen on while the timer is running
    val window = (LocalContext.current as Activity).window
    DisposableEffect(timerState.isRunning) {
        if (timerState.isRunning) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
        onDispose {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(backgroundColor)
    ) {
        // Main content
        if (isInitialState) {
            StartOverlay(
                timeRemaining = timerState.timeRemaining,
                onStartClick = onStartClick,
                isLandscape = isLandscape,
                modifier = if (isLandscape) Modifier.fillMaxSize() else Modifier.align(Alignment.Center)
            )
        } else {
            // Phase label + timer
            Column(
                modifier = Modifier.align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                if (!isLandscape) {
                    val phaseLabel = when (timerState.currentPhase) {
                        Phase.PREPARATION -> "PREP"
                        Phase.WORK -> "WORK"
                        Phase.REST -> "REST"
                    }
                    Text(
                        text = phaseLabel,
                        fontSize = 26.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 10.sp,
                        color = Color.Black.copy(alpha = 0.45f)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                }
                TimerDisplay(
                    timeInSeconds = timerState.timeRemaining,
                    totalPhaseTime = timerState.totalPhaseTime,
                    isLandscape = isLandscape
                )
            }

            // Full-screen click overlay (pause/resume)
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .clickable {
                        if (timerState.isRunning) onPauseClick() else onStartClick()
                    }
            )

            // Paused overlay
            if (!timerState.isRunning) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.28f))
                )

                if (isLandscape) {
                    // Landscape: PAUSED + RESET grouped centrally
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .align(Alignment.Center)
                            .displayCutoutPadding()
                            .padding(horizontal = 32.dp),
                        horizontalArrangement = Arrangement.spacedBy(48.dp, Alignment.CenterHorizontally),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "PAUSED",
                            fontSize = 52.sp,
                            fontWeight = FontWeight.Black,
                            letterSpacing = 6.sp,
                            color = Color.White
                        )
                        Button(
                            onClick = onResetClick,
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color.White.copy(alpha = 0.25f),
                                contentColor = Color.White
                            )
                        ) {
                            Text(
                                text = "RESET",
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 2.sp,
                                fontSize = 32.sp
                            )
                        }
                    }
                } else {
                    // Portrait: PAUSED + RESET stacked at bottom
                    Column(
                        modifier = Modifier
                            .align(Alignment.BottomCenter)
                            .padding(bottom = 48.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "PAUSED",
                            fontSize = 64.sp,
                            fontWeight = FontWeight.Black,
                            letterSpacing = 6.sp,
                            color = Color.White
                        )
                        Button(
                            onClick = onResetClick,
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Color.White.copy(alpha = 0.25f),
                                contentColor = Color.White
                            )
                        ) {
                            Text(
                                text = "RESET",
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 2.sp,
                                fontSize = 32.sp
                            )
                        }
                    }
                }
            }

            // Progress indicator (drawn last so it sits above the scrim)
            val progress = timerState.timeRemaining.toFloat() / timerState.totalPhaseTime.toFloat()
            if (isLandscape) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(20.dp)
                        .align(Alignment.BottomCenter)
                        .background(Color.Black.copy(alpha = 0.12f))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxHeight()
                            .fillMaxWidth(progress)
                            .align(Alignment.CenterStart)
                            .background(Color.Black.copy(alpha = 0.35f))
                    )
                }
            } else {
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .width(14.dp)
                        .align(Alignment.CenterEnd)
                        .background(Color.Black.copy(alpha = 0.12f))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .fillMaxHeight(progress)
                            .align(Alignment.BottomCenter)
                            .background(Color.Black.copy(alpha = 0.35f))
                    )
                }
            }
        }

        // Top bar — drawn last so it stays above all overlays and remains clickable
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .displayCutoutPadding()
                .padding(horizontal = 16.dp, vertical = 12.dp)
                .align(Alignment.TopCenter)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                if (isInitialState) {
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        val roundsDisplay = if (totalRounds == 0) "∞" else "$totalRounds"
                        SessionInfoRow(label = "ROUNDS", value = roundsDisplay)
                        SessionInfoRow(label = "WORK", value = formatDuration(workTime))
                        SessionInfoRow(label = "REST", value = formatDuration(restTime))
                    }
                } else {
                    Column {
                        Text(
                            text = "ROUND",
                            fontSize = 32.sp,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 3.sp,
                            color = Color.Black.copy(alpha = 0.55f)
                        )
                        val roundText = if (totalRounds > 0)
                            "${timerState.currentRound} / $totalRounds"
                        else
                            "${timerState.currentRound}"
                        Text(
                            text = roundText,
                            fontSize = 64.sp,
                            fontWeight = FontWeight.Black,
                            letterSpacing = (-1).sp,
                            color = Color.Black,
                            lineHeight = 58.sp
                        )
                    }
                }

                Row {
                    IconButton(onClick = onMuteToggle) {
                        Icon(
                            if (isMuted) Icons.Default.VolumeOff else Icons.Default.VolumeUp,
                            contentDescription = if (isMuted) "Unmute" else "Mute",
                            tint = Color.Black.copy(alpha = 0.7f),
                            modifier = Modifier.size(28.dp)
                        )
                    }
                    IconButton(onClick = onSettingsClick) {
                        Icon(
                            Icons.Default.Settings,
                            contentDescription = "Settings",
                            tint = Color.Black.copy(alpha = 0.7f),
                            modifier = Modifier.size(28.dp)
                        )
                    }
                }
            }

            // Phase label centered in the top bar (landscape only)
            if (isLandscape && !isInitialState) {
                val phaseLabel = when (timerState.currentPhase) {
                    Phase.PREPARATION -> "PREP"
                    Phase.WORK -> "WORK"
                    Phase.REST -> "REST"
                }
                Text(
                    text = phaseLabel,
                    fontSize = 26.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 10.sp,
                    color = Color.Black.copy(alpha = 0.45f),
                    modifier = Modifier.align(Alignment.Center)
                )
            }
        }
    }
}

@Composable
private fun SessionInfoRow(label: String, value: String) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 2.sp,
            color = Color.Black.copy(alpha = 0.55f),
            modifier = Modifier.width(150.dp)
        )
        Text(
            text = value,
            fontSize = 32.sp,
            fontWeight = FontWeight.Black,
            color = Color.Black
        )
    }
}

private fun formatDuration(seconds: Int): String =
    if (seconds >= 60) String.format("%d:%02d", seconds / 60, seconds % 60)
    else "${seconds}s"

@Composable
fun StartOverlay(
    timeRemaining: Int,
    onStartClick: () -> Unit,
    isLandscape: Boolean = false,
    modifier: Modifier = Modifier
) {
    if (isLandscape) {
        Box(modifier = modifier.clickable { onStartClick() }) {
            Icon(
                imageVector = Icons.Default.PlayArrow,
                contentDescription = "Start",
                tint = Color(0xFF2E7D32),
                modifier = Modifier
                    .size(360.dp)
                    .align(Alignment.Center)
            )
            Text(
                text = "Prep ${timeRemaining}s",
                fontSize = 64.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = (-1).sp,
                color = Color.Black,
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .displayCutoutPadding()
                    .padding(start = 48.dp)
            )
            Text(
                text = "TAP TO START",
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 4.sp,
                color = Color.Black.copy(alpha = 0.5f),
                modifier = Modifier
                    .align(Alignment.CenterEnd)
                    .padding(end = 48.dp)
            )
        }
    } else {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = modifier.clickable { onStartClick() }
        ) {
            Icon(
                imageVector = Icons.Default.PlayArrow,
                contentDescription = "Start",
                tint = Color(0xFF2E7D32),
                modifier = Modifier.size(360.dp)
            )
            Text(
                text = "Prep ${timeRemaining}s",
                fontSize = 64.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = (-1).sp,
                color = Color.Black
            )
            Text(
                text = "TAP TO START",
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 4.sp,
                color = Color.Black.copy(alpha = 0.5f),
                modifier = Modifier.padding(top = 12.dp)
            )
        }
    }
}

@Composable
fun TimerDisplay(
    timeInSeconds: Int,
    totalPhaseTime: Int,
    isLandscape: Boolean = false
) {
    val minutes = timeInSeconds / 60
    val seconds = timeInSeconds % 60

    when {
        totalPhaseTime >= 60 && isLandscape && minutes > 0 -> {
            // Landscape with minutes remaining: single-line MM:SS
            Text(
                text = String.format("%02d:%02d", minutes, seconds),
                fontSize = 140.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = (-3).sp,
                color = Color.Black,
                lineHeight = 135.sp
            )
        }
        totalPhaseTime >= 60 && isLandscape -> {
            // Landscape, minutes reached 0: show seconds only
            Text(
                text = seconds.toString(),
                fontSize = 200.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = (-6).sp,
                color = Color.Black,
                lineHeight = 190.sp
            )
        }
        totalPhaseTime >= 60 -> {
            // Portrait with minutes: stacked, hide minutes row when it reaches 0
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                if (minutes > 0) {
                    Text(
                        text = String.format("%02d", minutes),
                        fontSize = 200.sp,
                        fontWeight = FontWeight.Black,
                        letterSpacing = (-6).sp,
                        color = Color.Black,
                        lineHeight = 195.sp
                    )
                }
                Text(
                    text = String.format("%02d", seconds),
                    fontSize = 200.sp,
                    fontWeight = FontWeight.Black,
                    letterSpacing = (-6).sp,
                    color = Color.Black,
                    lineHeight = 195.sp
                )
            }
        }
        isLandscape -> {
            // Landscape sub-60s: scaled down
            Text(
                text = timeInSeconds.toString(),
                fontSize = 200.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = (-6).sp,
                color = Color.Black,
                lineHeight = 190.sp
            )
        }
        else -> {
            // Portrait sub-60s: large single number
            Text(
                text = timeInSeconds.toString(),
                fontSize = 280.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = (-8).sp,
                color = Color.Black,
                lineHeight = 270.sp
            )
        }
    }
}
