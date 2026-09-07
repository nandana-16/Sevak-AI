package `in`.sevakai.app.sync

import android.content.Context
import android.util.Log
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import `in`.sevakai.app.SevakApp
import java.util.concurrent.TimeUnit

/**
 * Drains the pending-visit queue whenever the phone has a connection.
 *
 * WorkManager is doing the load-bearing work here, not a foreground timer: the
 * worker may close the app, lock the phone and walk two villages before signal
 * returns, and the queue still has to go up. The CONNECTED constraint means
 * the system wakes us at the moment a network appears rather than us polling.
 */
class SyncWorker(
    context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val repository = SevakApp.repository(applicationContext)
        // No point burning a wake-up if nobody is signed in.
        if (repository.session.token() == null) return Result.success()

        return try {
            val sent = repository.flushQueue()
            if (sent > 0) Log.i(TAG, "Synced $sent queued visit(s)")
            Result.success()
        } catch (e: Exception) {
            Log.w(TAG, "Sync failed, will retry: ${e.message}")
            Result.retry()
        }
    }

    companion object {
        private const val TAG = "SevakSync"
        private const val PERIODIC = "sevakai_periodic_sync"
        private const val IMMEDIATE = "sevakai_immediate_sync"

        private val networkRequired = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        /** Safety net: even if every trigger is missed, the queue drains. */
        fun schedulePeriodic(context: Context) {
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                PERIODIC,
                ExistingPeriodicWorkPolicy.KEEP,
                PeriodicWorkRequestBuilder<SyncWorker>(15, TimeUnit.MINUTES)
                    .setConstraints(networkRequired)
                    .build(),
            )
        }

        /** Called when the app opens and after a visit is queued. */
        fun syncNow(context: Context) {
            WorkManager.getInstance(context).enqueueUniqueWork(
                IMMEDIATE,
                ExistingWorkPolicy.REPLACE,
                OneTimeWorkRequestBuilder<SyncWorker>()
                    .setConstraints(networkRequired)
                    .setBackoffCriteria(
                        androidx.work.BackoffPolicy.EXPONENTIAL,
                        30, TimeUnit.SECONDS,
                    )
                    .build(),
            )
        }
    }
}
