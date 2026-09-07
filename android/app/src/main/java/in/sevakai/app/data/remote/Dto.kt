package `in`.sevakai.app.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class LoginRequest(val phone: String, val pin: String)

@Serializable
data class LoginResponse(
    @SerialName("access_token") val accessToken: String,
    val worker: WorkerDto,
)

@Serializable
data class WorkerDto(
    val id: String,
    val name: String,
    val phone: String,
    val role: String,
    val village: String? = null,
    val block: String? = null,
    val district: String? = null,
    @SerialName("preferred_language") val preferredLanguage: String = "hi",
)

@Serializable
data class PatientSummaryDto(
    val id: String,
    val name: String,
    @SerialName("age_label") val ageLabel: String = "",
    val gender: String,
    val category: String,
    val village: String? = null,
    @SerialName("current_risk") val currentRisk: String,
    @SerialName("last_visit_at") val lastVisitAt: String? = null,
    @SerialName("last_visit_summary") val lastVisitSummary: String? = null,
    @SerialName("next_visit_due") val nextVisitDue: String? = null,
    @SerialName("aadhaar_verified") val aadhaarVerified: Boolean = false,
)

@Serializable
data class ConditionDto(
    val id: String,
    val name: String,
    @SerialName("diagnosed_on") val diagnosedOn: String? = null,
    val ongoing: Boolean,
    val notes: String? = null,
)

@Serializable
data class VaccinationDto(
    val id: String,
    val vaccine: String,
    @SerialName("dose_label") val doseLabel: String? = null,
    @SerialName("due_date") val dueDate: String? = null,
    @SerialName("given_date") val givenDate: String? = null,
    val given: Boolean,
    val overdue: Boolean = false,
)

@Serializable
data class PregnancyDto(
    val lmp: String? = null,
    val edd: String? = null,
    val gravida: Int? = null,
    val para: Int? = null,
    @SerialName("anc_visits_completed") val ancVisitsCompleted: Int = 0,
    @SerialName("tt_doses") val ttDoses: Int = 0,
    @SerialName("ifa_tablets_given") val ifaTabletsGiven: Int = 0,
    @SerialName("last_hb") val lastHb: Double? = null,
    @SerialName("last_bp_systolic") val lastBpSystolic: Int? = null,
    @SerialName("last_bp_diastolic") val lastBpDiastolic: Int? = null,
    @SerialName("last_weight_kg") val lastWeightKg: Double? = null,
    @SerialName("high_risk_factors") val highRiskFactors: List<String> = emptyList(),
    @SerialName("planned_delivery_place") val plannedDeliveryPlace: String? = null,
    @SerialName("gestation_weeks") val gestationWeeks: Int? = null,
)

@Serializable
data class InfantDto(
    @SerialName("birth_weight_kg") val birthWeightKg: Double? = null,
    @SerialName("gestation_weeks") val gestationWeeks: Int? = null,
    @SerialName("delivery_type") val deliveryType: String? = null,
    @SerialName("place_of_birth") val placeOfBirth: String? = null,
    @SerialName("exclusive_breastfeeding") val exclusiveBreastfeeding: Boolean? = null,
    @SerialName("last_weight_kg") val lastWeightKg: Double? = null,
    @SerialName("last_muac_cm") val lastMuacCm: Double? = null,
)

@Serializable
data class PatientDetailDto(
    val id: String,
    val name: String,
    @SerialName("age_label") val ageLabel: String = "",
    val gender: String,
    val category: String,
    val village: String? = null,
    @SerialName("current_risk") val currentRisk: String,
    @SerialName("last_visit_at") val lastVisitAt: String? = null,
    @SerialName("last_visit_summary") val lastVisitSummary: String? = null,
    @SerialName("next_visit_due") val nextVisitDue: String? = null,
    @SerialName("aadhaar_verified") val aadhaarVerified: Boolean = false,
    val dob: String? = null,
    @SerialName("blood_group") val bloodGroup: String? = null,
    val phone: String? = null,
    val address: String? = null,
    @SerialName("guardian_name") val guardianName: String? = null,
    @SerialName("household_id") val householdId: String? = null,
    val block: String? = null,
    val district: String? = null,
    @SerialName("aadhaar_masked") val aadhaarMasked: String = "Not linked",
    val conditions: List<ConditionDto> = emptyList(),
    val vaccinations: List<VaccinationDto> = emptyList(),
    val pregnancy: PregnancyDto? = null,
    val infant: InfantDto? = null,
    @SerialName("recent_visits") val recentVisits: List<VisitSummaryDto> = emptyList(),
)

