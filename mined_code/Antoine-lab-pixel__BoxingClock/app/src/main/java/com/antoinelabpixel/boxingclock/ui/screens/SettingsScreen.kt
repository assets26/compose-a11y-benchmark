package com.antoinelabpixel.boxingclock.ui.screens

import android.media.AudioManager
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.antoinelabpixel.boxingclock.model.TimerSettings

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    settings: TimerSettings,
    selectedPreset: Int,
    onPresetSelect: (Int) -> Unit,
    onSettingClick: (String) -> Unit,
    onSettingsChange: (TimerSettings) -> Unit,
    onBackClick: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Return")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .displayCutoutPadding()
        ) {
            // Preset selector — fixed, outside the scroll area
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp)
                    .clip(RoundedCornerShape(50))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                listOf("1", "2", "3").forEachIndexed { index, label ->
                    val isSelected = selectedPreset == index
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .padding(4.dp)
                            .clip(RoundedCornerShape(50))
                            .background(
                                if (isSelected) MaterialTheme.colorScheme.primary
                                else androidx.compose.ui.graphics.Color.Transparent
                            )
                            .clickable { onPresetSelect(index) }
                            .padding(vertical = 10.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = label,
                            fontSize = 18.sp,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                            color = if (isSelected) MaterialTheme.colorScheme.onPrimary
                                    else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            val audioManager = LocalContext.current.getSystemService(AudioManager::class.java)
            val maxVolume = audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM)
            var alarmVolume by remember {
                mutableStateOf(audioManager.getStreamVolume(AudioManager.STREAM_ALARM).toFloat().coerceAtLeast(1f))
            }

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
            ) {
            SettingRow(
                label = "Prep",
                value = formatDuration(settings.preparationTime),
                onClick = { onSettingClick("preparation") }
            )
            HorizontalDivider()
            SettingRow(
                label = "Work",
                value = formatDuration(settings.workTime),
                onClick = { onSettingClick("work") }
            )
            HorizontalDivider()
            SettingRow(
                label = "Rest",
                value = formatDuration(settings.restTime),
                onClick = { onSettingClick("rest") }
            )
            HorizontalDivider()
            SettingRow(
                label = "Rounds",
                value = if (settings.rounds == 0) "∞" else "${settings.rounds}",
                onClick = { onSettingClick("rounds") }
            )
            HorizontalDivider()

            // Alarm volume slider
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.VolumeUp,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Slider(
                    value = alarmVolume,
                    onValueChange = {
                        alarmVolume = it
                        audioManager.setStreamVolume(AudioManager.STREAM_ALARM, it.toInt(), 0)
                    },
                    valueRange = 1f..maxVolume.toFloat(),
                    steps = maxVolume - 2,
                    modifier = Modifier.weight(1f)
                )
                Text(
                    text = "${alarmVolume.toInt()} / $maxVolume",
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.width(40.dp)
                )
            }
            HorizontalDivider()

            // Bell toggle
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 20.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Bell", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Text(
                        text = "Sound at every phase transition",
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Switch(
                    checked = settings.bellEnabled,
                    onCheckedChange = { onSettingsChange(settings.copy(bellEnabled = it)) }
                )
            }
            HorizontalDivider()
            // End bell toggle
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 20.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("End bell", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Text(
                        text = "Sound when all rounds are complete",
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Switch(
                    checked = settings.endBellEnabled,
                    onCheckedChange = { onSettingsChange(settings.copy(endBellEnabled = it)) }
                )
            }
            HorizontalDivider()
            // Clapper toggle — immediate, no dedicated edit screen needed
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 20.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Clapper", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Text(
                        text = "10s left in round at the end of the sound",
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Switch(
                    checked = settings.clapperEnabled,
                    onCheckedChange = { onSettingsChange(settings.copy(clapperEnabled = it)) }
                )
            }
            HorizontalDivider()
            // 30s reminder toggle
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 20.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("30s reminder", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Text(
                        text = "Sound when 30s of work time remain",
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Switch(
                    checked = settings.thirtySecondsEnabled,
                    onCheckedChange = { onSettingsChange(settings.copy(thirtySecondsEnabled = it)) }
                )
            }
            } // end scrollable Column
        }
    }
}

@Composable
private fun SettingRow(label: String, value: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 20.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        Text(value, fontSize = 20.sp, color = MaterialTheme.colorScheme.primary)
    }
}

private fun formatDuration(seconds: Int): String =
    if (seconds >= 60) String.format("%d:%02d", seconds / 60, seconds % 60)
    else "${seconds}s"
