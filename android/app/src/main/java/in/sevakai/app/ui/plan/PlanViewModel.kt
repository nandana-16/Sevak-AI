package `in`.sevakai.app.ui.plan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.ScheduleRow
import `in`.sevakai.app.data.remote.UnauthorizedException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class PlanViewModel(private val repository: Repository) : ViewModel() {

    data class State(
        val items: List<ScheduleRow> = emptyList(),
        val days: Int = 0,
        val loading: Boolean = true,
        val fromCache: Boolean = false,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    init {
        load()
    }

    fun setRange(days: Int) {
        _state.value = _state.value.copy(days = days)
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            try {
                val result = repository.schedule(_state.value.days)
                _state.value = _state.value.copy(
                    items = result.items,
                    fromCache = result.fromCache,
                    loading = false,
                )
            } catch (e: UnauthorizedException) {
                repository.logout()
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false)
            }
        }
    }

    fun snooze(id: String) {
        viewModelScope.launch {
            repository.snooze(id, 1)
            load()
        }
    }

    companion object {
        fun factory(repository: Repository) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                PlanViewModel(repository) as T
        }
    }
}
