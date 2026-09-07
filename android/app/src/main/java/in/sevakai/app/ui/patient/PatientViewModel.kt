package `in`.sevakai.app.ui.patient

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.remote.PatientDetailDto
import `in`.sevakai.app.data.remote.UnauthorizedException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class PatientViewModel(
    private val repository: Repository,
    private val patientId: String,
) : ViewModel() {

    data class State(
        val patient: PatientDetailDto? = null,
        val loading: Boolean = true,
        val fromCache: Boolean = false,
        val error: String? = null,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val result = repository.patient(patientId)
                _state.value = State(
                    patient = result.patient,
                    loading = false,
                    fromCache = result.fromCache,
                )
            } catch (e: UnauthorizedException) {
                repository.logout()
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = e.message ?: "Could not open this profile",
                )
            }
        }
    }

    fun markVaccinationGiven(vaccinationId: String) {
        viewModelScope.launch {
            runCatching {
                repository.api.markVaccinationGiven(patientId, vaccinationId)
            }.onSuccess { load() }
        }
    }

    companion object {
        fun factory(repository: Repository, patientId: String) =
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    PatientViewModel(repository, patientId) as T
            }
    }
}
