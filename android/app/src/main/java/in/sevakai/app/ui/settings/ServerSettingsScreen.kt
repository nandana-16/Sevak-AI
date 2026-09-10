package `in`.sevakai.app.ui.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.sevakai.app.data.ConnectionCheck
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.ui.components.Notice
import `in`.sevakai.app.ui.components.NoticeTone
import `in`.sevakai.app.ui.components.SectionCard
import `in`.sevakai.app.ui.components.SectionLabel
import `in`.sevakai.app.ui.i18n.LocalStrings
import `in`.sevakai.app.ui.theme.LocalRiskPalette

/**
 * Where the backend is, and whether the phone can actually reach it.
 *
 * Deliberately reachable *before* sign-in: if the address is wrong, signing in
 * is the thing that fails, so the fix has to be available from the screen where
 * the failure appears.
 */
@Composable
fun ServerSettingsScreen(repository: Repository, onBack: () -> Unit) {
    val context = LocalContext.current
    val viewModel: ServerSettingsViewModel = viewModel(
        factory = ServerSettingsViewModel.factory(repository, context.applicationContext)
    )
    val state by viewModel.state.collectAsStateWithLifecycle()
    val palette = LocalRiskPalette.current
    val strings = LocalStrings.current

    Scaffold(containerColor = MaterialTheme.colorScheme.background) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .imePadding(),
        ) {
            Row(
                Modifier.fillMaxWidth().padding(start = 4.dp, end = 20.dp, top = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = strings.back)
                }
                Column(Modifier.weight(1f)) {
                    Text(strings.serverTitle, style = MaterialTheme.typography.titleMedium)
                    Text(
                        strings.serverSubtitle,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Column(Modifier.padding(horizontal = 20.dp)) {
                Spacer(Modifier.height(8.dp))

                SectionCard {
                    SectionLabel(strings.howConnected)
                    Spacer(Modifier.height(12.dp))

                    PresetRow(
                        title = strings.presetUsb,
                        subtitle = strings.presetUsbHint,
                        selected = state.isUsb,
                    ) { viewModel.usePreset(`in`.sevakai.app.data.SettingsStore.USB) }

                    Spacer(Modifier.height(8.dp))
                    PresetRow(
                        title = strings.presetEmulator,
                        subtitle = strings.presetEmulatorHint,
                        selected = state.isEmulator,
                    ) { viewModel.usePreset(`in`.sevakai.app.data.SettingsStore.EMULATOR) }

                    Spacer(Modifier.height(8.dp))
                    PresetRow(
                        title = strings.presetWifi,
                        subtitle = strings.presetWifiHint,
                        selected = state.isCustom,
                    ) { viewModel.useCustom() }
                }

                Spacer(Modifier.height(14.dp))

                SectionCard {
                    SectionLabel(strings.addressLabel)
                    Spacer(Modifier.height(10.dp))
                    OutlinedTextField(
                        value = state.input,
                        onValueChange = viewModel::onInputChange,
                        placeholder = { Text("192.168.1.7") },
                        singleLine = true,
                        shape = MaterialTheme.shapes.small,
                        textStyle = MaterialTheme.typography.bodyLarge.copy(
                            fontFamily = FontFamily.Monospace
                        ),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        strings.willConnectTo(state.resolvedLabel),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontFamily = FontFamily.Monospace,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        strings.addressHint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }

                Spacer(Modifier.height(14.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedButton(
                        onClick = viewModel::test,
                        enabled = !state.testing,
                        shape = MaterialTheme.shapes.small,
                        modifier = Modifier.weight(1f).heightIn(min = 52.dp),
                    ) {
                        if (state.testing) {
                            CircularProgressIndicator(
                                Modifier.size(18.dp), strokeWidth = 2.dp,
                            )
                        } else {
                            Text(strings.testConnection, style = MaterialTheme.typography.labelLarge)
                        }
                    }
                    Button(
                        onClick = viewModel::save,
                        enabled = !state.testing,
                        shape = MaterialTheme.shapes.small,
                        modifier = Modifier.weight(1f).heightIn(min = 52.dp),
                    ) {
                        Text(strings.save, style = MaterialTheme.typography.labelLarge)
                    }
                }

                state.result?.let { result ->
                    Spacer(Modifier.height(14.dp))
                    when (result) {
                        is ConnectionCheck.Result.Ok -> SectionCard(accent = palette.green) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    Icons.Default.CheckCircle,
                                    contentDescription = null,
                                    tint = palette.green,
                                    modifier = Modifier.size(20.dp),
                                )
                                Spacer(Modifier.width(10.dp))
                                Text(
                                    strings.connected,
                                    style = MaterialTheme.typography.titleSmall,
                                    color = palette.green,
                                )
                            }
                            Spacer(Modifier.height(8.dp))
                            Text(result.message, style = MaterialTheme.typography.bodyMedium)
                            if (!result.llmReady) {
                                Spacer(Modifier.height(10.dp))
                                Notice(
                                    strings.noLlmWarning,
                                    tone = NoticeTone.WARNING,
                                )
                            }
                        }

                        is ConnectionCheck.Result.Failed -> SectionCard(accent = palette.amber) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    Icons.Default.Error,
                                    contentDescription = null,
                                    tint = palette.amber,
                                    modifier = Modifier.size(20.dp),
                                )
                                Spacer(Modifier.width(10.dp))
                                Text(
                                    result.message,
                                    style = MaterialTheme.typography.titleSmall,
                                    color = palette.amber,
                                )
                            }
                            Spacer(Modifier.height(8.dp))
                            Text(result.hint, style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }

                if (state.saved) {
                    Spacer(Modifier.height(14.dp))
                    Notice(strings.saved, tone = NoticeTone.INFO)
                }

                Spacer(Modifier.height(20.dp))

                SectionCard {
                    SectionLabel(strings.findingYourIp)
                    Spacer(Modifier.height(8.dp))
                    Text(
                        strings.findingYourIpBody,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontFamily = FontFamily.Monospace,
                    )
                }

                Spacer(Modifier.height(40.dp))
            }
        }
    }
}

@Composable
private fun PresetRow(
    title: String,
    subtitle: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .clip(MaterialTheme.shapes.small)
            .background(
                if (selected) MaterialTheme.colorScheme.primaryContainer
                else MaterialTheme.colorScheme.surfaceVariant
            )
            .clickable(onClick = onClick)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .size(18.dp)
                .clip(CircleShape)
                .background(
                    if (selected) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.outline
                ),
            contentAlignment = Alignment.Center,
        ) {
            if (selected) {
                Box(
                    Modifier
                        .size(7.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.onPrimary)
                )
            }
        }
        Spacer(Modifier.width(12.dp))
        Column {
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Medium,
            )
            Text(
                subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
