package `in`.sevakai.app.speech

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import `in`.sevakai.app.ui.i18n.EnglishStrings
import `in`.sevakai.app.ui.i18n.Strings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

private const val TAG = "SevakSpeech"

/**
 * Dictation using Android's own recogniser.
 *
 * Chosen over a cloud STT API for three reasons: it is free with no key, it
 * handles Hindi and Indian English natively, and on most devices it keeps
 * working with the network off once the language pack is downloaded - which is
 * exactly the situation this app is built for.
 *
 * Partial results are surfaced as they arrive so the worker can see their
 * words appearing and knows the mic is actually listening.
 */
class SpeechController(private val context: Context) {

    data class State(
        val available: Boolean = false,
        val listening: Boolean = false,
        val partial: String = "",
        val finalText: String = "",
        /** Loudness 0..1, drives the mic animation. */
        val amplitude: Float = 0f,
        val error: String? = null,
        val offlineCapable: Boolean = false,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state

    private var recognizer: SpeechRecognizer? = null
    private var strings: Strings = EnglishStrings

    fun isAvailable(): Boolean = SpeechRecognizer.isRecognitionAvailable(context)

    fun start(languageTag: String, strings: Strings) {
        this.strings = strings
        if (!isAvailable()) {
            _state.value = _state.value.copy(
                available = false,
                error = strings.speechUnavailable,
            )
            return
        }

        stop()
        val speech = SpeechRecognizer.createSpeechRecognizer(context)
        recognizer = speech

        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
            )
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, languageTag)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
            // A worker describing a visit pauses to think. Default endpointing
            // cuts them off mid-sentence, so the silence windows are widened.
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 3000L)
            putExtra(
                RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS,
                3000L,
            )
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 2000L)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                putExtra(RecognizerIntent.EXTRA_ENABLE_LANGUAGE_SWITCH, "true")
            }
        }

        speech.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                _state.value = _state.value.copy(
                    available = true, listening = true, error = null,
                )
            }

            override fun onBeginningOfSpeech() = Unit

            override fun onRmsChanged(rmsdB: Float) {
                // Reported roughly -2..10 dB; normalise for the meter.
                val level = ((rmsdB + 2f) / 12f).coerceIn(0f, 1f)
                _state.value = _state.value.copy(amplitude = level)
            }

            override fun onBufferReceived(buffer: ByteArray?) = Unit

            override fun onEndOfSpeech() {
                _state.value = _state.value.copy(listening = false, amplitude = 0f)
            }

            override fun onError(error: Int) {
                val message = describe(error)
                Log.i(TAG, "Recognition error $error: $message")
                _state.value = _state.value.copy(
                    listening = false,
                    amplitude = 0f,
                    // A no-match after the worker clearly said something is
                    // noise, not a failure worth shouting about.
                    error = if (error == SpeechRecognizer.ERROR_NO_MATCH &&
                        _state.value.finalText.isNotBlank()
                    ) null else message,
                )
            }

            override fun onResults(results: Bundle?) {
                val text = results
                    ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull()
                    .orEmpty()
                val combined = listOf(_state.value.finalText, text)
                    .filter { it.isNotBlank() }
                    .joinToString(" ")
                _state.value = _state.value.copy(
                    listening = false,
                    partial = "",
                    finalText = combined,
                    amplitude = 0f,
                )
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val text = partialResults
                    ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull()
                    .orEmpty()
                if (text.isNotBlank()) {
                    _state.value = _state.value.copy(partial = text)
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) = Unit
        })

        _state.value = _state.value.copy(available = true, error = null)
        speech.startListening(intent)
    }

    fun stop() {
        recognizer?.let {
            runCatching { it.stopListening() }
            runCatching { it.destroy() }
        }
        recognizer = null
        _state.value = _state.value.copy(listening = false, amplitude = 0f)
    }

    fun setText(text: String) {
        _state.value = _state.value.copy(finalText = text, partial = "")
    }

    fun reset() {
        stop()
        _state.value = State(available = isAvailable())
    }

    private fun describe(error: Int): String = when (error) {
        SpeechRecognizer.ERROR_AUDIO -> strings.speechNoMic
        SpeechRecognizer.ERROR_CLIENT -> strings.speechStopped
        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> strings.speechPermission
        SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT ->
            strings.speechNoNetwork
        SpeechRecognizer.ERROR_NO_MATCH -> strings.speechNoMatch
        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> strings.speechBusy
        SpeechRecognizer.ERROR_SERVER -> strings.speechServerError
        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> strings.speechTimeout
        else -> strings.speechFailed
    }
}
