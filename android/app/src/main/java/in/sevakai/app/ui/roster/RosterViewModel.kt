package `in`.sevakai.app.ui.roster

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.sevakai.app.data.PatientRow
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.remote.UnauthorizedException
import `in`.sevakai.app.ui.i18n.stringsFor
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/** The roster filters. Kept as one object so a change reloads once, not twice. */
data class RosterFilters(
    val search: String = "",
    val village: String? = null,
    val category: String? = null,
    val risk: String? = null,
    val dueOnly: Boolean = false,
) {
    val activeCount: Int
        get() = listOfNotNull(village, category, risk).size + if (dueOnly) 1 else 0
}

class RosterViewModel(private val repository: Repository) : ViewModel() {

    data class State(
        val patients: List<PatientRow> = emptyList(),
        val villages: List<String> = emptyList(),
        val filters: RosterFilters = RosterFilters(),
        val loading: Boolean = true,
        val fromCache: Boolean = false,
        val error: String? = null,
        val workerName: String = "",
        val village: String? = null,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    val unsyncedCount: StateFlow<Int> = repository.unsyncedCount
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 0)

    private var searchJob: kotlinx.coroutines.Job? = null
    private var language: String = "hi"

    init {
        viewModelScope.launch {
            repository.session.session.collect { session ->
                _state.value = _state.value.copy(
                    workerName = session?.workerName.orEmpty(),
                    village = session?.village,
                )
            }
        }
        viewModelScope.launch {
            repository.settings.language.collect { language = it }
        }
        load()
        viewModelScope.launch {
            runCatching { repository.villages() }
                .onSuccess { _state.value = _state.value.copy(villages = it) }
        }
    }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            val filters = _state.value.filters
            try {
                val result = repository.roster(
                    search = filters.search,
                    village = filters.village,
                    category = filters.category,
                    risk = filters.risk,
                    dueOnly = filters.dueOnly,
                )
                _state.value = _state.value.copy(
                    patients = result.patients,
                    fromCache = result.fromCache,
                    loading = false,
                )
            } catch (e: UnauthorizedException) {
                repository.logout()
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = e.message ?: stringsFor(language).couldNotLoadRoster,
                )
            }
        }
    }

    fun onSearchChange(value: String) {
        _state.value = _state.value.copy(filters = _state.value.filters.copy(search = value))
        // Typing on a slow connection should not fire a request per keystroke.
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            kotlinx.coroutines.delay(300)
            load()
        }
    }

    fun toggleVillage(value: String?) = update { copy(village = if (village == value) null else value) }
    fun toggleCategory(value: String?) = update { copy(category = if (category == value) null else value) }
    fun toggleRisk(value: String?) = update { copy(risk = if (risk == value) null else value) }
    fun toggleDueOnly() = update { copy(dueOnly = !dueOnly) }
    fun clearFilters() = update { RosterFilters(search = search) }

    private fun update(block: RosterFilters.() -> RosterFilters) {
        _state.value = _state.value.copy(filters = _state.value.filters.block())
        load()
    }

    fun signOut() {
        viewModelScope.launch { repository.logout() }
    }

    companion object {
        fun factory(repository: Repository) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                RosterViewModel(repository) as T
        }
    }
}
