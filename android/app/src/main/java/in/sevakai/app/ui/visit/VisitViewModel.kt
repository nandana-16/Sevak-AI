package `in`.sevakai.app.ui.visit

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.CreationExtras
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.SubmitResult
import `in`.sevakai.app.data.remote.PatientDetailDto
import `in`.sevakai.app.data.remote.UnauthorizedException
import `in`.sevakai.app.data.remote.VisitDetailDto
import `in`.sevakai.app.speech.AudioRecorder
import `in`.sevakai.app.speech.SpeechController
import `in`.sevakai.app.sync.SyncWorker
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** The measurements a worker can type directly. Kept in one list so the form,
 *  the payload and the validation cannot drift apart. */
data class VitalField(
    val key: String,
    val label: String,
    val suffix: String,
    val min: Double,
    val max: Double,
) {
    fun validate(raw: String): String? {
        if (raw.isBlank()) return null
        val value = raw.toDoubleOrNull() ?: return "Enter a number"
        if (value < min || value > max) return "Expected $min–$max"
        return null
    }
}

val VITAL_FIELDS = listOf(
    VitalField("temperature_c", "Temperature", "°C", 30.0, 45.0),
    VitalField("bp_systolic", "BP systolic", "mmHg", 50.0, 260.0),
    VitalField("bp_diastolic", "BP diastolic", "mmHg", 30.0, 180.0),
    VitalField("pulse", "Pulse", "/min", 30.0, 220.0),
    VitalField("weight_kg", "Weight", "kg", 0.5, 200.0),
    VitalField("hb", "Haemoglobin", "g/dL", 2.0, 20.0),
    VitalField("spo2", "SpO₂", "%", 50.0, 100.0),
    VitalField("muac_cm", "MUAC", "cm", 5.0, 30.0),
)

