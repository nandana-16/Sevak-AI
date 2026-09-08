package `in`.sevakai.app.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.SettingsStore
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
    ) {
        val canSubmit: Boolean get() = phone.length >= 10 && pin.length >= 4
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            repository.settings.serverUrl.collect { url ->
                _state.value = _state.value.copy(serverLabel = SettingsStore.describe(url))
            }
        }
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
        error.message?.contains("401") == true ->
            "Incorrect phone number or PIN."
        error is IOException ->
            // Name the address that failed. "Cannot reach the server" sends
            // people hunting through the backend; the address usually IS the
            // problem, especially the first time on a real phone.
            "Cannot reach ${_state.value.serverLabel}. Tap \"Server\" below to " +
                "check the address, or test the connection."
        else -> "Could not sign in. ${error.message.orEmpty()}".trim()
    }

    companion object {
        fun factory(repository: Repository) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                LoginViewModel(repository) as T
        }
    }
}
