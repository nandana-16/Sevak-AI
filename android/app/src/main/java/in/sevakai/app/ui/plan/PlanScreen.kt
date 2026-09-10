package `in`.sevakai.app.ui.plan

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.EventAvailable
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.ScheduleRow
import `in`.sevakai.app.ui.components.EmptyState
import `in`.sevakai.app.ui.components.FilterPill
import `in`.sevakai.app.ui.components.LoadingBlock
import `in`.sevakai.app.ui.components.Notice
import `in`.sevakai.app.ui.components.NoticeTone
import `in`.sevakai.app.ui.components.Risk
import `in`.sevakai.app.ui.components.RiskChip
import `in`.sevakai.app.ui.components.SectionCard
import `in`.sevakai.app.ui.i18n.LocalStrings
import `in`.sevakai.app.ui.components.color

@Composable
fun PlanScreen(
    repository: Repository,
    onBack: () -> Unit,
    onOpenPatient: (String) -> Unit,
) {
    val viewModel: PlanViewModel = viewModel(factory = PlanViewModel.factory(repository))
    val state by viewModel.state.collectAsStateWithLifecycle()
    val strings = LocalStrings.current

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
                    Text(strings.visitPlanTitle, style = MaterialTheme.typography.titleMedium)
                    Text(
                        strings.visitPlanSubtitle,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            Row(
                Modifier.padding(horizontal = 20.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                FilterPill(strings.rangeDueNow, state.days == 0, { viewModel.setRange(0) })
                FilterPill(strings.rangeNext7, state.days == 7, { viewModel.setRange(7) })
                FilterPill(strings.rangeNext30, state.days == 30, { viewModel.setRange(30) })
            }

            when {
                state.loading && state.items.isEmpty() -> LoadingBlock(strings.loadingPlan)
                state.items.isEmpty() -> EmptyState(
                    title = strings.nothingScheduled,
                    body = strings.nothingScheduledBody,
                    icon = Icons.Default.EventAvailable,
                )
                else -> {
                    val overdue = state.items.filter { it.overdue }
                    val rest = state.items.filterNot { it.overdue }
                    LazyColumn(
                        contentPadding = PaddingValues(20.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        if (state.fromCache) {
                            item {
                                Notice(
                                    strings.planOffline,
                                    tone = NoticeTone.OFFLINE,
                                )
                            }
                        }
                        if (overdue.isNotEmpty()) {
                            item {
                                Text(
                                    strings.overdueHeading(overdue.size),
                                    style = MaterialTheme.typography.titleSmall,
                                    color = Risk.RED.color(),
                                )
                            }
                            items(overdue, key = { it.id }) {
                                PlanCard(it, onOpenPatient, viewModel::snooze)
                            }
                        }
                        if (rest.isNotEmpty()) {
                            item {
                                Spacer(Modifier.height(4.dp))
                                Text(strings.upcoming, style = MaterialTheme.typography.titleSmall)
                            }
                            items(rest, key = { it.id }) {
                                PlanCard(it, onOpenPatient, viewModel::snooze)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PlanCard(
    row: ScheduleRow,
    onOpen: (String) -> Unit,
    onSnooze: (String) -> Unit,
) {
    val risk = Risk.from(row.priority)
    val strings = LocalStrings.current
    SectionCard(
        onClick = { onOpen(row.patientId) },
        accent = if (row.overdue || risk == Risk.RED) risk.color() else null,
    ) {
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Text(row.patientName, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(2.dp))
                Text(
                    listOfNotNull(row.village, strings.dueOnDate(row.dueDate)).joinToString(" · "),
                    style = MaterialTheme.typography.bodySmall,
                    color = if (row.overdue) risk.color()
                    else MaterialTheme.colorScheme.onSurfaceVariant,
                    fontWeight = if (row.overdue) FontWeight.Medium else FontWeight.Normal,
                )
            }
            RiskChip(risk)
        }
        Spacer(Modifier.height(8.dp))
        Text(
            row.reason,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        // A high-risk follow-up has no snooze: the server refuses it, so the
        // button is not offered in the first place.
        if (risk != Risk.RED) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                TextButton(onClick = { onSnooze(row.id) }) {
                    Text(strings.snoozeOneDay,
                        style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
}
