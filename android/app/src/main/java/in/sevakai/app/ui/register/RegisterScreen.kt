package `in`.sevakai.app.ui.register

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
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.ui.components.Notice
import `in`.sevakai.app.ui.components.NoticeTone
import `in`.sevakai.app.ui.components.SectionCard
import `in`.sevakai.app.ui.components.SectionLabel
import `in`.sevakai.app.ui.i18n.LocalStrings
import `in`.sevakai.app.ui.roster.categoryLabel
import `in`.sevakai.app.ui.theme.LocalRiskPalette

private val CATEGORY_KEYS = listOf(
    "pregnant", "infant", "child", "postnatal", "adult", "elderly",
)

@Composable
fun RegisterScreen(
    repository: Repository,
    onBack: () -> Unit,
    onRegistered: (String) -> Unit,
) {
    val viewModel: RegisterViewModel = viewModel(factory = RegisterViewModel.factory(repository))
    val state by viewModel.state.collectAsStateWithLifecycle()
    val strings = LocalStrings.current

    LaunchedEffect(state.createdId) {
        state.createdId?.let(onRegistered)
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
                Text(strings.registerPatient, style = MaterialTheme.typography.titleMedium)
            }

            Column(Modifier.padding(horizontal = 20.dp)) {
                Spacer(Modifier.height(8.dp))

                // --- Aadhaar ------------------------------------------------
                SectionCard {
                    SectionLabel(strings.sectionAadhaar)
                    Spacer(Modifier.height(6.dp))
                    Text(
                        strings.aadhaarExplainer,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(
                        value = state.aadhaarDisplay,
                        onValueChange = viewModel::onAadhaarChange,
                        label = { Text(strings.aadhaarNumber) },
                        placeholder = { Text(strings.aadhaarPlaceholder) },
                        singleLine = true,
                        shape = MaterialTheme.shapes.small,
                        textStyle = MaterialTheme.typography.bodyLarge,
                        isError = state.aadhaarChecked && !state.aadhaarValid,
                        trailingIcon = {
                            if (state.checkingAadhaar) {
                                CircularProgressIndicator(
                                    Modifier.size(18.dp), strokeWidth = 2.dp,
                                )
                            } else if (state.aadhaarValid) {
                                Icon(
                                    Icons.Default.CheckCircle,
                                    contentDescription = strings.connected,
                                    tint = MaterialTheme.colorScheme.primary,
                                )
                            }
                        },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth(),
                    )
                    if (state.aadhaarMessage != null) {
                        Spacer(Modifier.height(10.dp))
                        Notice(
                            state.aadhaarMessage!!,
                            tone = if (state.aadhaarValid) NoticeTone.INFO else NoticeTone.WARNING,
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(
                            checked = state.consent,
                            onCheckedChange = viewModel::onConsentChange,
                        )
                        Spacer(Modifier.width(4.dp))
                        Text(
                            strings.aadhaarConsent,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.clickable { viewModel.onConsentChange(!state.consent) },
                        )
                    }
                }

                Spacer(Modifier.height(14.dp))

                // --- Identity -----------------------------------------------
                SectionCard {
                    SectionLabel(strings.sectionPatientDetails)
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(
                        value = state.name,
                        onValueChange = viewModel::onNameChange,
                        label = { Text(strings.fullName) },
                        singleLine = true,
                        shape = MaterialTheme.shapes.small,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf(
                            "female" to strings.genderFemale,
                            "male" to strings.genderMale,
                            "other" to strings.genderOther,
                        )
                            .forEach { (key, label) ->
                                val selected = state.gender == key
                                Box(
                                    Modifier
                                        .weight(1f)
                                        .clip(MaterialTheme.shapes.small)
                                        .background(
                                            if (selected) MaterialTheme.colorScheme.primaryContainer
                                            else MaterialTheme.colorScheme.surfaceVariant
                                        )
                                        .clickable { viewModel.onGenderChange(key) }
                                        .padding(vertical = 14.dp),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    Text(
                                        label,
                                        style = MaterialTheme.typography.labelLarge,
                                        color = if (selected) MaterialTheme.colorScheme.primary
                                        else MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        OutlinedTextField(
                            value = state.dob,
                            onValueChange = viewModel::onDobChange,
                            label = { Text(strings.dateOfBirth) },
                            placeholder = { Text(strings.dobPlaceholder) },
                            singleLine = true,
                            isError = state.dobError != null,
                            supportingText = state.dobError?.let { { Text(it) } },
                            shape = MaterialTheme.shapes.small,
                            modifier = Modifier.weight(1f),
                        )
                        OutlinedTextField(
                            value = state.bloodGroup,
                            onValueChange = viewModel::onBloodGroupChange,
                            label = { Text(strings.bloodGroup) },
                            singleLine = true,
                            shape = MaterialTheme.shapes.small,
                            modifier = Modifier.weight(1f),
                        )
                    }
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(
                        value = state.phone,
                        onValueChange = viewModel::onPhoneChange,
                        label = { Text(strings.phoneOptional) },
                        singleLine = true,
                        shape = MaterialTheme.shapes.small,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                        modifier = Modifier.fillMaxWidth(),
                    )
                }

                Spacer(Modifier.height(14.dp))

                // --- Category -----------------------------------------------
                SectionCard {
                    SectionLabel(strings.sectionCategory)
                    Spacer(Modifier.height(4.dp))
                    Text(
                        strings.categoryHint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(12.dp))
                    CATEGORY_KEYS.chunked(3).forEach { row ->
                        Row(
                            Modifier.fillMaxWidth().padding(bottom = 8.dp),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            row.forEach { key ->
                                val selected = state.category == key
                                Box(
                                    Modifier
                                        .weight(1f)
                                        .clip(MaterialTheme.shapes.small)
                                        .background(
                                            if (selected) MaterialTheme.colorScheme.primaryContainer
                                            else MaterialTheme.colorScheme.surfaceVariant
                                        )
                                        .clickable { viewModel.onCategoryChange(key) }
                                        .padding(vertical = 14.dp),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    Text(
                                        categoryLabel(key),
                                        style = MaterialTheme.typography.labelMedium,
                                        color = if (selected) MaterialTheme.colorScheme.primary
                                        else MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                            repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
                        }
                    }

                    if (state.category == "pregnant") {
                        Spacer(Modifier.height(4.dp))
                        OutlinedTextField(
                            value = state.lmp,
                            onValueChange = viewModel::onLmpChange,
                            label = { Text(strings.lastMenstrualPeriod) },
                            placeholder = { Text(strings.dobPlaceholder) },
                            singleLine = true,
                            shape = MaterialTheme.shapes.small,
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Spacer(Modifier.height(6.dp))
                        Text(
                            strings.lmpHint,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }

                    if (state.category == "infant") {
                        Spacer(Modifier.height(4.dp))
                        OutlinedTextField(
                            value = state.birthWeight,
                            onValueChange = viewModel::onBirthWeightChange,
                            label = { Text(strings.birthWeightKg) },
                            singleLine = true,
                            shape = MaterialTheme.shapes.small,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Spacer(Modifier.height(6.dp))
                        Text(
                            strings.infantScheduleHint,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }

                if (state.error != null) {
                    Spacer(Modifier.height(14.dp))
                    Notice(state.error!!, tone = NoticeTone.WARNING)
                }

                Spacer(Modifier.height(20.dp))
                Button(
                    onClick = viewModel::submit,
                    enabled = state.canSubmit && !state.submitting,
                    shape = MaterialTheme.shapes.small,
                    modifier = Modifier.fillMaxWidth().heightIn(min = 56.dp),
                ) {
                    if (state.submitting) {
                        CircularProgressIndicator(
                            Modifier.size(20.dp), strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary,
                        )
                    } else {
                        Text(strings.registerButton, style = MaterialTheme.typography.labelLarge)
                    }
                }
                Spacer(Modifier.height(40.dp))
            }
        }
    }
}
