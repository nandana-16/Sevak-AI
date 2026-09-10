package `in`.sevakai.app.ui.settings

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.sevakai.app.data.ConnectionCheck
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.SettingsStore
import `in`.sevakai.app.ui.i18n.stringsFor
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ServerSettingsViewModel(
    private val repository: Repository,
    private val context: Context,
) : ViewModel() {

    data class State(
        val input: String = "",
        val testing: Boolean = false,
        val saved: Boolean = false,
        val result: ConnectionCheck.Result? = null,
    ) {
        val resolved: String get() = SettingsStore.normalise(input)
        val resolvedLabel: String get() = SettingsStore.describe(resolved)
        val isUsb: Boolean get() = resolved == SettingsStore.USB
        val isEmulator: Boolean get() = resolved == SettingsStore.EMULATOR
        val isCustom: Boolean get() = !isUsb && !isEmulator
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    private var language: String = "hi"

    init {
        viewModelScope.launch {
            _state.value = _state.value.copy(
                input = SettingsStore.describe(repository.settings.current())
            )
        }
        viewModelScope.launch {
            repository.settings.language.collect { language = it }
        }
    }

    fun onInputChange(value: String) {
        _state.value = _state.value.copy(input = value, saved = false, result = null)
    }

    fun usePreset(url: String) {
        _state.value = _state.value.copy(
            input = SettingsStore.describe(url), saved = false, result = null,
        )
    }

    fun useCustom() {
        // Clear a preset so the field is ready for a typed address, rather
        // than making someone delete "127.0.0.1:8010" first.
        if (!_state.value.isCustom) {
            _state.value = _state.value.copy(input = "", saved = false, result = null)
        }
    }

    fun test() {
        val target = _state.value.resolved
        _state.value = _state.value.copy(testing = true, result = null, saved = false)
        viewModelScope.launch {
            val result = ConnectionCheck.run(context, target, stringsFor(language))
            _state.value = _state.value.copy(testing = false, result = result)
            // A working address is worth keeping without a second tap.
            if (result is ConnectionCheck.Result.Ok) {
                repository.settings.setServerUrl(target)
                _state.value = _state.value.copy(saved = true)
            }
        }
    }

    fun save() {
        val target = _state.value.resolved
        viewModelScope.launch {
            repository.settings.setServerUrl(target)
            _state.value = _state.value.copy(saved = true)
        }
    }

    companion object {
        fun factory(repository: Repository, context: Context) =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    ServerSettingsViewModel(repository, context) as T
            }
    }
}
