package `in`.sevakai.app.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore("sevakai_session")

/**
 * Who is signed in, and their token.
 *
 * The token is long-lived by design (14 days) because a worker can be out of
 * signal for days and being logged out mid-round is worse than the marginal
 * exposure. See the security notes in docs/ for what this trades away.
 */
class SessionStore(private val context: Context) {

    private object Keys {
        val TOKEN = stringPreferencesKey("token")
        val WORKER_ID = stringPreferencesKey("worker_id")
        val WORKER_NAME = stringPreferencesKey("worker_name")
        val WORKER_ROLE = stringPreferencesKey("worker_role")
        val WORKER_VILLAGE = stringPreferencesKey("worker_village")
        val WORKER_PHONE = stringPreferencesKey("worker_phone")
        val ONBOARDED = booleanPreferencesKey("onboarded")
    }

    data class Session(
        val token: String,
        val workerId: String,
        val workerName: String,
        val role: String,
        val village: String?,
        val phone: String,
    )

    val session: Flow<Session?> = context.dataStore.data.map { prefs ->
        val token = prefs[Keys.TOKEN] ?: return@map null
        Session(
            token = token,
            workerId = prefs[Keys.WORKER_ID].orEmpty(),
            workerName = prefs[Keys.WORKER_NAME].orEmpty(),
            role = prefs[Keys.WORKER_ROLE] ?: "asha",
            village = prefs[Keys.WORKER_VILLAGE],
            phone = prefs[Keys.WORKER_PHONE].orEmpty(),
        )
    }


    suspend fun token(): String? = context.dataStore.data.first()[Keys.TOKEN]

    suspend fun save(
        token: String,
        workerId: String,
        name: String,
        role: String,
        village: String?,
        phone: String,
    ) {
        context.dataStore.edit { prefs ->
            prefs[Keys.TOKEN] = token
            prefs[Keys.WORKER_ID] = workerId
            prefs[Keys.WORKER_NAME] = name
            prefs[Keys.WORKER_ROLE] = role
            prefs[Keys.WORKER_PHONE] = phone
            if (village != null) prefs[Keys.WORKER_VILLAGE] = village
            prefs[Keys.ONBOARDED] = true
        }
    }


    /**
     * Sign out. Note this clears credentials only - queued visits stay on the
     * device, because they are unsent work, not session state.
     */
    suspend fun clear() {
        context.dataStore.edit { prefs ->
            prefs.remove(Keys.TOKEN)
            prefs.remove(Keys.WORKER_ID)
            prefs.remove(Keys.WORKER_NAME)
            prefs.remove(Keys.WORKER_ROLE)
            prefs.remove(Keys.WORKER_VILLAGE)
        }
    }
}
