package `in`.sevakai.app.data

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import `in`.sevakai.app.data.remote.HealthDto
import `in`.sevakai.app.ui.i18n.Strings
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
            override val message: String,
        ) : Result

        data class Failed(
            override val message: String,
            val hint: String,
        ) : Result
    }

    suspend fun run(
        context: Context,
        url: String,
        strings: Strings,
    ): Result = withContext(Dispatchers.IO) {
        val normalised = SettingsStore.normalise(url)
        val target = normalised.trimEnd('/') + "/api/health"

        if (!hasNetwork(context)) {
            // A USB-tethered phone with mobile data off genuinely has no
            // transport, yet `adb reverse` still works - so this is a warning
            // about the likely cause, not a reason to skip the attempt.
            val loopback = normalised.contains("127.0.0.1") || normalised.contains("localhost")
            if (!loopback) {
                return@withContext Result.Failed(
                    strings.connNoNetwork,
                    strings.connNoNetworkHint,
                )
            }
        }

        if (normalised.contains("10.0.2.2")) {
            // Worth catching explicitly: it looks like an ordinary timeout and
            // costs people a lot of time to work out.
            val emulator = SettingsStore.isEmulator()
            if (!emulator) {
                return@withContext Result.Failed(
                    strings.connEmulatorOnly,
                    strings.connEmulatorOnlyHint,
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
                            strings.connHttpStatus(response.code),
                            strings.connHttpStatusHint,
                        )
                    }
                    val body = response.body?.string().orEmpty()
                    val health = runCatching {
                        `in`.sevakai.app.data.remote.ApiClient.json
                            .decodeFromString<HealthDto>(body)
                    }.getOrNull()
                        ?: return@use Result.Failed(
                            strings.connUnexpectedReply,
                            strings.connUnexpectedReplyHint,
                        )

                    val elapsed = System.currentTimeMillis() - started
                    Result.Ok(
                        llmReady = health.llmReady,
                        guidelineChunks = health.guidelineChunks,
                        patients = health.patients,
                        latencyMs = elapsed,
                        message = strings.connOk(
                            elapsed, health.patients, health.guidelineChunks,
                        ),
                    )
                }
            }
            result ?: Result.Failed(
                strings.connTimedOutSlow,
                strings.connTimedOutSlowHint,
            )
        } catch (e: UnknownHostException) {
            Result.Failed(
                strings.connUnknownHost,
                strings.connUnknownHostHint,
            )
        } catch (e: ConnectException) {
            Result.Failed(
                strings.connRefused,
                strings.connRefusedHint,
            )
        } catch (e: SocketTimeoutException) {
            Result.Failed(
                strings.connTimedOut,
                strings.connTimedOutHint,
            )
        } catch (e: Exception) {
            Result.Failed(
                e.message ?: e.javaClass.simpleName,
                strings.connGenericHint,
            )
        }
    }

    private fun hasNetwork(context: Context): Boolean {
        val manager = context.getSystemService(ConnectivityManager::class.java) ?: return false
        val capabilities = manager.getNetworkCapabilities(manager.activeNetwork) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

}
