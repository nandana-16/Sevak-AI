package `in`.sevakai.app.ui.visit

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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.Button
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.remote.VisitDetailDto
import `in`.sevakai.app.ui.components.EmptyState
import `in`.sevakai.app.ui.components.LoadingBlock
import `in`.sevakai.app.ui.components.Notice
import `in`.sevakai.app.ui.components.NoticeTone
import `in`.sevakai.app.ui.components.Risk
import `in`.sevakai.app.ui.components.SectionCard
import `in`.sevakai.app.ui.components.SectionLabel
import `in`.sevakai.app.ui.i18n.LocalStrings
import `in`.sevakai.app.ui.components.color
import `in`.sevakai.app.ui.components.label
import `in`.sevakai.app.ui.components.tint

@Composable
fun VisitResultScreen(
    repository: Repository,
    visitId: String,
    onBack: () -> Unit,
) {
    var visit by remember { mutableStateOf<VisitDetailDto?>(null) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    val strings = LocalStrings.current

    LaunchedEffect(visitId) {
        repository.visit(visitId)
            .onSuccess { visit = it }
            .onFailure { error = it.message }
        loading = false
    }

    Scaffold(containerColor = MaterialTheme.colorScheme.background) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            Row(
                Modifier.fillMaxWidth().padding(start = 4.dp, end = 20.dp, top = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = strings.back)
                }
                Text(strings.visitResult, style = MaterialTheme.typography.titleMedium)
            }
            when {
                loading -> LoadingBlock()
                visit == null -> EmptyState(
                    title = strings.couldNotLoadVisit,
                    body = error ?: strings.couldNotLoadVisitBody,
                )
                else -> VisitResultBody(visit = visit!!, onDone = null)
            }
        }
    }
}

/**
 * The result view.
 *
 * Order is deliberate: what to do, then why, then the evidence. A worker
 * standing in someone's doorway needs the action first; the guideline text is
 * there to justify it when a family asks "says who?", and it is collapsed by
 * default so it never gets in the way of the action.
 */
