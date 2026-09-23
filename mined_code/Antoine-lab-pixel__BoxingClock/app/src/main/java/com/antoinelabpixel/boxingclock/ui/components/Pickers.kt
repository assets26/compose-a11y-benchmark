package com.antoinelabpixel.boxingclock.ui.components

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.snapping.rememberSnapFlingBehavior
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun WheelPicker(
    items: List<String>,
    initialIndex: Int,
    onSelectionChanged: (Int) -> Unit,
    visibleItemsCount: Int = 3,
    itemHeight: Dp = 40.dp,
    modifier: Modifier = Modifier
) {
    val listState = rememberLazyListState(initialFirstVisibleItemIndex = initialIndex)
    val flingBehavior = rememberSnapFlingBehavior(lazyListState = listState)
    
    // Calculate content padding to center the selected item
    val containerHeight = itemHeight * visibleItemsCount
    val paddingY = (containerHeight - itemHeight) / 2

    // Logic to determine the centered item
    val centerItemIndex by remember {
        derivedStateOf {
            val layoutInfo = listState.layoutInfo
            if (layoutInfo.visibleItemsInfo.isEmpty()) return@derivedStateOf initialIndex
            
            val centerOffset = layoutInfo.viewportEndOffset / 2
            
            // Find the item that contains the center offset
            val centerItem = layoutInfo.visibleItemsInfo.find { item ->
                centerOffset >= item.offset && centerOffset <= item.offset + item.size
            }
            
            centerItem?.index ?: initialIndex
        }
    }
    
    // Notify selection change
    LaunchedEffect(centerItemIndex) {
        if (centerItemIndex in items.indices) {
            onSelectionChanged(centerItemIndex)
        }
    }
    
    // Handle external updates (e.g. reset)
    LaunchedEffect(initialIndex) {
        if (!listState.isScrollInProgress && initialIndex != centerItemIndex) {
            listState.scrollToItem(initialIndex)
        }
    }

    Box(
        modifier = modifier
            .height(containerHeight)
            .fillMaxWidth(),
        contentAlignment = Alignment.Center
    ) {
        // Selection Indicator (Background)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(itemHeight)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f))
        )

        LazyColumn(
            state = listState,
            flingBehavior = flingBehavior,
            contentPadding = PaddingValues(vertical = paddingY),
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxSize()
        ) {
            items(items.size) { index ->
                val isSelected = index == centerItemIndex
                
                Box(
                    modifier = Modifier
                        .height(itemHeight)
                        .fillMaxWidth(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = items[index],
                        fontSize = if (isSelected) 24.sp else 18.sp,
                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                        color = if (isSelected) 
                            MaterialTheme.colorScheme.onSurface 
                        else 
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        textAlign = TextAlign.Center
                    )
                }
            }
        }
    }
}

@Composable
fun TimePicker(
    minutes: Int,   
    seconds: Int,
    onMinutesChange: (Int) -> Unit,
    onSecondsChange: (Int) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Minutes
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Min", fontSize = 14.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 8.dp))
            WheelPicker(
                items = (0..60).map { it.toString() },
                initialIndex = minutes,
                onSelectionChanged = onMinutesChange,
                modifier = Modifier.width(80.dp)
            )
        }

        Text(
            text = ":", 
            fontSize = 32.sp, 
            fontWeight = FontWeight.Bold, 
            modifier = Modifier.padding(horizontal = 16.dp).offset(y = 10.dp)
        )

        // Seconds
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("Sec", fontSize = 14.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 8.dp))
            WheelPicker(
                items = (0..59).map { String.format("%02d", it) },
                initialIndex = seconds,
                onSelectionChanged = onSecondsChange,
                modifier = Modifier.width(80.dp)
            )
        }
    }
}

@Composable
fun RoundsPicker(
    rounds: Int,
    onRoundsChange: (Int) -> Unit
) {
    // 0 is Infinite, 1-20 are numbers
    val items = listOf("∞") + (1..20).map { it.toString() }
    val initialIndex = if (rounds == 0) 0 else rounds // rounds 1 maps to index 1 (value "1")

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text("Rounds", fontSize = 14.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(bottom = 8.dp))
        WheelPicker(
            items = items,
            initialIndex = initialIndex,
            onSelectionChanged = { index ->
                val newValue = if (index == 0) 0 else index
                onRoundsChange(newValue)
            },
            modifier = Modifier.width(100.dp)
        )
    }
}
