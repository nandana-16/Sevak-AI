package `in`.sevakai.app.ui.roster

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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.CloudQueue
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.PersonSearch
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.sevakai.app.data.PatientRow
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.ui.components.EmptyState
import `in`.sevakai.app.ui.components.FilterPill
import `in`.sevakai.app.ui.components.LoadingBlock
import `in`.sevakai.app.ui.components.Notice
import `in`.sevakai.app.ui.components.NoticeTone
import `in`.sevakai.app.ui.components.Risk
import `in`.sevakai.app.ui.components.RiskChip
import `in`.sevakai.app.ui.components.SectionCard
import `in`.sevakai.app.ui.components.color
import `in`.sevakai.app.ui.components.tint

private val CATEGORIES = listOf(
    "pregnant" to "Pregnant",
    "infant" to "Infants",
    "child" to "Children",
    "postnatal" to "Postnatal",
    "adult" to "Adults",
    "elderly" to "Elderly",
)

@Composable
fun RosterScreen(
    repository: Repository,
    onOpenPatient: (String) -> Unit,
    onOpenPlan: () -> Unit,
    onOpenQueue: () -> Unit,
    onRegister: () -> Unit,
    onOpenServerSettings: () -> Unit,
) {
    val viewModel: RosterViewModel = viewModel(factory = RosterViewModel.factory(repository))
    val state by viewModel.state.collectAsStateWithLifecycle()
    val queued by viewModel.unsyncedCount.collectAsStateWithLifecycle()

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = onRegister,
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                shape = MaterialTheme.shapes.small,
            ) {
                Icon(Icons.Default.Add, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Register", style = MaterialTheme.typography.labelLarge)
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {

            // --- Header ------------------------------------------------------
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(start = 20.dp, end = 8.dp, top = 12.dp, bottom = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        "My patients",
                        style = MaterialTheme.typography.headlineMedium,
                    )
                    Text(
                        listOfNotNull(
                            state.workerName.takeIf { it.isNotBlank() },
                            state.village,
                        ).joinToString(" · "),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                IconButton(onClick = onOpenPlan) {
                    Icon(Icons.Default.CalendarMonth, contentDescription = "Visit plan")
                }
                Box {
                    IconButton(onClick = onOpenQueue) {
                        Icon(Icons.Default.CloudQueue, contentDescription = "Sync queue")
                    }
                    if (queued > 0) {
                        Box(
                            Modifier
                                .align(Alignment.TopEnd)
                                .padding(6.dp)
                                .size(18.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primary),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                queued.toString(),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onPrimary,
                            )
                        }
                    }
                }
                IconButton(onClick = onOpenServerSettings) {
                    Icon(Icons.Default.Dns, contentDescription = "Server settings")
                }
                IconButton(onClick = viewModel::signOut) {
                    Icon(Icons.Default.Logout, contentDescription = "Sign out")
                }
            }

            // --- Search ------------------------------------------------------
            OutlinedTextField(
                value = state.filters.search,
                onValueChange = viewModel::onSearchChange,
                placeholder = { Text("Search by name or village") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                singleLine = true,
                shape = MaterialTheme.shapes.small,
                textStyle = MaterialTheme.typography.bodyLarge,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 8.dp),
            )

            // --- Filters -----------------------------------------------------
            LazyRow(
                contentPadding = PaddingValues(horizontal = 20.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.padding(vertical = 4.dp),
            ) {
                item {
                    FilterPill(
                        text = "Due now",
                        selected = state.filters.dueOnly,
                        onClick = viewModel::toggleDueOnly,
                    )
                }
                item {
                    FilterPill(
                        text = "High risk",
                        selected = state.filters.risk == "red",
                        onClick = { viewModel.toggleRisk("red") },
                        accent = Risk.RED.color(),
                    )
                }
                item {
                    FilterPill(
                        text = "Watch",
                        selected = state.filters.risk == "yellow",
                        onClick = { viewModel.toggleRisk("yellow") },
                        accent = Risk.AMBER.color(),
                    )
                }
                items(CATEGORIES) { (key, label) ->
                    FilterPill(
                        text = label,
                        selected = state.filters.category == key,
                        onClick = { viewModel.toggleCategory(key) },
                    )
                }
                if (state.villages.size > 1) {
                    items(state.villages) { village ->
                        FilterPill(
                            text = village,
                            selected = state.filters.village == village,
                            onClick = { viewModel.toggleVillage(village) },
                        )
                    }
                }
            }

            // --- Content -----------------------------------------------------
            when {
                state.loading && state.patients.isEmpty() ->
                    LoadingBlock("Loading your patients…")

                state.patients.isEmpty() -> EmptyState(
                    title = if (state.filters.activeCount > 0 || state.filters.search.isNotBlank())
                        "No matching patients" else "No patients assigned yet",
                    body = if (state.filters.activeCount > 0 || state.filters.search.isNotBlank())
                        "Try clearing the filters or searching a different name."
                    else "Patients assigned to you by your ANM will appear here.",
                    icon = Icons.Default.PersonSearch,
                )

                else -> LazyColumn(
                    contentPadding = PaddingValues(
                        start = 20.dp, end = 20.dp, top = 8.dp, bottom = 96.dp,
                    ),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    if (state.fromCache) {
                        item {
                            Notice(
                                "You are offline. Showing the last saved copy of your roster.",
                                tone = NoticeTone.OFFLINE,
                            )
                        }
                    }
                    item {
                        Text(
                            "${state.patients.size} patient${if (state.patients.size == 1) "" else "s"}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    items(state.patients, key = { it.id }) { patient ->
                        PatientCard(patient) { onOpenPatient(patient.id) }
                    }
                }
            }
        }
    }
}

@Composable
private fun PatientCard(patient: PatientRow, onClick: () -> Unit) {
    val risk = Risk.from(patient.risk)
    SectionCard(
        onClick = onClick,
        // A red patient gets a coloured edge, so the list can be scanned for
        // urgency without reading a word.
        accent = if (risk == Risk.RED || risk == Risk.AMBER) risk.color() else null,
    ) {
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Text(patient.name, style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(2.dp))
                Text(
                    listOfNotNull(
                        patient.ageLabel.takeIf { it.isNotBlank() },
                        categoryLabel(patient.category),
                        patient.village,
                    ).joinToString(" · "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            RiskChip(risk)
        }

        // The last-visit note: what the worker needs before knocking.
        if (!patient.lastVisitSummary.isNullOrBlank()) {
            Spacer(Modifier.height(10.dp))
            Box(
                Modifier
                    .fillMaxWidth()
                    .clip(MaterialTheme.shapes.extraSmall)
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .padding(10.dp)
            ) {
                Text(
                    "Last visit: ${patient.lastVisitSummary}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        if (patient.nextVisitDue != null) {
            Spacer(Modifier.height(8.dp))
            Text(
                "Next visit due ${patient.nextVisitDue}",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Medium,
            )
        }
    }
}

internal fun categoryLabel(category: String): String = when (category) {
    "pregnant" -> "Pregnant"
    "infant" -> "Infant"
    "child" -> "Child"
    "postnatal" -> "Postnatal"
    "elderly" -> "Elderly"
    else -> "Adult"
}