@Composable
fun VisitResultBody(
    visit: VisitDetailDto,
    onDone: (() -> Unit)?,
) {
    val risk = Risk.from(visit.riskLevel)
    val strings = LocalStrings.current

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        // --- Verdict --------------------------------------------------------
        item {
            Box(
                Modifier
                    .fillMaxWidth()
                    .clip(MaterialTheme.shapes.medium)
                    .background(risk.tint())
                    .padding(20.dp)
            ) {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            Modifier
                                .size(14.dp)
                                .clip(CircleShape)
                                .background(risk.color())
                        )
                        Spacer(Modifier.width(10.dp))
                        Text(
                            risk.label(),
                            style = MaterialTheme.typography.headlineSmall,
                            color = risk.color(),
                            fontWeight = FontWeight.Bold,
                        )
                    }
                    if (!visit.riskRationale.isNullOrBlank()) {
                        Spacer(Modifier.height(10.dp))
                        Text(
                            visit.riskRationale!!,
                            style = MaterialTheme.typography.bodyLarge,
                        )
                    }
                }
            }
        }

        // Honesty about how the answer was produced.
        if (visit.degradedSteps.isNotEmpty()) {
            item {
                Notice(
                    strings.degradedWarning(visit.degradedSteps.joinToString("; ")),
                    tone = NoticeTone.WARNING,
                )
            }
        }

        if (visit.status == "failed") {
            item {
                Notice(
                    visit.errorMessage ?: strings.visitFailed,
                    tone = NoticeTone.WARNING,
                )
            }
        }

        // --- Danger signs ---------------------------------------------------
        if (visit.dangerSigns.isNotEmpty()) {
            item {
                SectionCard(accent = risk.color()) {
                    SectionLabel(strings.dangerSignsFound)
                    Spacer(Modifier.height(10.dp))
                    visit.dangerSigns.forEach { sign ->
                        Row(
                            Modifier.padding(vertical = 4.dp),
                            verticalAlignment = Alignment.Top,
                        ) {
                            Box(
                                Modifier
                                    .padding(top = 7.dp)
                                    .size(6.dp)
                                    .clip(CircleShape)
                                    .background(risk.color())
                            )
                            Spacer(Modifier.width(10.dp))
                            Text(sign, style = MaterialTheme.typography.bodyLarge)
                        }
                    }
                }
            }
        }

        // --- Actions --------------------------------------------------------
        if (visit.actions.isNotEmpty()) {
            item {
                SectionCard {
                    SectionLabel(strings.whatToDoNow)
                    Spacer(Modifier.height(12.dp))
                    visit.actions.forEachIndexed { index, action ->
                        Row(Modifier.padding(vertical = 6.dp), verticalAlignment = Alignment.Top) {
                            Box(
                                Modifier
                                    .size(24.dp)
                                    .clip(CircleShape)
                                    .background(MaterialTheme.colorScheme.primaryContainer),
                                contentAlignment = Alignment.Center,
                            ) {
                                Text(
                                    "${index + 1}",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                            }
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(action.action, style = MaterialTheme.typography.bodyLarge)
                                Text(
                                    urgencyLabel(action.urgency),
                                    style = MaterialTheme.typography.labelMedium,
                                    color = urgencyColor(action.urgency),
                                )
                            }
                        }
                    }
                }
            }
        }

        // --- Follow-up ------------------------------------------------------
        if (visit.nextVisitDue != null) {
            item {
                SectionCard(accent = MaterialTheme.colorScheme.primary) {
                    SectionLabel(strings.nextVisit)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        visit.nextVisitDue!!,
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    Spacer(Modifier.height(4.dp))
                    Text(
                        strings.nextVisitAuto,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        // --- What was recorded ----------------------------------------------
        item {
            SectionCard {
                SectionLabel(strings.recordedInThisVisit)
                Spacer(Modifier.height(10.dp))
                val vitals = buildList {
                    visit.temperatureC?.let { add(strings.vitalTemperature to "$it °C") }
                    visit.bpSystolic?.let { add("BP" to "$it/${visit.bpDiastolic ?: "-"}") }
                    visit.pulse?.let { add(strings.vitalPulse to "$it /min") }
                    visit.hb?.let { add("Hb" to "$it g/dL") }
                    visit.spo2?.let { add("SpO₂" to "$it %") }
                    visit.weightKg?.let { add(strings.vitalWeight to "$it kg") }
                }
                if (visit.symptoms.isNotEmpty()) {
                    Text(
                        visit.symptoms.joinToString(", ") {
                            it.replaceFirstChar(Char::uppercase)
                        },
                        style = MaterialTheme.typography.bodyLarge,
                    )
                    Spacer(Modifier.height(10.dp))
                }
                vitals.forEach { (label, value) ->
                    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp)) {
                        Text(
                            label,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.weight(1f),
                        )
                        Text(
                            value,
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium,
                        )
                    }
                }
                if (visit.symptoms.isEmpty() && vitals.isEmpty()) {
                    Text(
                        strings.noFindings,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }

        // --- Evidence -------------------------------------------------------
        if (visit.citations.isNotEmpty()) {
            item {
                var expanded by remember { mutableStateOf(false) }
                SectionCard {
                    Row(
                        Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(Modifier.weight(1f)) {
                            SectionLabel(strings.basedOnGuidelines)
                            Spacer(Modifier.height(4.dp))
                            Text(
                                strings.passagesCount(visit.citations.size),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        IconButton(onClick = { expanded = !expanded }) {
                            Icon(
                                if (expanded) Icons.Default.ExpandLess
                                else Icons.Default.ExpandMore,
                                contentDescription = if (expanded) strings.hide else strings.show,
                            )
                        }
                    }
                    if (expanded) {
                        Spacer(Modifier.height(10.dp))
                        visit.citations.forEach { citation ->
                            Column(Modifier.padding(vertical = 8.dp)) {
                                Text(
                                    "${citation.title} · ${strings.pageLabel(citation.page)}",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    citation.text,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                    }
                }
            }
        }

        if (onDone != null) {
            item {
                Spacer(Modifier.height(4.dp))
                Button(
                    onClick = onDone,
                    shape = MaterialTheme.shapes.small,
                    modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
                ) {
                    Text(strings.done, style = MaterialTheme.typography.labelLarge)
                }
                Spacer(Modifier.height(24.dp))
            }
        }
    }
}

@Composable
private fun urgencyLabel(urgency: String): String = with(LocalStrings.current) {
    when (urgency) {
        "now" -> urgencyNow
        "today" -> urgencyToday
        "this_week" -> urgencyThisWeek
        else -> urgencyRoutine
    }
}

@Composable
private fun urgencyColor(urgency: String) = when (urgency) {
    "now" -> Risk.RED.color()
    "today" -> Risk.AMBER.color()
    else -> MaterialTheme.colorScheme.onSurfaceVariant
}
