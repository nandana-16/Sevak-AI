package `in`.sevakai.app.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.SettingsStore
import `in`.sevakai.app.ui.i18n.Strings
import `in`.sevakai.app.ui.i18n.stringsFor
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.IOException

class LoginViewModel(private val repository: Repository) : ViewModel() {

    data class State(
        val phone: String = "",
        val pin: String = "",
        val loading: Boolean = false,
        val error: String? = null,
        val serverLabel: String = "",
        val language: String = "hi",
    ) {
        val canSubmit: Boolean get() = phone.length >= 10 && pin.length >= 4
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    /** Errors are built here, so this view model needs the table too. */
    private val strings: Strings get() = stringsFor(_state.value.language)

    init {
        viewModelScope.launch {
            repository.settings.serverUrl.collect { url ->
                _state.value = _state.value.copy(serverLabel = SettingsStore.describe(url))
            }
        }
        viewModelScope.launch {
            repository.settings.language.collect { code ->
                _state.value = _state.value.copy(language = code)
            }
        }
    }

    /**
     * One setting drives both the interface and the speech recogniser. A
     * worker who chose Hindi expects the mic to listen in Hindi too, and
     * making that a second, separate choice would be a trap.
     */
    fun setLanguage(code: String) {
        _state.value = _state.value.copy(language = code, error = null)
        viewModelScope.launch { repository.settings.setLanguage(code) }
    }

    fun onPhoneChange(value: String) {
        _state.value = _state.value.copy(
            phone = value.filter(Char::isDigit).take(10),
            error = null,
        )
    }

    fun onPinChange(value: String) {
        _state.value = _state.value.copy(
            pin = value.filter(Char::isDigit).take(6),
            error = null,
        )
    }

    fun submit() {
        val current = _state.value
        if (!current.canSubmit || current.loading) return

        _state.value = current.copy(loading = true, error = null)
        viewModelScope.launch {
            val result = repository.login(current.phone, current.pin)
            _state.value = _state.value.copy(
                loading = false,
                error = result.exceptionOrNull()?.let(::describe),
            )
            // On success the session flow changes and the nav host moves us on.
        }
    }

    private fun describe(error: Throwable): String = when {
        error.message?.contains("401") == true -> strings.signInWrongPin
        // Name the address that failed. "Cannot reach the server" sends people
        // hunting through the backend; the address usually IS the problem,
        // especially the first time on a real phone.
        error is IOException -> strings.signInUnreachable(_state.value.serverLabel)
        else -> strings.signInFailed(error.message.orEmpty())
    }

    companion object {
        fun factory(repository: Repository) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                LoginViewModel(repository) as T
        }
    }
}
