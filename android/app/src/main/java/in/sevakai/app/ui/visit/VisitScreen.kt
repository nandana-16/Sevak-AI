package `in`.sevakai.app.ui.visit

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.FiberManualRecord
import androidx.compose.material.icons.filled.Keyboard
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.ui.components.Notice
import `in`.sevakai.app.ui.components.NoticeTone
import `in`.sevakai.app.ui.components.SectionCard
import `in`.sevakai.app.ui.components.SectionLabel
import `in`.sevakai.app.ui.i18n.LocalStrings

@Composable
fun VisitScreen(
    repository: Repository,
    patientId: String,
    onBack: () -> Unit,
    onDone: () -> Unit,
) {
    val context = LocalContext.current
    val application = context.applicationContext as android.app.Application
    val viewModel: VisitViewModel = viewModel(
        factory = VisitViewModel.factory(application, repository, patientId)
    )
    val state by viewModel.state.collectAsStateWithLifecycle()
    val strings = LocalStrings.current

    var micGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED
        )
    }
    var pendingAction by remember { mutableStateOf<(() -> Unit)?>(null) }

    val micPermission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        micGranted = granted
        if (granted) pendingAction?.invoke()
        pendingAction = null
    }

    fun withMic(action: () -> Unit) {
        if (micGranted) action() else {
            pendingAction = action
            micPermission.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    // A finished visit takes over the screen entirely.
    state.result?.let { visit ->
        VisitResultBody(visit = visit, onDone = onDone)
        return
    }

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
                    Text(strings.recordVisitTitle, style = MaterialTheme.typography.titleMedium)
                    state.patient?.let {
                        Text(
                            it.name,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }

            Spacer(Modifier.height(8.dp))

            // --- Mode switch: voice and typing are peers, not fallbacks ------
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp)
                    .clip(MaterialTheme.shapes.small)
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .padding(4.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                ModeTab(
                    text = strings.tabSpeak,
                    icon = Icons.Default.Mic,
                    selected = state.mode == VisitViewModel.Mode.VOICE,
                    modifier = Modifier.weight(1f),
                ) { viewModel.setMode(VisitViewModel.Mode.VOICE) }
                ModeTab(
                    text = strings.tabType,
                    icon = Icons.Default.Keyboard,
                    selected = state.mode == VisitViewModel.Mode.TYPE,
                    modifier = Modifier.weight(1f),
                ) { viewModel.setMode(VisitViewModel.Mode.TYPE) }
            }

            Spacer(Modifier.height(16.dp))

            if (state.mode == VisitViewModel.Mode.VOICE) {
                VoiceSection(
                    state = state,
                    onStart = { withMic(viewModel::startListening) },
                    onStop = viewModel::stopListening,
                    onRecord = { withMic(viewModel::startRecording) },
                    onStopRecord = { viewModel.stopRecording() },
                    onDiscardRecord = viewModel::discardRecording,
                    onTranscriptChange = viewModel::onTranscriptChange,
                    onLanguage = viewModel::setLanguage,
                )
            }

            Spacer(Modifier.height(16.dp))

            // Measurements are always available, in both modes: a worker
            // speaks the story and types the numbers.
            Column(Modifier.padding(horizontal = 20.dp)) {
                SectionCard {
                    SectionLabel(strings.sectionMeasurements)
                    Spacer(Modifier.height(4.dp))
                    Text(
                        strings.measurementsHint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(12.dp))
                    VITAL_FIELDS.chunked(2).forEach { pair ->
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            pair.forEach { field ->
                                OutlinedTextField(
                                    value = state.vitals[field.key].orEmpty(),
                                    onValueChange = { viewModel.onVitalChange(field.key, it) },
                                    label = { Text(field.label(strings)) },
                                    suffix = { Text(field.suffix) },
                                    isError = state.vitalErrors.containsKey(field.key),
                                    supportingText = state.vitalErrors[field.key]?.let {
                                        { Text(it) }
                                    },
                                    singleLine = true,
                                    shape = MaterialTheme.shapes.small,
                                    keyboardOptions = KeyboardOptions(
                                        keyboardType = KeyboardType.Decimal
                                    ),
                                    modifier = Modifier.weight(1f),
                                )
                            }
                            if (pair.size == 1) Spacer(Modifier.weight(1f))
                        }
                        Spacer(Modifier.height(8.dp))
                    }
                }

                Spacer(Modifier.height(14.dp))

                SectionCard {
                    SectionLabel(
                        if (state.mode == VisitViewModel.Mode.TYPE) strings.visitNotes
                        else strings.extraNotes
                    )
                    Spacer(Modifier.height(10.dp))
                    OutlinedTextField(
                        value = state.typedNotes,
                        onValueChange = viewModel::onNotesChange,
                        placeholder = {
                            Text(strings.notesPlaceholder)
                        },
                        shape = MaterialTheme.shapes.small,
                        textStyle = MaterialTheme.typography.bodyLarge,
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = if (state.mode == VisitViewModel.Mode.TYPE) 160.dp else 96.dp),
                    )
                }

                if (state.queuedMessage != null) {
                    Spacer(Modifier.height(14.dp))
                    Notice(state.queuedMessage!!, tone = NoticeTone.OFFLINE)
                    Spacer(Modifier.height(10.dp))
                    Button(
                        onClick = onDone,
                        modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp),
                        shape = MaterialTheme.shapes.small,
                    ) { Text(strings.done, style = MaterialTheme.typography.labelLarge) }
                }

                if (state.error != null) {
                    Spacer(Modifier.height(14.dp))
                    Notice(state.error!!, tone = NoticeTone.WARNING)
                }

                Spacer(Modifier.height(20.dp))

                if (state.queuedMessage == null) {
                    Button(
                        onClick = viewModel::submit,
                        enabled = state.hasContent && !state.submitting,
                        shape = MaterialTheme.shapes.small,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                        ),
                        modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
                    ) {
                        if (state.submitting) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp,
                                color = MaterialTheme.colorScheme.onPrimary,
                            )
                            Spacer(Modifier.width(12.dp))
                            Text(strings.analysing, style = MaterialTheme.typography.labelLarge)
                        } else {
                            Text(strings.saveVisit, style = MaterialTheme.typography.labelLarge)
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Text(
                        strings.offlineSaveHint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }

                Spacer(Modifier.height(40.dp))
            }
        }
    }
}

