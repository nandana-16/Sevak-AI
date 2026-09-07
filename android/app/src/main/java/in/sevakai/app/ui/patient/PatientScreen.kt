package `in`.sevakai.app.ui.patient

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
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.remote.PatientDetailDto
import `in`.sevakai.app.data.remote.VaccinationDto
import `in`.sevakai.app.ui.components.Divider
import `in`.sevakai.app.ui.components.EmptyState
import `in`.sevakai.app.ui.components.LabelledValue
import `in`.sevakai.app.ui.components.LoadingBlock
import `in`.sevakai.app.ui.components.Notice
import `in`.sevakai.app.ui.components.NoticeTone
import `in`.sevakai.app.ui.components.Risk
import `in`.sevakai.app.ui.components.RiskChip
import `in`.sevakai.app.ui.components.SectionCard
import `in`.sevakai.app.ui.components.SectionLabel
import `in`.sevakai.app.ui.components.color
import `in`.sevakai.app.ui.components.tint
import `in`.sevakai.app.ui.roster.categoryLabel

@Composable
fun PatientScreen(
    repository: Repository,
    patientId: String,
    onBack: () -> Unit,
    onRecordVisit: (String) -> Unit,
    onOpenVisit: (String) -> Unit,
) {
    val viewModel: PatientViewModel = viewModel(
        factory = PatientViewModel.factory(repository, patientId)
    )
    val state by viewModel.state.collectAsStateWithLifecycle()

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
            if (state.patient != null) {
                ExtendedFloatingActionButton(
                    onClick = { onRecordVisit(patientId) },
                    containerColor = MaterialTheme.colorScheme.primary,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                    shape = MaterialTheme.shapes.small,
                ) {
                    Icon(Icons.Default.Mic, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Record visit", style = MaterialTheme.typography.labelLarge)
                }
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            Row(
                Modifier.fillMaxWidth().padding(start = 4.dp, end = 20.dp, top = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                }
                Text("Patient profile", style = MaterialTheme.typography.titleMedium)
            }

            when {
                state.loading && state.patient == null -> LoadingBlock("Opening profile…")
                state.patient == null -> EmptyState(
                    title = "Could not open this profile",
                    body = state.error ?: "Please try again when you have a connection.",
                )
                else -> PatientBody(
                    patient = state.patient!!,
                    fromCache = state.fromCache,
                    onOpenVisit = onOpenVisit,
                    onMarkGiven = viewModel::markVaccinationGiven,
                )
            }
        }
    }
}

