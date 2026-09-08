package `in`.sevakai.app.data.remote

import `in`.sevakai.app.BuildConfig
import `in`.sevakai.app.data.SessionStore
import `in`.sevakai.app.data.SettingsStore
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.Retrofit
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Raised when the token is gone or rejected, so the UI can send the worker back to sign-in. */
class UnauthorizedException : IOException("Session expired")

object ApiClient {

    val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
        encodeDefaults = true
    }

    fun create(session: SessionStore, settings: SettingsStore): ApiService {
        // Retrofit needs a base URL at construction time, but the real
        // destination is a runtime setting - the same APK runs against an
        // emulator, a USB-tethered phone and a laptop on the LAN. So the base
        // URL below is only a placeholder, and this interceptor rewrites the
        // scheme, host and port of every request from the stored setting.
        val rewriteHost = Interceptor { chain ->
            val configured = runBlocking { settings.current() }.toHttpUrlOrNull()
            var request = chain.request()
            if (configured != null) {
                val url = request.url.newBuilder()
                    .scheme(configured.scheme)
                    .host(configured.host)
                    .port(configured.port)
                    .build()
                request = request.newBuilder().url(url).build()
            }
            chain.proceed(request)
        }

        val auth = Interceptor { chain ->
            val token = runBlocking { session.token() }
            val request = chain.request().newBuilder().apply {
                if (!token.isNullOrBlank()) header("Authorization", "Bearer $token")
            }.build()

            val response: Response = chain.proceed(request)
            if (response.code == 401) {
                response.close()
                // Distinguish "your session ended" from "you are offline".
                // Conflating the two was a real source of confusion: a worker
                // in a dead zone was being told to sign in again.
                throw UnauthorizedException()
            }
            response
        }

        val client = OkHttpClient.Builder()
            .addInterceptor(rewriteHost)
            .addInterceptor(auth)
            // The pipeline runs three LLM calls, so a visit legitimately takes
            // several seconds. A short read timeout would abandon work the
            // server is about to finish.
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .writeTimeout(120, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .apply {
                if (BuildConfig.DEBUG) {
                    addInterceptor(
                        okhttp3.logging.HttpLoggingInterceptor().apply {
                            level = okhttp3.logging.HttpLoggingInterceptor.Level.BASIC
                        }
                    )
                }
            }
            .build()

        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(ApiService::class.java)
    }
}
