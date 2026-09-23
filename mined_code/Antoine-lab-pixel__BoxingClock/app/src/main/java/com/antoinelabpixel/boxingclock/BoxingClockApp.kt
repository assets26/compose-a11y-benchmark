package com.antoinelabpixel.boxingclock

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.antoinelabpixel.boxingclock.ui.screens.MainScreen
import com.antoinelabpixel.boxingclock.ui.screens.SettingEditScreen
import com.antoinelabpixel.boxingclock.ui.screens.SettingsScreen

@Composable
fun BoxingClockApp(viewModel: TimerViewModel) {
    val navController = rememberNavController()
    val timerState by viewModel.timerState.collectAsState()
    val settings by viewModel.settings.collectAsState()
    val selectedPreset by viewModel.selectedPreset.collectAsState()
    val isMuted by viewModel.isMuted.collectAsState()

    NavHost(navController = navController, startDestination = "main") {
        composable("main") {
            MainScreen(
                timerState = timerState,
                totalRounds = settings.rounds,
                workTime = settings.workTime,
                restTime = settings.restTime,
                isMuted = isMuted,
                onStartClick = { viewModel.startTimer() },
                onPauseClick = { viewModel.pauseTimer() },
                onResetClick = { viewModel.resetTimer() },
                onMuteToggle = { viewModel.toggleMute() },
                onSettingsClick = { navController.navigate("settings") }
            )
        }
        composable("settings") {
            SettingsScreen(
                settings = settings,
                selectedPreset = selectedPreset,
                onPresetSelect = { viewModel.selectPreset(it) },
                onSettingClick = { key -> navController.navigate("settings/edit/$key") },
                onSettingsChange = { newSettings -> viewModel.updateSettings(newSettings) },
                onBackClick = { navController.popBackStack() }
            )
        }
        composable("settings/edit/{setting}") { backStackEntry ->
            val settingKey = backStackEntry.arguments?.getString("setting") ?: return@composable
            SettingEditScreen(
                settingKey = settingKey,
                settings = settings,
                onSettingsChange = { newSettings -> viewModel.updateSettings(newSettings) },
                onBackClick = { navController.popBackStack() }
            )
        }
    }
}