@Composable
private fun PatientBody(
    patient: PatientDetailDto,
    fromCache: Boolean,
    onOpenVisit: (String) -> Unit,
    onMarkGiven: (String) -> Unit,
) {
    val risk = Risk.from(patient.currentRisk)

    LazyColumn(
        contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 100.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        if (fromCache) {
            item {
                Notice(
                    "Offline — showing the copy saved on this phone.",
                    tone = NoticeTone.OFFLINE,
                )
            }
        }

        // --- Identity -------------------------------------------------------
        item {
            Column {
                Text(patient.name, style = MaterialTheme.typography.headlineMedium)
                Spacer(Modifier.height(4.dp))
                Text(
                    listOfNotNull(
                        patient.ageLabel.takeIf { it.isNotBlank() },
                        patient.gender.replaceFirstChar(Char::uppercase),
                        categoryLabel(patient.category),
                        patient.village,
                    ).joinToString(" · "),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(10.dp))
                RiskChip(risk, expanded = true)
            }
        }

        // --- Last visit, right at the top where it is useful ----------------
        if (!patient.lastVisitSummary.isNullOrBlank()) {
            item {
                SectionCard(accent = MaterialTheme.colorScheme.primary) {
                    SectionLabel("Last visit")
                    Spacer(Modifier.height(6.dp))
                    Text(patient.lastVisitSummary!!, style = MaterialTheme.typography.bodyLarge)
                    if (patient.lastVisitAt != null) {
                        Spacer(Modifier.height(6.dp))
                        Text(
                            patient.lastVisitAt!!.take(10),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }

        if (patient.nextVisitDue != null) {
            item {
                Notice("Next visit due ${patient.nextVisitDue}", tone = NoticeTone.INFO)
            }
        }

        // --- Basic details --------------------------------------------------
        item {
            SectionCard {
                SectionLabel("Details")
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    LabelledValue("Date of birth", patient.dob, Modifier.weight(1f))
                    LabelledValue("Blood group", patient.bloodGroup, Modifier.weight(1f))
                }
                Spacer(Modifier.height(14.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    LabelledValue("Phone", patient.phone, Modifier.weight(1f))
                    LabelledValue("Household", patient.householdId, Modifier.weight(1f))
                }
                if (!patient.guardianName.isNullOrBlank()) {
                    Spacer(Modifier.height(14.dp))
                    LabelledValue("Guardian", patient.guardianName)
                }
                if (!patient.address.isNullOrBlank()) {
                    Spacer(Modifier.height(14.dp))
                    LabelledValue("Address", patient.address)
                }
                Spacer(Modifier.height(14.dp))
                Divider()
                Spacer(Modifier.height(12.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        if (patient.aadhaarVerified) Icons.Default.VerifiedUser
                        else Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = if (patient.aadhaarVerified) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.width(8.dp))
                    Column {
                        Text(
                            "Aadhaar ${patient.aadhaarMasked}",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Text(
                            if (patient.aadhaarVerified)
                                "Verified offline at registration"
                            else "Not linked",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }

        // --- Pregnancy ------------------------------------------------------
        patient.pregnancy?.let { pregnancy ->
            item {
                SectionCard {
                    SectionLabel("Pregnancy")
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        LabelledValue(
                            "Gestation",
                            pregnancy.gestationWeeks?.let { "$it weeks" },
                            Modifier.weight(1f),
                        )
                        LabelledValue("Due date", pregnancy.edd, Modifier.weight(1f))
                    }
                    Spacer(Modifier.height(14.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        LabelledValue(
                            "Gravida / Para",
                            "G${pregnancy.gravida ?: "-"} P${pregnancy.para ?: "-"}",
                            Modifier.weight(1f),
                        )
                        LabelledValue(
                            "ANC visits",
                            "${pregnancy.ancVisitsCompleted} of 4",
                            Modifier.weight(1f),
                        )
                    }
                    Spacer(Modifier.height(14.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        LabelledValue(
                            "Last Hb",
                            pregnancy.lastHb?.let { "$it g/dL" },
                            Modifier.weight(1f),
                        )
                        LabelledValue(
                            "Last BP",
                            pregnancy.lastBpSystolic?.let {
                                "$it/${pregnancy.lastBpDiastolic ?: "-"}"
                            },
                            Modifier.weight(1f),
                        )
                    }
                    Spacer(Modifier.height(14.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        LabelledValue("TT doses", pregnancy.ttDoses.toString(), Modifier.weight(1f))
                        LabelledValue(
                            "IFA tablets",
                            pregnancy.ifaTabletsGiven.toString(),
                            Modifier.weight(1f),
                        )
                    }
                    if (!pregnancy.plannedDeliveryPlace.isNullOrBlank()) {
                        Spacer(Modifier.height(14.dp))
                        LabelledValue("Planned delivery", pregnancy.plannedDeliveryPlace)
                    }
                    if (pregnancy.highRiskFactors.isNotEmpty()) {
                        Spacer(Modifier.height(14.dp))
                        SectionLabel("High-risk factors")
                        Spacer(Modifier.height(8.dp))
                        pregnancy.highRiskFactors.forEach { factor ->
                            Row(
                                Modifier.padding(vertical = 3.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Box(
                                    Modifier
                                        .size(6.dp)
                                        .clip(CircleShape)
                                        .background(Risk.AMBER.color())
                                )
                                Spacer(Modifier.width(10.dp))
                                Text(factor, style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                }
            }
        }

        // --- Infant ---------------------------------------------------------
        patient.infant?.let { infant ->
            item {
                SectionCard {
                    SectionLabel("Newborn details")
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        LabelledValue(
                            "Birth weight",
                            infant.birthWeightKg?.let { "$it kg" },
                            Modifier.weight(1f),
                        )
                        LabelledValue(
                            "Born at",
                            infant.gestationWeeks?.let { "$it weeks" },
                            Modifier.weight(1f),
                        )
                    }
                    Spacer(Modifier.height(14.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        LabelledValue(
                            "Current weight",
                            infant.lastWeightKg?.let { "$it kg" },
                            Modifier.weight(1f),
                        )
                        LabelledValue(
                            "MUAC",
                            infant.lastMuacCm?.let { "$it cm" },
                            Modifier.weight(1f),
                        )
                    }
                    Spacer(Modifier.height(14.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        LabelledValue("Delivery", infant.deliveryType, Modifier.weight(1f))
                        LabelledValue(
                            "Feeding",
                            infant.exclusiveBreastfeeding?.let {
                                if (it) "Exclusive breastfeeding" else "Mixed feeding"
                            },
                            Modifier.weight(1f),
                        )
                    }
                }
            }
        }

        // --- Immunisation ---------------------------------------------------
        if (patient.vaccinations.isNotEmpty()) {
            val overdue = patient.vaccinations.filter { it.overdue }
            val upcoming = patient.vaccinations.filter { !it.given && !it.overdue }.take(4)
            val done = patient.vaccinations.count { it.given }

            item {
                SectionCard(accent = if (overdue.isNotEmpty()) Risk.AMBER.color() else null) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        SectionLabel("Immunisation", Modifier.weight(1f))
                        Text(
                            "$done given",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    if (overdue.isNotEmpty()) {
                        Spacer(Modifier.height(12.dp))
                        Text(
                            "${overdue.size} overdue",
                            style = MaterialTheme.typography.titleSmall,
                            color = Risk.AMBER.color(),
                        )
                        Spacer(Modifier.height(6.dp))
                        overdue.forEach { VaccinationRow(it, onMarkGiven) }
                    }
                    if (upcoming.isNotEmpty()) {
                        Spacer(Modifier.height(12.dp))
                        Text(
                            "Coming up",
                            style = MaterialTheme.typography.titleSmall,
                        )
                        Spacer(Modifier.height(6.dp))
                        upcoming.forEach { VaccinationRow(it, onMarkGiven) }
                    }
                    if (overdue.isEmpty() && upcoming.isEmpty()) {
                        Spacer(Modifier.height(10.dp))
                        Text(
                            "Immunisation schedule is complete.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }

        // --- History --------------------------------------------------------
        if (patient.conditions.isNotEmpty()) {
            item {
                SectionCard {
                    SectionLabel("Medical history")
                    Spacer(Modifier.height(10.dp))
                    val ongoing = patient.conditions.filter { it.ongoing }
                    val past = patient.conditions.filter { !it.ongoing }
                    if (ongoing.isNotEmpty()) {
                        Text("Ongoing", style = MaterialTheme.typography.titleSmall)
                        Spacer(Modifier.height(4.dp))
                        ongoing.forEach {
                            Text(
                                "• ${it.name}${it.diagnosedOn?.let { d -> "  (since $d)" }.orEmpty()}",
                                style = MaterialTheme.typography.bodyMedium,
                                modifier = Modifier.padding(vertical = 2.dp),
                            )
                        }
                    }
                    if (past.isNotEmpty()) {
                        Spacer(Modifier.height(10.dp))
                        Text("Past", style = MaterialTheme.typography.titleSmall)
                        Spacer(Modifier.height(4.dp))
                        past.forEach {
                            Text(
                                "• ${it.name}",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(vertical = 2.dp),
                            )
                        }
                    }
                }
            }
        }

        // --- Visit history --------------------------------------------------
        if (patient.recentVisits.isNotEmpty()) {
            item { SectionLabel("Previous visits") }
            items(patient.recentVisits, key = { it.id }) { visit ->
                val visitRisk = Risk.from(visit.riskLevel)
                SectionCard(onClick = { onOpenVisit(visit.id) }) {
                    Row(verticalAlignment = Alignment.Top) {
                        Column(Modifier.weight(1f)) {
                            Text(
                                visit.visitedAt.take(10),
                                style = MaterialTheme.typography.titleSmall,
                            )
                            if (!visit.summary.isNullOrBlank()) {
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    visit.summary!!,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        }
                        Spacer(Modifier.width(8.dp))
                        RiskChip(visitRisk)
                    }
                }
            }
        }
    }
}

@Composable
private fun VaccinationRow(vaccination: VaccinationDto, onMarkGiven: (String) -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(
                listOfNotNull(vaccination.vaccine, vaccination.doseLabel).joinToString(" "),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium,
            )
            Text(
                "Due ${vaccination.dueDate ?: "-"}",
                style = MaterialTheme.typography.bodySmall,
                color = if (vaccination.overdue) Risk.AMBER.color()
                else MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        TextButton(onClick = { onMarkGiven(vaccination.id) }) {
            Text("Mark given", style = MaterialTheme.typography.labelMedium)
        }
    }
}
