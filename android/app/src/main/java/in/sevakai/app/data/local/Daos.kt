package `in`.sevakai.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface PatientDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(patients: List<CachedPatient>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(patient: CachedPatient)

    @Query("SELECT * FROM cached_patients ORDER BY name")
    fun observeAll(): Flow<List<CachedPatient>>

    @Query("SELECT * FROM cached_patients ORDER BY name")
    suspend fun allOnce(): List<CachedPatient>

    @Query("SELECT * FROM cached_patients WHERE id = :id")
    suspend fun byId(id: String): CachedPatient?

    @Query("DELETE FROM cached_patients")
    suspend fun clear()

    @Query("SELECT COUNT(*) FROM cached_patients")
    suspend fun count(): Int
}

@Dao
interface ScheduleDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(items: List<CachedScheduleItem>)

    @Query("SELECT * FROM cached_schedule ORDER BY overdue DESC, dueDate")
    fun observeAll(): Flow<List<CachedScheduleItem>>

    @Query("SELECT * FROM cached_schedule ORDER BY overdue DESC, dueDate")
    suspend fun allOnce(): List<CachedScheduleItem>

    @Query("DELETE FROM cached_schedule")
    suspend fun clear()
}

@Dao
interface PendingVisitDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(visit: PendingVisit)

    @Update
    suspend fun update(visit: PendingVisit)

    @Query("SELECT * FROM pending_visits ORDER BY createdAt DESC")
    fun observeAll(): Flow<List<PendingVisit>>

    @Query("SELECT * FROM pending_visits WHERE status IN ('PENDING','FAILED') ORDER BY createdAt")
    suspend fun readyToSend(): List<PendingVisit>

    @Query("SELECT COUNT(*) FROM pending_visits WHERE status IN ('PENDING','UPLOADING','FAILED')")
    fun observeUnsyncedCount(): Flow<Int>

    @Query("SELECT * FROM pending_visits WHERE clientUuid = :uuid")
    suspend fun byUuid(uuid: String): PendingVisit?

    @Query("DELETE FROM pending_visits WHERE status = 'SYNCED' AND createdAt < :before")
    suspend fun pruneSynced(before: Long)

    /** Reset a row stuck in UPLOADING, e.g. after the app was killed mid-send. */
    @Query("UPDATE pending_visits SET status = 'PENDING' WHERE status = 'UPLOADING'")
    suspend fun releaseStuck()
}
