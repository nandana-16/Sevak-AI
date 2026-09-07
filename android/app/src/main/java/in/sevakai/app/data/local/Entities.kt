package `in`.sevakai.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Local storage serves two distinct jobs, and they are kept apart on purpose.
 *
 * [CachedPatient] is a *mirror* - a read-only copy of server data so a roster
 * and a profile still open with no signal. It can be thrown away and rebuilt.
 *
 * [PendingVisit] is *the only copy* - work the worker has done that the server
 * has never seen. Losing a row here means losing a home visit, so it is never
 * cleared except after the server confirms receipt.
 */

@Entity(tableName = "cached_patients")
data class CachedPatient(
    @PrimaryKey val id: String,
    val name: String,
    val ageLabel: String,
    val gender: String,
    val category: String,
    val village: String?,
    val currentRisk: String,
    val lastVisitAt: String?,
    val lastVisitSummary: String?,
    val nextVisitDue: String?,
    val aadhaarVerified: Boolean,
    /** Full PatientDetailDto as JSON, so a profile opens offline too. */
    val detailJson: String? = null,
    val cachedAt: Long = System.currentTimeMillis(),
)

@Entity(tableName = "cached_schedule")
data class CachedScheduleItem(
    @PrimaryKey val id: String,
    val patientId: String,
    val patientName: String,
    val patientVillage: String?,
    val dueDate: String,
    val reason: String,
    val priority: String,
    val overdue: Boolean,
)

enum class QueueStatus { PENDING, UPLOADING, SYNCED, FAILED }

@Entity(tableName = "pending_visits")
data class PendingVisit(
    /** Generated on the device before anything is sent. The server keys
     *  idempotency off this, so retrying is always safe. */
    @PrimaryKey val clientUuid: String,
    val patientId: String,
    val patientName: String,
    val transcript: String?,
    val typedNotes: String?,
    /** Manual measurements, serialised as JSON. */
    val manualFieldsJson: String,
    val inputMode: String,
    val language: String,
    val visitedAt: String,
    /** Absolute path to a recording, when speech could not be transcribed on
     *  the device. Deleted only once the visit is confirmed synced. */
    val audioPath: String? = null,
    val status: QueueStatus = QueueStatus.PENDING,
    val attempts: Int = 0,
    val lastError: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    /** Server visit id once accepted. */
    val serverVisitId: String? = null,
    val resultRisk: String? = null,
    val resultSummary: String? = null,
)
