package `in`.sevakai.app.ui.register

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.sevakai.app.data.Repository
import `in`.sevakai.app.data.remote.PatientCreateRequest
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeParseException

class RegisterViewModel(private val repository: Repository) : ViewModel() {

    data class State(
        val aadhaarDisplay: String = "",
        val aadhaarDigits: String = "",
        val checkingAadhaar: Boolean = false,
        val aadhaarChecked: Boolean = false,
        val aadhaarValid: Boolean = false,
        val aadhaarMessage: String? = null,
        val consent: Boolean = false,
        val name: String = "",
        val gender: String = "female",
        val dob: String = "",
        val dobError: String? = null,
        val bloodGroup: String = "",
        val phone: String = "",
        val category: String = "adult",
        val lmp: String = "",
        val birthWeight: String = "",
        val submitting: Boolean = false,
        val error: String? = null,
        val createdId: String? = null,
    ) {
        val canSubmit: Boolean
            get() = name.trim().length >= 2 &&
                dobError == null &&
                // An Aadhaar is optional (infants often have none), but if one
                // was entered it must be valid and consented.
                (aadhaarDigits.isEmpty() || (aadhaarValid && consent))
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    private var checkJob: Job? = null

    fun onAadhaarChange(value: String) {
        val digits = value.filter(Char::isDigit).take(12)
        // Display in the familiar 4-4-4 grouping while keeping digits clean.
        val display = digits.chunked(4).joinToString(" ")
        _state.value = _state.value.copy(
            aadhaarDisplay = display,
            aadhaarDigits = digits,
            aadhaarChecked = false,
            aadhaarValid = false,
            aadhaarMessage = null,
        )

        checkJob?.cancel()
        if (digits.length == 12) {
            checkJob = viewModelScope.launch {
                delay(250)
                _state.value = _state.value.copy(checkingAadhaar = true)
                repository.checkAadhaar(digits)
                    .onSuccess { result ->
                        _state.value = _state.value.copy(
                            checkingAadhaar = false,
                            aadhaarChecked = true,
                            aadhaarValid = result.valid && !result.alreadyRegistered,
                            aadhaarMessage = if (result.valid && !result.alreadyRegistered) {
                                "Verified. Only ending ${result.last4} will be stored."
                            } else result.reason,
                        )
                    }
                    .onFailure {
                        _state.value = _state.value.copy(
                            checkingAadhaar = false,
                            aadhaarMessage = "Could not check the number while offline. " +
                                "Registration needs a connection.",
                        )
                    }
            }
        }
    }

    fun onConsentChange(value: Boolean) {
        _state.value = _state.value.copy(consent = value)
    }

    fun onNameChange(value: String) {
        _state.value = _state.value.copy(name = value, error = null)
    }

    fun onGenderChange(value: String) {
        _state.value = _state.value.copy(gender = value)
    }

    fun onDobChange(value: String) {
        _state.value = _state.value.copy(dob = value, dobError = validateDate(value))
    }

    fun onBloodGroupChange(value: String) {
        _state.value = _state.value.copy(bloodGroup = value.uppercase().take(3))
    }

    fun onPhoneChange(value: String) {
        _state.value = _state.value.copy(phone = value.filter(Char::isDigit).take(10))
    }

    fun onCategoryChange(value: String) {
        _state.value = _state.value.copy(category = value)
    }

    fun onLmpChange(value: String) {
        _state.value = _state.value.copy(lmp = value)
    }

    fun onBirthWeightChange(value: String) {
        _state.value = _state.value.copy(
            birthWeight = value.filter { it.isDigit() || it == '.' }
        )
    }

    private fun validateDate(value: String): String? {
        if (value.isBlank()) return null
        return try {
            val parsed = LocalDate.parse(value)
            if (parsed.isAfter(LocalDate.now())) "Date cannot be in the future" else null
        } catch (e: DateTimeParseException) {
            "Use the format YYYY-MM-DD"
        }
    }

    fun submit() {
        val current = _state.value
        if (!current.canSubmit || current.submitting) return

        _state.value = current.copy(submitting = true, error = null)
        viewModelScope.launch {
            repository.registerPatient(
                PatientCreateRequest(
                    name = current.name.trim(),
                    gender = current.gender,
                    dob = current.dob.takeIf { it.isNotBlank() && current.dobError == null },
                    bloodGroup = current.bloodGroup.takeIf { it.isNotBlank() },
                    phone = current.phone.takeIf { it.length == 10 },
                    category = current.category,
                    aadhaar = current.aadhaarDigits.takeIf { it.length == 12 },
                    aadhaarConsentGiven = current.consent,
                    lmp = current.lmp.takeIf {
                        current.category == "pregnant" && it.isNotBlank()
                    },
                    birthWeightKg = current.birthWeight.toDoubleOrNull()
                        ?.takeIf { current.category == "infant" },
                )
            ).onSuccess {
                _state.value = _state.value.copy(submitting = false, createdId = it.id)
            }.onFailure {
                _state.value = _state.value.copy(
                    submitting = false,
                    error = it.message
                        ?: "Could not register. Registration needs a connection.",
                )
            }
        }
    }

    companion object {
        fun factory(repository: Repository) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                RegisterViewModel(repository) as T
        }
    }
}