@Serializable
data class VisitSummaryDto(
    val id: String,
    @SerialName("visited_at") val visitedAt: String,
    @SerialName("risk_level") val riskLevel: String,
    val summary: String? = null,
    val status: String,
    @SerialName("input_mode") val inputMode: String,
)

@Serializable
data class CitationDto(
    val text: String,
    val title: String,
    val page: Int,
    val url: String,
    val score: Double,
)

@Serializable
data class ActionDto(val action: String, val urgency: String)

@Serializable
data class VisitDetailDto(
    val id: String,
    @SerialName("visited_at") val visitedAt: String,
    @SerialName("risk_level") val riskLevel: String,
    val summary: String? = null,
    val status: String,
    @SerialName("input_mode") val inputMode: String,
    @SerialName("client_uuid") val clientUuid: String,
    @SerialName("patient_id") val patientId: String,
    val language: String = "hi",
    val transcript: String? = null,
    @SerialName("typed_notes") val typedNotes: String? = null,
    val symptoms: List<String> = emptyList(),
    @SerialName("temperature_c") val temperatureC: Double? = null,
    @SerialName("bp_systolic") val bpSystolic: Int? = null,
    @SerialName("bp_diastolic") val bpDiastolic: Int? = null,
    val pulse: Int? = null,
    @SerialName("weight_kg") val weightKg: Double? = null,
    val hb: Double? = null,
    val spo2: Int? = null,
    @SerialName("risk_rationale") val riskRationale: String? = null,
    @SerialName("risk_confidence") val riskConfidence: Double? = null,
    @SerialName("danger_signs") val dangerSigns: List<String> = emptyList(),
    @SerialName("guideline_citations") val citations: List<CitationDto> = emptyList(),
    @SerialName("recommended_actions") val actions: List<ActionDto> = emptyList(),
    @SerialName("next_visit_due") val nextVisitDue: String? = null,
    @SerialName("refer_to_facility") val referToFacility: Boolean = false,
    @SerialName("degraded_steps") val degradedSteps: List<String> = emptyList(),
    @SerialName("processing_ms") val processingMs: Int? = null,
    @SerialName("error_message") val errorMessage: String? = null,
)

@Serializable
data class VisitCreateRequest(
    @SerialName("client_uuid") val clientUuid: String,
    @SerialName("patient_id") val patientId: String,
    val transcript: String? = null,
    @SerialName("typed_notes") val typedNotes: String? = null,
    @SerialName("manual_fields") val manualFields: Map<String, Double> = emptyMap(),
    @SerialName("input_mode") val inputMode: String = "voice",
    val language: String = "hi",
    @SerialName("visited_at") val visitedAt: String? = null,
)

@Serializable
data class ScheduledVisitDto(
    val id: String,
    @SerialName("patient_id") val patientId: String,
    @SerialName("patient_name") val patientName: String = "",
    @SerialName("patient_village") val patientVillage: String? = null,
    @SerialName("due_date") val dueDate: String,
    val reason: String,
    val priority: String,
    val status: String,
    val overdue: Boolean = false,
)

@Serializable
data class EscalationDto(
    val id: String,
    @SerialName("patient_id") val patientId: String,
    @SerialName("patient_name") val patientName: String = "",
    @SerialName("visit_id") val visitId: String,
    @SerialName("worker_name") val workerName: String = "",
    @SerialName("raised_at") val raisedAt: String,
    val reason: String,
    val resolved: Boolean = false,
)

@Serializable
data class AadhaarCheckRequest(val aadhaar: String)

@Serializable
data class AadhaarCheckResponse(
    val valid: Boolean,
    val reason: String,
    val last4: String? = null,
    @SerialName("already_registered") val alreadyRegistered: Boolean = false,
    val method: String = "offline_verhoeff",
)

@Serializable
data class PatientCreateRequest(
    val name: String,
    val gender: String,
    val dob: String? = null,
    @SerialName("age_years_approx") val ageYearsApprox: Int? = null,
    @SerialName("blood_group") val bloodGroup: String? = null,
    val phone: String? = null,
    val category: String = "adult",
    val village: String? = null,
    val address: String? = null,
    @SerialName("guardian_name") val guardianName: String? = null,
    val aadhaar: String? = null,
    @SerialName("aadhaar_consent_given") val aadhaarConsentGiven: Boolean = false,
    val conditions: List<String> = emptyList(),
    val lmp: String? = null,
    @SerialName("birth_weight_kg") val birthWeightKg: Double? = null,
)

@Serializable
data class HealthDto(
    val status: String,
    @SerialName("llm_provider") val llmProvider: String,
    @SerialName("llm_ready") val llmReady: Boolean,
    @SerialName("guideline_chunks") val guidelineChunks: Int,
    val patients: Int,
)
