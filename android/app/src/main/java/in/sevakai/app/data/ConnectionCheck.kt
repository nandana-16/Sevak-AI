package `in`.sevakai.app.data

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import `in`.sevakai.app.data.remote.HealthDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.TimeUnit

/**
 * "Cannot connect to the server" is a useless thing to tell someone standing in
 * a field with a demo in ten minutes. This works out *which* link in the chain
 * is broken and says so, with the specific command or setting that fixes it.
 */
object ConnectionCheck {

    sealed interface Result {
        val message: String

        data class Ok(
            val llmReady: Boolean,
            val guidelineChunks: Int,
            val patients: Int,
            val latencyMs: Long,
        ) : Result {
            override val message: String
                get() = "Connected in ${latencyMs} ms · $patients patients · " +
                    "$guidelineChunks guideline chunks"
        }

        data class Failed(
            override val message: String,
            val hint: String,
        ) : Result
    }

    suspend fun run(context: Context, url: String): Result = withContext(Dispatchers.IO) {
        val normalised = SettingsStore.normalise(url)
        val target = normalised.trimEnd('/') + "/api/health"

        if (!hasNetwork(context)) {
            // A USB-tethered phone with mobile data off genuinely has no
            // transport, yet `adb reverse` still works - so this is a warning
            // about the likely cause, not a reason to skip the attempt.
            val loopback = normalised.contains("127.0.0.1") || normalised.contains("localhost")
            if (!loopback) {
                return@withContext Result.Failed(
                    "This phone has no network connection",
                    "Turn on Wi-Fi, or connect by USB and use the \"USB cable\" preset.",
                )
            }
        }

        if (normalised.contains("10.0.2.2")) {
            // Worth catching explicitly: it looks like an ordinary timeout and
            // costs people a lot of time to work out.
            val emulator = SettingsStore.isEmulator()
            if (!emulator) {
                return@withContext Result.Failed(
                    "10.0.2.2 only works on the emulator",
                    "On a real phone use the \"USB cable\" preset (with " +
                        "adb reverse tcp:8010 tcp:8010), or enter your laptop's " +
                        "Wi-Fi IP address.",
                )
            }
        }

        val client = OkHttpClient.Builder()
            .connectTimeout(6, TimeUnit.SECONDS)
            .readTimeout(6, TimeUnit.SECONDS)
            .build()

        val started = System.currentTimeMillis()
        try {
            val result = withTimeoutOrNull(12_000) {
                client.newCall(Request.Builder().url(target).build()).execute().use { response ->
                    if (!response.isSuccessful) {
                        return@use Result.Failed(
                            "Server answered with HTTP ${response.code}",
                            "Something is listening on that address, but it is not " +
                                "the SevakAI backend.",
                        )
                    }
                    val body = response.body?.string().orEmpty()
                    val health = runCatching {
                        `in`.sevakai.app.data.remote.ApiClient.json
                            .decodeFromString<HealthDto>(body)
                    }.getOrNull()
                        ?: return@use Result.Failed(
                            "Unexpected reply from that address",
                            "Reachable, but it did not answer like the SevakAI backend.",
                        )

                    Result.Ok(
                        llmReady = health.llmReady,
                        guidelineChunks = health.guidelineChunks,
                        patients = health.patients,
                        latencyMs = System.currentTimeMillis() - started,
                    )
                }
            }
            result ?: Result.Failed(
                "The server did not answer in time",
                "It may be starting up, or blocked by a firewall.",
            )
        } catch (e: UnknownHostException) {
            Result.Failed(
                "That address could not be found",
                "Check the IP address is typed correctly.",
            )
        } catch (e: ConnectException) {
            Result.Failed(
                "Nothing is listening on that address",
                "Check the backend is running with --host 0.0.0.0, and that your " +
                    "laptop firewall allows port 8010.",
            )
        } catch (e: SocketTimeoutException) {
            Result.Failed(
                "Timed out reaching the server",
                "The phone and laptop may be on different networks, or a firewall " +
                    "is dropping the connection.",
            )
        } catch (e: Exception) {
            Result.Failed(
                e.message ?: e.javaClass.simpleName,
                "Check the address and that the backend is running.",
            )
        }
    }

    private fun hasNetwork(context: Context): Boolean {
        val manager = context.getSystemService(ConnectivityManager::class.java) ?: return false
        val capabilities = manager.getNetworkCapabilities(manager.activeNetwork) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

}