class VisitViewModel(
    application: Application,
    private val repository: Repository,
    private val patientId: String,
) : AndroidViewModel(application) {

    enum class Mode { VOICE, TYPE }

    data class State(
        val patient: PatientDetailDto? = null,
        val mode: Mode = Mode.VOICE,
        val transcript: String = "",
        val partial: String = "",
        val typedNotes: String = "",
        val vitals: Map<String, String> = emptyMap(),
        val vitalErrors: Map<String, String> = emptyMap(),
        val listening: Boolean = false,
        val recordingAudio: Boolean = false,
        val recordedMs: Long = 0,
        val amplitude: Float = 0f,
        val speechAvailable: Boolean = true,
        val speechError: String? = null,
        val language: String = "hi",
        val submitting: Boolean = false,
        val result: VisitDetailDto? = null,
        val queuedMessage: String? = null,
        val error: String? = null,
    ) {
        val hasContent: Boolean
            get() = transcript.isNotBlank() || typedNotes.isNotBlank() ||
                vitals.values.any { it.isNotBlank() } || recordedMs > 0
    }

    val speech = SpeechController(application)
    val recorder = AudioRecorder(application)

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    init {
        _state.value = _state.value.copy(speechAvailable = speech.isAvailable())

        viewModelScope.launch {
            runCatching { repository.patient(patientId) }
                .onSuccess { _state.value = _state.value.copy(patient = it.patient) }
        }
        viewModelScope.launch {
            repository.session.language.collect {
                _state.value = _state.value.copy(language = it)
            }
        }
        viewModelScope.launch {
            speech.state.collect { s ->
                _state.value = _state.value.copy(
                    listening = s.listening,
                    partial = s.partial,
                    transcript = if (s.finalText.isNotBlank()) s.finalText
                    else _state.value.transcript,
                    amplitude = if (s.listening) s.amplitude else _state.value.amplitude,
                    speechError = s.error,
                )
            }
        }
        viewModelScope.launch {
            recorder.state.collect { s ->
                _state.value = _state.value.copy(
                    recordingAudio = s.recording,
                    recordedMs = s.elapsedMs,
                    amplitude = if (s.recording) s.amplitude else _state.value.amplitude,
                )
            }
        }
    }

    fun setMode(mode: Mode) {
        if (mode != Mode.VOICE) stopListening()
        _state.value = _state.value.copy(mode = mode)
    }

    fun setLanguage(code: String) {
        _state.value = _state.value.copy(language = code)
        viewModelScope.launch { repository.session.setLanguage(code) }
    }

    // --- Voice --------------------------------------------------------------

    fun startListening() {
        val tag = if (_state.value.language == "en") "en-IN" else "hi-IN"
        speech.setText(_state.value.transcript)
        speech.start(tag)
    }

    fun stopListening() = speech.stop()

    fun onTranscriptChange(value: String) {
        // The worker can always correct what was heard before it is submitted.
        speech.setText(value)
        _state.value = _state.value.copy(transcript = value)
    }

    /** Offline capture: record raw audio, transcribe on the server later. */
    fun startRecording() {
        if (recorder.start()) {
            viewModelScope.launch {
                while (_state.value.recordingAudio) {
                    recorder.tick()
                    delay(120)
                }
            }
        }
    }

    fun stopRecording() = recorder.stop()

    fun discardRecording() = recorder.discard()

    // --- Typed --------------------------------------------------------------

    fun onNotesChange(value: String) {
        _state.value = _state.value.copy(typedNotes = value)
    }

    fun onVitalChange(key: String, value: String) {
        val cleaned = value.filter { it.isDigit() || it == '.' }
        val field = VITAL_FIELDS.first { it.key == key }
        val errors = _state.value.vitalErrors.toMutableMap()
        field.validate(cleaned)?.let { errors[key] = it } ?: errors.remove(key)
        _state.value = _state.value.copy(
            vitals = _state.value.vitals + (key to cleaned),
            vitalErrors = errors,
        )
    }

    // --- Submit -------------------------------------------------------------

    fun submit() {
        val current = _state.value
        if (current.submitting || !current.hasContent) return
        if (current.vitalErrors.isNotEmpty()) {
            _state.value = current.copy(error = "Please correct the highlighted measurements.")
            return
        }

        stopListening()
        val audio = if (current.recordingAudio) recorder.stop() else recorder.state.value.file

        val manual = current.vitals
            .mapNotNull { (key, raw) -> raw.toDoubleOrNull()?.let { key to it } }
            .toMap()

        val inputMode = when {
            audio != null && current.transcript.isBlank() -> "voice_offline"
            current.transcript.isNotBlank() -> "voice"
            else -> "typed"
        }

        _state.value = current.copy(submitting = true, error = null)
        viewModelScope.launch {
            try {
                val result = repository.submitVisit(
                    patientId = patientId,
                    patientName = current.patient?.name.orEmpty(),
                    transcript = current.transcript.takeIf { it.isNotBlank() },
                    typedNotes = current.typedNotes.takeIf { it.isNotBlank() },
                    manualFields = manual,
                    inputMode = inputMode,
                    language = current.language,
                    audioFile = audio,
                )
                when (result) {
                    is SubmitResult.Processed ->
                        _state.value = _state.value.copy(
                            submitting = false,
                            result = result.visit,
                        )

                    is SubmitResult.Queued -> {
                        // Make sure WorkManager will pick it up the moment
                        // signal returns.
                        SyncWorker.syncNow(getApplication())
                        _state.value = _state.value.copy(
                            submitting = false,
                            queuedMessage = "Saved on this phone. It will be sent " +
                                "automatically when you have a network.",
                        )
                    }
                }
            } catch (e: UnauthorizedException) {
                repository.logout()
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    submitting = false,
                    error = e.message ?: "Could not save the visit",
                )
            }
        }
    }

    override fun onCleared() {
        speech.reset()
        recorder.reset()
        super.onCleared()
    }

    companion object {
        fun factory(
            application: Application,
            repository: Repository,
            patientId: String,
        ) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(
                modelClass: Class<T>,
                extras: CreationExtras,
            ): T = VisitViewModel(application, repository, patientId) as T
        }
    }
}
