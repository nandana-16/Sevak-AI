package `in`.sevakai.app.data

import android.content.Context
import android.util.Log
import `in`.sevakai.app.data.local.AppDatabase
import `in`.sevakai.app.data.local.CachedPatient
import `in`.sevakai.app.data.local.CachedScheduleItem
import `in`.sevakai.app.data.local.PendingVisit
import `in`.sevakai.app.data.local.QueueStatus
import `in`.sevakai.app.data.remote.ApiClient
import `in`.sevakai.app.data.remote.ApiService
import `in`.sevakai.app.data.remote.LoginRequest
import `in`.sevakai.app.data.remote.PatientCreateRequest
import `in`.sevakai.app.data.remote.PatientDetailDto
import `in`.sevakai.app.data.remote.PatientSummaryDto
import `in`.sevakai.app.data.remote.ScheduledVisitDto
import `in`.sevakai.app.data.remote.UnauthorizedException
import `in`.sevakai.app.data.remote.VisitCreateRequest
import `in`.sevakai.app.data.remote.VisitDetailDto
import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.encodeToString
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.IOException
import java.time.Instant
import java.util.UUID

private const val TAG = "SevakRepo"

/**
 * The single source of truth for the UI.
 *
 * The rule throughout: **a network failure is never an error the worker has to
 * deal with.** Reads fall back to the local mirror; a submitted visit goes
 * into the queue first and is uploaded whenever a connection appears. The only
 * failure surfaced as an error is an expired session, because that one does
 * need the worker to act.
 */
