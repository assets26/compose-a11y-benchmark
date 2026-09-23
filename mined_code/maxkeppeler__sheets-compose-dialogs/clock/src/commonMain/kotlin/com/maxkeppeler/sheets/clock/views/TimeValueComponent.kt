/*
 *  Copyright (C) 2022-2024. Maximilian Keppeler (https://www.maxkeppeler.com)
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */
@file:OptIn(ExperimentalTextApi::class, ExperimentalMaterial3Api::class)

package com.maxkeppeler.sheets.clock.views

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import com.maxkeppeker.sheets.core.utils.TestTags
import com.maxkeppeker.sheets.core.utils.testTags
import org.jetbrains.compose.resources.ExperimentalResourceApi
import org.jetbrains.compose.resources.stringResource
import sheets_compose_dialogs.clock.generated.resources.*
import sheets_compose_dialogs.clock.generated.resources.Res
import sheets_compose_dialogs.clock.generated.resources.scd_clock_dialog_am
import sheets_compose_dialogs.clock.generated.resources.scd_clock_dialog_hours
import sheets_compose_dialogs.clock.generated.resources.scd_clock_dialog_pm

@OptIn(ExperimentalResourceApi::class)
@Composable
internal fun PortraitTimeValueComponent(
    modifier: Modifier,
    verticalArrangement: Arrangement.Vertical = Arrangement.Top,
    valueIndex: Int,
    groupIndex: Int,
    unitValues: List<StringBuilder>,
    is24hourFormat: Boolean,
    isAm: Boolean,
    onGroupClick: (Int) -> Unit,
    onAm: (Boolean) -> Unit,
) {

    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = verticalArrangement,
    ) {

        Row(
            modifier = Modifier
                .wrapContentWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.Bottom
        ) {

            unitValues.forEachIndexed { currentGroupIndex, value ->

                val textStyle =
                    MaterialTheme.typography.displaySmall.copy(fontWeight = FontWeight.Bold)

                Text(
                    modifier = Modifier
                        .wrapContentSize()
                        .clip(MaterialTheme.shapes.medium)
                        .background(if (currentGroupIndex == groupIndex) MaterialTheme.colorScheme.secondaryContainer else Color.Transparent)
                        .clickable { onGroupClick.invoke(currentGroupIndex) }
                        .padding(horizontal = 6.dp),
                    text = buildAnnotatedString {
                        val values = value.toString().toCharArray()
                        val selectedStyle = SpanStyle(
                            color = MaterialTheme.colorScheme.primary,
                        )
                        values.forEachIndexed { currentValueIndex, value ->
                            val selected = currentGroupIndex == groupIndex
                                    && currentValueIndex == valueIndex
                            if (selected) withStyle(selectedStyle) { append(value) }
                            else append(value)
                        }
                    },
                    style = textStyle
                )

                if (currentGroupIndex != unitValues.lastIndex) {
                    Text(
                        modifier = Modifier
                            .wrapContentSize()
                            .padding(horizontal = 4.dp),
                        text = ":",
                        style = textStyle
                    )
                }
            }
        }
        if (!is24hourFormat) {
            Row(
                Modifier
                    .padding(top = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                TimeTypeItemComponent(
                    modifier = Modifier.testTags(TestTags.CLOCK_12_HOUR_FORMAT, 0),
                    selected = isAm,
                    onClick = { onAm.invoke(true) },
                    text = stringResource(Res.string.scd_clock_dialog_am),
                )
                TimeTypeItemComponent(
                    modifier = Modifier.testTags(TestTags.CLOCK_12_HOUR_FORMAT, 1),
                    selected = !isAm,
                    onClick = { onAm.invoke(false) },
                    text = stringResource(Res.string.scd_clock_dialog_pm),
                )
            }
        }
    }
}


@OptIn(ExperimentalResourceApi::class)
@Composable
internal fun LandscapeTimeValueComponent(
    modifier: Modifier,
    verticalArrangement: Arrangement.Vertical = Arrangement.Top,
    valueIndex: Int,
    groupIndex: Int,
    unitValues: List<StringBuilder>,
    is24hourFormat: Boolean,
    isAm: Boolean,
    onGroupClick: (Int) -> Unit,
    onAm: (Boolean) -> Unit,
) {

    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.Start,
        verticalArrangement = verticalArrangement,
    ) {

        val labelRes = listOf(
            Res.string.scd_clock_dialog_hours,
            Res.string.scd_clock_dialog_minutes,
            Res.string.scd_clock_dialog_seconds,
        )

        Column(
            modifier = Modifier
                .wrapContentWidth(),
            verticalArrangement = Arrangement.Center
        ) {

            unitValues.forEachIndexed { currentGroupIndex, value ->

                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {

                    val textStyle =
                        MaterialTheme.typography.displaySmall.copy(fontWeight = FontWeight.Bold)

                    Text(
                        modifier = Modifier
                            .wrapContentSize()
                            .clip(MaterialTheme.shapes.medium)
                            .background(if (currentGroupIndex == groupIndex) MaterialTheme.colorScheme.secondaryContainer else Color.Transparent)
                            .clickable { onGroupClick.invoke(currentGroupIndex) }
                            .padding(horizontal = 6.dp),
                        text = buildAnnotatedString {
                            val values = value.toString().toCharArray()
                            val selectedStyle = SpanStyle(
                                color = MaterialTheme.colorScheme.primary,
                            )
                            values.forEachIndexed { currentValueIndex, value ->
                                val selected = currentGroupIndex == groupIndex
                                        && currentValueIndex == valueIndex
                                if (selected) withStyle(selectedStyle) { append(value) }
                                else append(value)
                            }
                        },
                        style = textStyle
                    )
                    Spacer(modifier = Modifier.width(12.dp))

                    Text(
                        text = stringResource(labelRes[currentGroupIndex]),
                        style = MaterialTheme.typography.labelSmall,
                    )

                }
            }
        }
        if (!is24hourFormat) {
            Row(
                Modifier
                    .padding(top = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                TimeTypeItemComponent(
                    modifier = Modifier.testTags(TestTags.CLOCK_12_HOUR_FORMAT, 0),
                    selected = isAm,
                    onClick = { onAm.invoke(true) },
                    text = stringResource(Res.string.scd_clock_dialog_am),
                )
                TimeTypeItemComponent(
                    modifier = Modifier.testTags(TestTags.CLOCK_12_HOUR_FORMAT, 1),
                    selected = !isAm,
                    onClick = { onAm.invoke(false) },
                    text = stringResource(Res.string.scd_clock_dialog_pm),
                )
            }
        }
    }
}