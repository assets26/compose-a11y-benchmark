package com.antoinelabpixel.boxingclock.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.antoinelabpixel.boxingclock.model.TimerSettings
import com.antoinelabpixel.boxingclock.ui.components.RoundsPicker
import com.antoinelabpixel.boxingclock.ui.components.TimePicker

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingEditScreen(
    settingKey: String,
    settings: TimerSettings,
    onSettingsChange: (TimerSettings) -> Unit,
    onBackClick: () -> Unit
) {
    val title = when (settingKey) {
        "preparation" -> "Prep"
        "work" -> "Work"
        "rest" -> "Rest"
        "rounds" -> "Rounds"
        else -> ""
    }

    // Initialise local state unconditionally
    val initialMinutes = when (settingKey) {
        "preparation" -> settings.preparationTime / 60
        "work" -> settings.workTime / 60
        "rest" -> settings.restTime / 60
        else -> 0
    }
    val initialSeconds = when (settingKey) {
        "preparation" -> settings.preparationTime % 60
        "work" -> settings.workTime % 60
        "rest" -> settings.restTime % 60
        else -> 0
    }

    var minutes by remember { mutableIntStateOf(initialMinutes) }
    var seconds by remember { mutableIntStateOf(initialSeconds) }
    var rounds by remember { mutableIntStateOf(settings.rounds) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Annuler")
                    }
                }
            )
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(40.dp)
            ) {
                when (settingKey) {
                    "preparation", "work", "rest" -> TimePicker(
                        minutes = minutes,
                        seconds = seconds,
                        onMinutesChange = { minutes = it },
                        onSecondsChange = { seconds = it }
                    )
                    "rounds" -> RoundsPicker(
                        rounds = rounds,
                        onRoundsChange = { rounds = it }
                    )
                }

                Button(
                    onClick = {
                        val newSettings = when (settingKey) {
                            "preparation" -> settings.copy(preparationTime = minutes * 60 + seconds)
                            "work" -> settings.copy(workTime = minutes * 60 + seconds)
                            "rest" -> settings.copy(restTime = minutes * 60 + seconds)
                            "rounds" -> settings.copy(rounds = rounds)
                            else -> settings
                        }
                        onSettingsChange(newSettings)
                        onBackClick()
                    },
                    modifier = Modifier.width(160.dp)
                ) {
                    Text("OK", fontSize = 18.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}