class Repository(
    private val context: Context,
    val api: ApiService,
    val session: SessionStore,
    val settings: SettingsStore,
) {
    private val db = AppDatabase.get(context)
    private val patientDao = db.patients()
    private val scheduleDao = db.schedule()
    private val queueDao = db.pendingVisits()

    val pendingVisits: Flow<List<PendingVisit>> = queueDao.observeAll()
    val unsyncedCount: Flow<Int> = queueDao.observeUnsyncedCount()

    // --- Auth ---------------------------------------------------------------

    suspend fun login(phone: String, pin: String): Result<Unit> = runCatching {
        val response = api.login(LoginRequest(phone, pin))
        session.save(
            token = response.accessToken,
            workerId = response.worker.id,
            name = response.worker.name,
            role = response.worker.role,
            village = response.worker.village,
            phone = response.worker.phone,
        )
    }

    suspend fun logout() {
        session.clear()
        patientDao.clear()
        scheduleDao.clear()
        // Queued visits are intentionally left alone.
    }

    // --- Roster -------------------------------------------------------------

    /**
     * Returns the roster and whether it came from the network. When offline,
     * the cached mirror is returned with `fromCache = true` so the UI can say
     * so honestly instead of pretending the data is live.
     */
    suspend fun roster(
        search: String? = null,
        village: String? = null,
        category: String? = null,
        risk: String? = null,
        dueOnly: Boolean = false,
    ): RosterResult {
        return try {
            val remote = api.patients(
                search = search?.takeIf { it.isNotBlank() },
                village = village,
                category = category,
                risk = risk,
                dueOnly = dueOnly.takeIf { it },
            )
            // Only a full, unfiltered fetch is allowed to define the mirror -
            // caching a filtered result would silently delete patients from
            // the offline roster.
            if (search.isNullOrBlank() && village == null && category == null &&
                risk == null && !dueOnly
            ) {
                patientDao.upsertAll(remote.map { it.toCached() })
            }
            RosterResult(remote.map { it.toRow() }, fromCache = false)
        } catch (e: UnauthorizedException) {
            throw e
        } catch (e: Exception) {
            Log.i(TAG, "Roster from cache: ${e.javaClass.simpleName}")
            val cached = patientDao.allOnce()
                .filter { row ->
                    (search.isNullOrBlank() ||
                        row.name.contains(search, true) ||
                        row.village.orEmpty().contains(search, true)) &&
                        (village == null || row.village == village) &&
                        (category == null || row.category == category) &&
                        (risk == null || row.currentRisk == risk)
                }
            RosterResult(cached.map { it.toRow() }, fromCache = true)
        }
    }

    suspend fun villages(): List<String> = try {
        api.villages()
    } catch (e: UnauthorizedException) {
        throw e
    } catch (e: Exception) {
        patientDao.allOnce().mapNotNull { it.village }.distinct().sorted()
    }

    suspend fun patient(id: String): PatientResult {
        return try {
            val detail = api.patient(id)
            patientDao.upsert(
                detail.toSummary().toCached(
                    detailJson = ApiClient.json.encodeToString(detail)
                )
            )
            PatientResult(detail, fromCache = false)
        } catch (e: UnauthorizedException) {
            throw e
        } catch (e: Exception) {
            val cached = patientDao.byId(id)
            val json = cached?.detailJson
                ?: throw IOException("This profile has not been opened before, so there is no offline copy")
            PatientResult(ApiClient.json.decodeFromString(json), fromCache = true)
        }
    }

    suspend fun registerPatient(request: PatientCreateRequest): Result<PatientDetailDto> =
        runCatching { api.createPatient(request) }

    suspend fun checkAadhaar(number: String) = runCatching {
        api.checkAadhaar(`in`.sevakai.app.data.remote.AadhaarCheckRequest(number))
    }

    // --- Schedule -----------------------------------------------------------

    suspend fun schedule(days: Int = 14): ScheduleResult = try {
        val remote = if (days <= 0) api.scheduleToday() else api.schedule(days)
        scheduleDao.upsertAll(remote.map { it.toCached() })
        ScheduleResult(remote.map { it.toRow() }, fromCache = false)
    } catch (e: UnauthorizedException) {
        throw e
    } catch (e: Exception) {
        ScheduleResult(scheduleDao.allOnce().map { it.toRow() }, fromCache = true)
    }

    suspend fun snooze(id: String, days: Int) = runCatching { api.snooze(id, days) }

    // --- Visits -------------------------------------------------------------

    /**
     * Record a visit.
     *
     * Always writes to the local queue first, then tries to upload. That order
     * is the whole point: if the phone dies, the app is killed, or the network
     * vanishes between the two steps, the visit still exists.
     */
    suspend fun submitVisit(
        patientId: String,
        patientName: String,
        transcript: String?,
        typedNotes: String?,
        manualFields: Map<String, Double>,
        inputMode: String,
        language: String,
        audioFile: File? = null,
    ): SubmitResult {
        val clientUuid = UUID.randomUUID().toString()
        val visitedAt = Instant.now().toString()

        val queued = PendingVisit(
            clientUuid = clientUuid,
            patientId = patientId,
            patientName = patientName,
            transcript = transcript,
            typedNotes = typedNotes,
            manualFieldsJson = ApiClient.json.encodeToString(manualFields),
            inputMode = inputMode,
            language = language,
            visitedAt = visitedAt,
            audioPath = audioFile?.absolutePath,
        )
        queueDao.insert(queued)

        return when (val outcome = upload(queued)) {
            is UploadOutcome.Success -> SubmitResult.Processed(outcome.visit)
            is UploadOutcome.Retry -> SubmitResult.Queued(clientUuid, outcome.reason)
            is UploadOutcome.Unauthorized -> throw UnauthorizedException()
        }
    }

    /** Push one queued visit. Used by both the foreground path and the worker. */
    suspend fun upload(item: PendingVisit): UploadOutcome {
        queueDao.update(item.copy(status = QueueStatus.UPLOADING))
        return try {
            val response = if (item.audioPath != null && item.transcript.isNullOrBlank()) {
                uploadAudio(item)
            } else {
                api.submitVisit(
                    VisitCreateRequest(
                        clientUuid = item.clientUuid,
                        patientId = item.patientId,
                        transcript = item.transcript,
                        typedNotes = item.typedNotes,
                        manualFields = ApiClient.json.decodeFromString(item.manualFieldsJson),
                        inputMode = item.inputMode,
                        language = item.language,
                        visitedAt = item.visitedAt,
                    )
                )
            }
            queueDao.update(
                item.copy(
                    status = QueueStatus.SYNCED,
                    serverVisitId = response.id,
                    resultRisk = response.riskLevel,
                    resultSummary = response.summary,
                    lastError = null,
                )
            )
            // The recording has served its purpose once the server has the text.
            item.audioPath?.let { runCatching { File(it).delete() } }
            UploadOutcome.Success(response)
        } catch (e: UnauthorizedException) {
            queueDao.update(item.copy(status = QueueStatus.PENDING))
            UploadOutcome.Unauthorized
        } catch (e: Exception) {
            val attempts = item.attempts + 1
            queueDao.update(
                item.copy(
                    status = QueueStatus.FAILED,
                    attempts = attempts,
                    lastError = e.message ?: e.javaClass.simpleName,
                )
            )
            Log.i(TAG, "Visit ${item.clientUuid} queued (attempt $attempts): ${e.message}")
            UploadOutcome.Retry(e.message ?: "No connection")
        }
    }

    private suspend fun uploadAudio(item: PendingVisit): VisitDetailDto {
        val file = File(item.audioPath!!)
        if (!file.exists()) throw IOException("The recording for this visit is missing")

        fun text(value: String) = value.toRequestBody("text/plain".toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData(
            "audio", file.name, file.asRequestBody("audio/mp4".toMediaTypeOrNull())
        )
        return api.submitVisitAudio(
            clientUuid = text(item.clientUuid),
            patientId = text(item.patientId),
            language = text(item.language),
            typedNotes = item.typedNotes?.let { text(it) },
            manualFields = text(item.manualFieldsJson),
            audio = part,
        )
    }

    suspend fun flushQueue(): Int {
        queueDao.releaseStuck()
        var sent = 0
        for (item in queueDao.readyToSend()) {
            when (upload(item)) {
                is UploadOutcome.Success -> sent++
                is UploadOutcome.Unauthorized -> return sent
                is UploadOutcome.Retry -> Unit
            }
        }
        queueDao.pruneSynced(System.currentTimeMillis() - SYNCED_RETENTION_MS)
        return sent
    }

    suspend fun visit(id: String) = runCatching { api.visit(id) }

    suspend fun visits(patientId: String) = runCatching { api.visits(patientId) }

    suspend fun escalations() = runCatching { api.escalations() }

    suspend fun cachedPatientCount() = patientDao.count()

    companion object {
        /** Keep synced rows around for a day so the worker can still see what
         *  came back for a visit they recorded offline this morning. */
        private const val SYNCED_RETENTION_MS = 24 * 60 * 60 * 1000L
    }
}

sealed interface SubmitResult {
    data class Processed(val visit: VisitDetailDto) : SubmitResult
    data class Queued(val clientUuid: String, val reason: String) : SubmitResult
}

sealed interface UploadOutcome {
    data class Success(val visit: VisitDetailDto) : UploadOutcome
    data class Retry(val reason: String) : UploadOutcome
    data object Unauthorized : UploadOutcome
}

data class RosterResult(val patients: List<PatientRow>, val fromCache: Boolean)
data class PatientResult(val patient: PatientDetailDto, val fromCache: Boolean)
data class ScheduleResult(val items: List<ScheduleRow>, val fromCache: Boolean)

data class PatientRow(
    val id: String,
    val name: String,
    val ageLabel: String,
    val gender: String,
    val category: String,
    val village: String?,
    val risk: String,
    val lastVisitSummary: String?,
    val nextVisitDue: String?,
    val aadhaarVerified: Boolean,
)

data class ScheduleRow(
    val id: String,
    val patientId: String,
    val patientName: String,
    val village: String?,
    val dueDate: String,
    val reason: String,
    val priority: String,
    val overdue: Boolean,
)

// --- Mapping ----------------------------------------------------------------

private fun PatientSummaryDto.toRow() = PatientRow(
    id, name, ageLabel, gender, category, village, currentRisk,
    lastVisitSummary, nextVisitDue, aadhaarVerified,
)

private fun CachedPatient.toRow() = PatientRow(
    id, name, ageLabel, gender, category, village, currentRisk,
    lastVisitSummary, nextVisitDue, aadhaarVerified,
)

private fun PatientSummaryDto.toCached(detailJson: String? = null) = CachedPatient(
    id = id,
    name = name,
    ageLabel = ageLabel,
    gender = gender,
    category = category,
    village = village,
    currentRisk = currentRisk,
    lastVisitAt = lastVisitAt,
    lastVisitSummary = lastVisitSummary,
    nextVisitDue = nextVisitDue,
    aadhaarVerified = aadhaarVerified,
    detailJson = detailJson,
)

private fun PatientDetailDto.toSummary() = PatientSummaryDto(
    id = id, name = name, ageLabel = ageLabel, gender = gender, category = category,
    village = village, currentRisk = currentRisk, lastVisitAt = lastVisitAt,
    lastVisitSummary = lastVisitSummary, nextVisitDue = nextVisitDue,
    aadhaarVerified = aadhaarVerified,
)

private fun ScheduledVisitDto.toRow() = ScheduleRow(
    id, patientId, patientName, patientVillage, dueDate, reason, priority, overdue,
)

private fun CachedScheduleItem.toRow() = ScheduleRow(
    id, patientId, patientName, patientVillage, dueDate, reason, priority, overdue,
)

private fun ScheduledVisitDto.toCached() = CachedScheduleItem(
    id, patientId, patientName, patientVillage, dueDate, reason, priority, overdue,
)
