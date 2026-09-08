package `in`.sevakai.app.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import `in`.sevakai.app.BuildConfig
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.settingsDataStore by preferencesDataStore("sevakai_settings")

/**
 * Where the backend lives.
 *
 * This has to be changeable at runtime, not baked in at build time. The same
 * APK gets run on an emulator, on a phone tethered over USB, and on a phone on
 * the same Wi-Fi as the laptop - and each of those needs a different address:
 *
 *   emulator            http://10.0.2.2:8010    (QEMU maps this to the host)
 *   phone, USB          http://127.0.0.1:8010   (via `adb reverse`)
 *   phone, same Wi-Fi   http://<laptop LAN IP>:8010
 *
 * 10.0.2.2 is emulator-only magic. It does not resolve on a real device, which
 * is a confusing failure because it looks like an ordinary connection timeout.
 */
class SettingsStore(private val context: Context) {

    private object Keys {
        val SERVER_URL = stringPreferencesKey("server_url")
    }

    val serverUrl: Flow<String> = context.settingsDataStore.data.map {
        it[Keys.SERVER_URL] ?: BuildConfig.API_BASE_URL
    }

    suspend fun current(): String =
        context.settingsDataStore.data.first()[Keys.SERVER_URL] ?: BuildConfig.API_BASE_URL

    suspend fun setServerUrl(raw: String) {
        context.settingsDataStore.edit { it[Keys.SERVER_URL] = normalise(raw) }
    }

    suspend fun reset() {
        context.settingsDataStore.edit { it.remove(Keys.SERVER_URL) }
    }

    companion object {
        const val EMULATOR = "http://10.0.2.2:8010/"
        const val USB = "http://127.0.0.1:8010/"

        /**
         * Accept what someone actually types. "192.168.1.7" should work as
         * well as "http://192.168.1.7:8010/", because on a phone keyboard the
         * full form is tedious and easy to get wrong.
         */
        fun normalise(raw: String): String {
            var value = raw.trim()
            if (value.isEmpty()) return EMULATOR
            if (!value.startsWith("http://") && !value.startsWith("https://")) {
                value = "http://$value"
            }
            // Add the default port when only a host was given.
            val afterScheme = value.substringAfter("://")
            val hostPart = afterScheme.substringBefore("/")
            if (!hostPart.contains(":")) {
                value = value.replaceFirst(hostPart, "$hostPart:8010")
            }
            if (!value.endsWith("/")) value = "$value/"
            return value
        }

        /** A short label for the address bar, e.g. "192.168.1.7:8010". */
        fun describe(url: String): String =
            url.substringAfter("://").trimEnd('/')
    }
}
