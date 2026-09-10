package `in`.sevakai.app.speech

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import android.util.Log
import `in`.sevakai.app.ui.i18n.EnglishStrings
import `in`.sevakai.app.ui.i18n.Strings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private const val TAG = "SevakRecorder"

/**
 * Plain audio capture, for when on-device recognition cannot run - no language
 * pack installed, or a device whose recogniser needs a network it does not
 * have. The file is queued and transcribed on the server later.
 *
 * AAC in an MP4 container at 32 kbps mono: roughly 240 KB per minute, which
 * matters when a day's queue has to go up over a weak rural connection.
 */
class AudioRecorder(private val context: Context) {

    data class State(
        val recording: Boolean = false,
        val elapsedMs: Long = 0,
        val amplitude: Float = 0f,
        val file: File? = null,
        val error: String? = null,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state

    private var recorder: MediaRecorder? = null
    private var outputFile: File? = null
    private var startedAt: Long = 0
    private var strings: Strings = EnglishStrings

    private fun queueDir(): File =
        File(context.filesDir, "visit_audio").apply { mkdirs() }

    fun start(strings: Strings): Boolean {
        this.strings = strings
        stop()
        return try {
            val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val file = File(queueDir(), "visit_$stamp.m4a")

            val recorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                MediaRecorder(context)
            } else {
                @Suppress("DEPRECATION")
                MediaRecorder()
            }
            recorder.apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setAudioChannels(1)
                setAudioSamplingRate(16_000)
                setAudioEncodingBitRate(32_000)
                setOutputFile(file.absolutePath)
                prepare()
                start()
            }

            this.recorder = recorder
            this.outputFile = file
            this.startedAt = System.currentTimeMillis()
            _state.value = State(recording = true, file = file)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Could not start recording", e)
            _state.value = State(error = strings.couldNotStartRecording(e.message.orEmpty()))
            false
        }
    }

    /** Call periodically while recording to drive the level meter and timer. */
    fun tick() {
        val active = recorder ?: return
        val amplitude = runCatching { active.maxAmplitude / 12_000f }.getOrDefault(0f)
        _state.value = _state.value.copy(
            elapsedMs = System.currentTimeMillis() - startedAt,
            amplitude = amplitude.coerceIn(0f, 1f),
        )
    }

    /** Returns the finished recording, or null if nothing usable was captured. */
    fun stop(): File? {
        val active = recorder ?: return outputFile
        recorder = null
        return try {
            active.stop()
            active.release()
            val file = outputFile
            _state.value = _state.value.copy(recording = false, amplitude = 0f, file = file)
            file?.takeIf { it.exists() && it.length() > 1024 }
        } catch (e: Exception) {
            // stop() throws when the clip is too short to have written a valid
            // MP4 header. That file is unusable, so discard it rather than
            // queueing something the server can never transcribe.
            Log.w(TAG, "Recording too short or invalid: ${e.message}")
            runCatching { active.release() }
            outputFile?.delete()
            _state.value = State(error = strings.recordingTooShort)
            null
        }
    }

    fun discard() {
        stop()
        outputFile?.delete()
        outputFile = null
        _state.value = State()
    }

    fun reset() {
        recorder?.let { runCatching { it.release() } }
        recorder = null
        outputFile = null
        _state.value = State()
    }
}