@Composable
private fun ModeTab(
    text: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Row(
        modifier
            .clip(MaterialTheme.shapes.extraSmall)
            .background(
                if (selected) MaterialTheme.colorScheme.surface else Color.Transparent
            )
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            icon,
            contentDescription = null,
            modifier = Modifier.size(18.dp),
            tint = if (selected) MaterialTheme.colorScheme.primary
            else MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.width(8.dp))
        Text(
            text,
            style = MaterialTheme.typography.labelLarge,
            color = if (selected) MaterialTheme.colorScheme.onSurface
            else MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun VoiceSection(
    state: VisitViewModel.State,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onRecord: () -> Unit,
    onStopRecord: () -> Unit,
    onDiscardRecord: () -> Unit,
    onTranscriptChange: (String) -> Unit,
    onLanguage: (String) -> Unit,
) {
    val strings = LocalStrings.current
    Column(Modifier.padding(horizontal = 20.dp)) {

        // Language choice sits next to the mic, because it changes what the
        // recogniser listens for and the worker may switch per household.
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("hi" to "हिन्दी", "en" to "English").forEach { (code, label) ->
                val selected = state.language == code
                Box(
                    Modifier
                        .clip(CircleShape)
                        .background(
                            if (selected) MaterialTheme.colorScheme.primaryContainer
                            else Color.Transparent
                        )
                        .border(
                            1.dp,
                            if (selected) Color.Transparent
                            else MaterialTheme.colorScheme.outline,
                            CircleShape,
                        )
                        .clickable { onLanguage(code) }
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                ) {
                    Text(
                        label,
                        style = MaterialTheme.typography.labelMedium,
                        color = if (selected) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        Spacer(Modifier.height(20.dp))

        // --- The mic ---------------------------------------------------------
        val active = state.listening || state.recordingAudio
        val pulse by animateFloatAsState(
            targetValue = if (active) 1f + state.amplitude * 0.22f else 1f,
            label = "micPulse",
        )

        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Box(
                Modifier
                    .scale(pulse)
                    .size(112.dp)
                    .clip(CircleShape)
                    .background(
                        when {
                            state.recordingAudio -> MaterialTheme.colorScheme.error
                            state.listening -> MaterialTheme.colorScheme.primary
                            else -> MaterialTheme.colorScheme.primaryContainer
                        }
                    )
                    .clickable {
                        when {
                            state.recordingAudio -> onStopRecord()
                            state.listening -> onStop()
                            else -> onStart()
                        }
                    },
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    when {
                        state.recordingAudio -> Icons.Default.Stop
                        state.listening -> Icons.Default.Stop
                        else -> Icons.Default.Mic
                    },
                    contentDescription = if (active) strings.tabSpeak else strings.micPrompt,
                    modifier = Modifier.size(44.dp),
                    tint = if (active) MaterialTheme.colorScheme.onPrimary
                    else MaterialTheme.colorScheme.primary,
                )
            }
        }

        Spacer(Modifier.height(14.dp))

        Text(
            when {
                state.recordingAudio ->
                    strings.micRecording(state.recordedMs / 1000)
                state.listening -> strings.micListening
                state.transcript.isNotBlank() -> strings.micTapToAdd
                else -> strings.micPrompt
            },
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )

        if (state.partial.isNotBlank()) {
            Spacer(Modifier.height(12.dp))
            Text(
                state.partial,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        if (state.speechError != null) {
            Spacer(Modifier.height(14.dp))
            Notice(state.speechError!!, tone = NoticeTone.WARNING)
        }

        // --- Offline recording ----------------------------------------------
        Spacer(Modifier.height(16.dp))
        if (state.recordedMs > 0 && !state.recordingAudio) {
            SectionCard(accent = MaterialTheme.colorScheme.primary) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Default.FiberManualRecord,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.error,
                        modifier = Modifier.size(14.dp),
                    )
                    Spacer(Modifier.width(10.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            strings.recordingSaved(state.recordedMs / 1000),
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium,
                        )
                        Text(
                            strings.recordingSavedHint,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    IconButton(onClick = onDiscardRecord) {
                        Icon(Icons.Default.Delete, contentDescription = strings.discardRecording)
                    }
                }
            }
        } else if (!state.recordingAudio) {
            OutlinedButton(
                onClick = onRecord,
                shape = MaterialTheme.shapes.small,
                modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
            ) {
                Icon(Icons.Default.FiberManualRecord, contentDescription = null,
                    modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(10.dp))
                Text(strings.recordForLater, style = MaterialTheme.typography.labelLarge)
            }
            Spacer(Modifier.height(6.dp))
            Text(
                strings.recordForLaterHint,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        // --- Editable transcript ---------------------------------------------
        if (state.transcript.isNotBlank()) {
            Spacer(Modifier.height(18.dp))
            SectionCard {
                SectionLabel(strings.whatWasHeard)
                Spacer(Modifier.height(4.dp))
                Text(
                    strings.whatWasHeardHint,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = state.transcript,
                    onValueChange = onTranscriptChange,
                    shape = MaterialTheme.shapes.small,
                    textStyle = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.fillMaxWidth().heightIn(min = 120.dp),
                )
            }
        }
    }
}
