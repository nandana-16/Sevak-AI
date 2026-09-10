package `in`.sevakai.app.ui.queue

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CloudDone
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.local.PendingVisit
import `in`.sevakai.app.data.local.QueueStatus
import `in`.sevakai.app.ui.components.EmptyState
import `in`.sevakai.app.ui.components.Notice
import `in`.sevakai.app.ui.components.NoticeTone
import `in`.sevakai.app.ui.components.Risk
import `in`.sevakai.app.ui.components.RiskChip
import `in`.sevakai.app.ui.components.SectionCard
import `in`.sevakai.app.ui.i18n.LocalStrings
import `in`.sevakai.app.ui.components.color
import `in`.sevakai.app.ui.theme.LocalRiskPalette
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * The offline queue, made visible.
 *
 * A worker who recorded six visits in a dead zone needs to be able to confirm
 * that all six are still there and see them go up. A silent background queue
 * would be technically fine and completely untrustworthy.
 */
@Composable
fun QueueScreen(repository: Repository, onBack: () -> Unit) {
    val viewModel: QueueViewModel = viewModel(factory = QueueViewModel.factory(repository))
    val items by viewModel.items.collectAsStateWithLifecycle()
    val syncing by viewModel.syncing.collectAsStateWithLifecycle()
    val strings = LocalStrings.current

    val waiting = items.count { it.status != QueueStatus.SYNCED }

    Scaffold(containerColor = MaterialTheme.colorScheme.background) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            Row(
                Modifier.fillMaxWidth().padding(start = 4.dp, end = 20.dp, top = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = strings.back)
                }
                Column(Modifier.weight(1f)) {
                    Text(strings.queueTitle, style = MaterialTheme.typography.titleMedium)
                    Text(
                        if (waiting == 0) strings.queueAllSent
                        else strings.queueWaiting(waiting),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            if (items.isEmpty()) {
                EmptyState(
                    title = strings.queueNothingWaiting,
                    body = strings.queueNothingWaitingBody,
                    icon = Icons.Default.CloudDone,
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(20.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    item {
                        Notice(
                            strings.queueExplainer,
                            tone = NoticeTone.INFO,
                        )
                    }
                    if (waiting > 0) {
                        item {
                            OutlinedButton(
                                onClick = viewModel::syncNow,
                                enabled = !syncing,
                                shape = MaterialTheme.shapes.small,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text(
                                    if (syncing) strings.sending else strings.trySendingNow,
                                    style = MaterialTheme.typography.labelLarge,
                                )
                            }
                        }
                    }
                    items(items, key = { it.clientUuid }) { QueueCard(it) }
                }
            }
        }
    }
}

@Composable
private fun QueueCard(item: PendingVisit) {
    val palette = LocalRiskPalette.current
    val strings = LocalStrings.current
    val (statusText, statusColor) = when (item.status) {
        QueueStatus.PENDING -> strings.statusWaiting to palette.grey
        QueueStatus.UPLOADING -> strings.statusSending to MaterialTheme.colorScheme.primary
        QueueStatus.SYNCED -> strings.statusSent to palette.green
        QueueStatus.FAILED -> strings.statusWillRetry to palette.amber
    }

    SectionCard(accent = if (item.status == QueueStatus.SYNCED) null else statusColor) {
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Text(
                    item.patientName.ifBlank { strings.recordVisitTitle },
                    style = MaterialTheme.typography.titleMedium,
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    formatTime(item.createdAt),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    Modifier.size(8.dp).clip(CircleShape).background(statusColor)
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    statusText,
                    style = MaterialTheme.typography.labelMedium,
                    color = statusColor,
                )
            }
        }

        Spacer(Modifier.height(8.dp))
        Text(
            when {
                item.audioPath != null && item.transcript.isNullOrBlank() ->
                    strings.queueVoiceRecording
                !item.transcript.isNullOrBlank() -> "\"${item.transcript!!.take(110)}\""
                !item.typedNotes.isNullOrBlank() -> item.typedNotes!!.take(110)
                else -> strings.queueMeasurementsOnly
            },
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        // Once it lands, show what came back so the worker sees the outcome
        // for a visit they recorded hours earlier in a dead zone.
        if (item.status == QueueStatus.SYNCED && item.resultRisk != null) {
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                RiskChip(Risk.from(item.resultRisk))
                Spacer(Modifier.width(10.dp))
                item.resultSummary?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        if (item.status == QueueStatus.FAILED && item.lastError != null) {
            Spacer(Modifier.height(8.dp))
            Text(
                strings.attemptLabel(item.attempts, item.lastError!!),
                style = MaterialTheme.typography.bodySmall,
                color = palette.amber,
            )
        }
    }
}

private fun formatTime(millis: Long): String =
    SimpleDateFormat("d MMM, h:mm a", Locale.getDefault()).format(Date(millis))
