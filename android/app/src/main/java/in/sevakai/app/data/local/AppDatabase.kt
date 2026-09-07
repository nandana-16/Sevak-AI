package `in`.sevakai.app.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters

class Converters {
    @TypeConverter
    fun toStatus(value: String): QueueStatus = QueueStatus.valueOf(value)

    @TypeConverter
    fun fromStatus(status: QueueStatus): String = status.name
}

@Database(
    entities = [CachedPatient::class, CachedScheduleItem::class, PendingVisit::class],
    version = 1,
    exportSchema = false,
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun patients(): PatientDao
    abstract fun schedule(): ScheduleDao
    abstract fun pendingVisits(): PendingVisitDao

    companion object {
        @Volatile
        private var instance: AppDatabase? = null

        fun get(context: Context): AppDatabase = instance ?: synchronized(this) {
            instance ?: Room.databaseBuilder(
                context.applicationContext,
                AppDatabase::class.java,
                "sevakai.db",
            )
                // The cache tables are disposable, but pending_visits is not,
                // so destructive migration is deliberately NOT enabled: a
                // schema change must be migrated, never dropped.
                .build()
                .also { instance = it }
        }
    }
}
