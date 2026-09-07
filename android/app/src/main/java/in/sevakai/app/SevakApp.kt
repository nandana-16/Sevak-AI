package `in`.sevakai.app

import android.app.Application
import android.content.Context
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.SessionStore
import `in`.sevakai.app.data.remote.ApiClient
import `in`.sevakai.app.sync.SyncWorker

/**
 * Application entry point and a deliberately tiny service locator.
 *
 * A DI framework would buy little here - there are three long-lived objects and
 * no build variants that swap them - and it would add annotation processing to
 * every build. Everything is constructed once, lazily, and handed out.
 */
class SevakApp : Application() {

    override fun onCreate() {
        super.onCreate()
        instance = this
        SyncWorker.schedulePeriodic(this)
        SyncWorker.syncNow(this)
    }

    companion object {
        @Volatile
        private var instance: SevakApp? = null

        @Volatile
        private var repo: Repository? = null

        fun repository(context: Context): Repository = repo ?: synchronized(this) {
            repo ?: run {
                val app = context.applicationContext
                val session = SessionStore(app)
                Repository(app, ApiClient.create(session), session).also { repo = it }
            }
        }
    }
}
