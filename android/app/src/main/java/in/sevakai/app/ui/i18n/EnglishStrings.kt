package `in`.sevakai.app.ui.i18n

object EnglishStrings : Strings {

    override val languageName = "English"

    override val appName = "SevakAI"
    override val appTagline = "For ASHA workers"
    override val loading = "Loading…"
    override val back = "Back"
    override val done = "Done"
    override val cancel = "Cancel"
    override val retry = "Try again"
    override val offlineBanner = "You are offline. Showing the last saved copy."
    override val notRecorded = "—"

    override val riskRedAction = "Go to hospital today"
    override val riskAmberAction = "See a doctor soon"
    override val riskGreenAction = "Healthy"
    override val riskUnknownAction = "Not assessed"
    override val riskRedShort = "High risk"
    override val riskAmberShort = "Medium"
    override val riskGreenShort = "Healthy"
    override val riskUnknownShort = "New"

    override val categoryPregnant = "Pregnant"
    override val categoryInfant = "Infant"
    override val categoryChild = "Child"
    override val categoryPostnatal = "Postnatal"
    override val categoryAdult = "Adult"
    override val categoryElderly = "Elderly"

    override val chooseLanguage = "Choose your language"
    override val phoneNumber = "Phone number"
    override val pin = "4-digit PIN"
    override val signIn = "Sign in"
    override val demoSignIn = "Demo sign-in\n9000000002  ·  PIN 1234"
    override val serverLabel = { address: String -> "Server: $address" }
    override val signInWrongPin = "Incorrect phone number or PIN."
    override val signInUnreachable = { address: String ->
        "Cannot reach $address. Tap \"Server\" below to check the address, " +
            "or test the connection."
    }
    override val signInFailed = { detail: String -> "Could not sign in. $detail".trim() }

    override val myPatients = "My patients"
    override val searchHint = "Search by name or village"
    override val visitPlan = "Visit plan"
    override val syncQueue = "Sync queue"
    override val serverSettings = "Server settings"
    override val signOut = "Sign out"
    override val filterDueNow = "Due now"
    override val filterHighRisk = "High risk"
    override val filterWatch = "Medium"
    override val patientCount = { n: Int -> "$n patient${if (n == 1) "" else "s"}" }
    override val loadingPatients = "Loading your patients…"
    override val rosterOffline = "You are offline. Showing the last saved copy of your roster."
    override val noMatchingPatients = "No matching patients"
    override val noMatchingPatientsBody =
        "Try clearing the filters or searching a different name."
    override val noPatientsYet = "No patients assigned yet"
    override val noPatientsYetBody =
        "Patients assigned to you by your ANM will appear here."
    override val lastVisitPrefix = { summary: String -> "Last visit: $summary" }
    override val nextVisitDue = { date: String -> "Next visit due $date" }

    override val patientProfile = "Patient profile"
    override val profileOffline = "Offline — showing the copy saved on this phone."
    override val couldNotOpenProfile = "Could not open this profile"
    override val couldNotOpenProfileBody = "Please try again when you have a connection."
    override val openingProfile = "Opening profile…"
    override val sectionLastVisit = "Last visit"
    override val sectionDetails = "Details"
    override val dateOfBirth = "Date of birth"
    override val bloodGroup = "Blood group"
    override val phone = "Phone"
    override val household = "Household"
    override val address = "Address"
    override val guardian = "Guardian"
    override val aadhaarLine = { masked: String -> "Aadhaar $masked" }
    override val aadhaarVerified = "Verified offline at registration"
    override val aadhaarNotLinked = "Not linked"
    override val sectionPregnancy = "Pregnancy"
    override val gestation = "Gestation"
    override val weeksSuffix = { weeks: Int -> "$weeks weeks" }
    override val dueDate = "Due date"
    override val gravidaPara = "Gravida / Para"
    override val ancVisits = "ANC visits"
    override val ancVisitsValue = { done: Int -> "$done of 4" }
    override val lastHb = "Last Hb"
    override val lastBp = "Last BP"
    override val ttDoses = "TT doses"
    override val ifaTablets = "IFA tablets"
    override val plannedDelivery = "Planned delivery"
    override val highRiskFactors = "High-risk factors"
    override val sectionNewborn = "Newborn details"
    override val birthWeight = "Birth weight"
    override val bornAt = "Born at"
    override val currentWeight = "Current weight"
    override val muac = "MUAC"
    override val delivery = "Delivery"
    override val feeding = "Feeding"
    override val exclusiveBreastfeeding = "Exclusive breastfeeding"
    override val mixedFeeding = "Mixed feeding"
    override val sectionImmunisation = "Immunisation"
    override val givenCount = { n: Int -> "$n given" }
    override val overdueCount = { n: Int -> "$n overdue" }
    override val comingUp = "Coming up"
    override val immunisationComplete = "Immunisation schedule is complete."
    override val dueOn = { date: String -> "Due $date" }
    override val markGiven = "Mark given"
    override val sectionMedicalHistory = "Medical history"
    override val ongoing = "Ongoing"
    override val pastHistory = "Past"
    override val sinceDate = { date: String -> "  (since $date)" }
    override val sectionPreviousVisits = "Previous visits"
    override val recordVisit = "Record visit"

    override val recordVisitTitle = "Record visit"
    override val tabSpeak = "Speak"
    override val tabType = "Type"
    override val micPrompt = "Tap the mic and describe the visit in your own words."
    override val micListening = "Listening… speak naturally, then tap to stop."
    override val micRecording = { seconds: Long -> "Recording… ${seconds}s. Tap to stop." }
    override val micTapToAdd = "Tap the mic to add more."
    override val recordForLater = "Record audio for later"
    override val recordForLaterHint =
        "Use this where speech recognition will not work without a network."
    override val recordingSaved = { seconds: Long -> "Recording saved (${seconds}s)" }
    override val recordingSavedHint = "It will be transcribed when this visit is sent."
    override val discardRecording = "Discard recording"
    override val whatWasHeard = "What was heard"
    override val whatWasHeardHint = "Correct anything that came out wrong before saving."
    override val sectionMeasurements = "Measurements"
    override val measurementsHint = "Anything you type here is used exactly as entered."
    override val visitNotes = "Visit notes"
    override val extraNotes = "Extra notes (optional)"
    override val notesPlaceholder =
        "What did you observe? Symptoms, advice given, anything unusual."
    override val saveVisit = "Save visit"
    override val analysing = "Analysing…"
    override val offlineSaveHint =
        "If there is no network, the visit is saved on this phone and sent later."
    override val queuedMessage =
        "Saved on this phone. It will be sent automatically when you have a network."
    override val correctMeasurements = "Please correct the highlighted measurements."
    override val couldNotSaveVisit = "Could not save the visit"
    override val enterANumber = "Enter a number"
    override val expectedRange = { min: Double, max: Double -> "Expected $min–$max" }

    override val vitalTemperature = "Temperature"
    override val vitalBpSystolic = "BP systolic"
    override val vitalBpDiastolic = "BP diastolic"
    override val vitalPulse = "Pulse"
    override val vitalWeight = "Weight"
    override val vitalHaemoglobin = "Haemoglobin"
    override val vitalSpo2 = "SpO₂"
    override val vitalMuac = "MUAC"

    override val visitResult = "Visit result"
    override val couldNotLoadVisit = "Could not load this visit"
    override val couldNotLoadVisitBody = "Try again when you have a connection."
    override val degradedWarning = { steps: String ->
        "Part of this was worked out by fixed rules, not the AI model ($steps). " +
            "Please review it yourself."
    }
    override val visitFailed = "This visit could not be analysed automatically."
    override val dangerSignsFound = "Danger signs found"
    override val whatToDoNow = "What to do now"
    override val nextVisit = "Next visit"
    override val nextVisitAuto = "Added to your visit plan automatically."
    override val recordedInThisVisit = "Recorded in this visit"
    override val noFindings = "No specific findings were picked up."
    override val basedOnGuidelines = "Based on NHM guidelines"
    override val passagesCount = { n: Int ->
        "$n passage${if (n == 1) "" else "s"} from official documents"
    }
    override val show = "Show"
    override val hide = "Hide"
    override val pageLabel = { page: Int -> "page $page" }
    override val urgencyNow = "Right now"
    override val urgencyToday = "Today"
    override val urgencyThisWeek = "This week"
    override val urgencyRoutine = "Routine"

    override val visitPlanTitle = "Visit plan"
    override val visitPlanSubtitle = "Scheduled from each visit's risk level"
    override val rangeDueNow = "Due now"
    override val rangeNext7 = "Next 7 days"
    override val rangeNext30 = "Next 30 days"
    override val loadingPlan = "Loading your plan…"
    override val planOffline = "Offline — showing your last saved plan."
    override val nothingScheduled = "Nothing scheduled"
    override val nothingScheduledBody =
        "Follow-ups appear here automatically after you record a visit."
    override val overdueHeading = { n: Int -> "Overdue ($n)" }
    override val upcoming = "Upcoming"
    override val dueOnDate = { date: String -> "Due $date" }
    override val snoozeOneDay = "Nobody home — push 1 day"

    override val queueTitle = "Visit queue"
    override val queueAllSent = "Everything is sent"
    override val queueWaiting = { n: Int -> "$n waiting to be sent" }
    override val queueNothingWaiting = "Nothing waiting"
    override val queueNothingWaitingBody =
        "Visits you record without a network are held here and sent " +
            "automatically once you are back in signal."
    override val queueExplainer =
        "Visits are sent automatically. Nothing is lost if you close the app " +
            "or the phone restarts."
    override val trySendingNow = "Try sending now"
    override val sending = "Sending…"
    override val statusWaiting = "Waiting for network"
    override val statusSending = "Sending…"
    override val statusSent = "Sent"
    override val statusWillRetry = "Will retry"
    override val queueVoiceRecording = "Voice recording, to be transcribed on the server"
    override val queueMeasurementsOnly = "Measurements only"
    override val attemptLabel = { n: Int, error: String -> "Attempt $n: $error" }

    override val registerPatient = "Register patient"
    override val sectionAadhaar = "Aadhaar verification"
    override val aadhaarExplainer =
        "The number is checked for validity on this phone. Only the last 4 " +
            "digits and a one-way code are stored — never the full number."
    override val aadhaarNumber = "Aadhaar number"
    override val aadhaarPlaceholder = "XXXX XXXX XXXX"
    override val aadhaarConsent = "The patient has agreed to link their Aadhaar"
    override val aadhaarValidMessage = { last4: String ->
        "Verified. Only ending $last4 will be stored."
    }
    override val aadhaarOfflineMessage =
        "Could not check the number while offline. Registration needs a connection."
    override val sectionPatientDetails = "Patient details"
    override val fullName = "Full name"
    override val genderFemale = "Female"
    override val genderMale = "Male"
    override val genderOther = "Other"
    override val dobPlaceholder = "YYYY-MM-DD"
    override val phoneOptional = "Phone (optional)"
    override val sectionCategory = "Category"
    override val categoryHint = "This decides which schedule and guidelines apply."
    override val lastMenstrualPeriod = "Last menstrual period"
    override val lmpHint = "Used to work out the due date and the ANC visit schedule."
    override val birthWeightKg = "Birth weight (kg)"
    override val infantScheduleHint =
        "The full national immunisation schedule is created automatically " +
            "from the date of birth."
    override val registerButton = "Register patient"
    override val dateFormatError = "Use the format YYYY-MM-DD"
    override val dateFutureError = "Date cannot be in the future"
    override val registerFailed = "Could not register. Registration needs a connection."

    override val serverTitle = "Server"
    override val serverSubtitle = "Where this app sends visits"
    override val howConnected = "How is this phone connected?"
    override val presetUsb = "USB cable"
    override val presetUsbHint = "127.0.0.1:8010 — run  adb reverse tcp:8010 tcp:8010"
    override val presetEmulator = "Emulator"
    override val presetEmulatorHint = "10.0.2.2:8010 — only works on an emulator"
    override val presetWifi = "Same Wi-Fi"
    override val presetWifiHint = "Enter your laptop's IP address below"
    override val addressLabel = "Address"
    override val willConnectTo = { address: String -> "Will connect to  $address" }
    override val addressHint =
        "You can type just the IP — the port and http:// are added for you."
    override val testConnection = "Test connection"
    override val save = "Save"
    override val saved = "Saved."
    override val connected = "Connected"
    override val noLlmWarning =
        "The server is reachable but has no LLM configured. Visits will be " +
            "classified by rules only. Add GROQ_API_KEY to backend/.env."
    override val findingYourIp = "Finding your laptop's IP"
    override val findingYourIpBody =
        "Windows:  ipconfig  — look for IPv4 Address\n" +
            "macOS / Linux:  ifconfig | grep inet\n\n" +
            "The phone and laptop must be on the same Wi-Fi, and the backend " +
            "must be started with --host 0.0.0.0."

    override val speechUnavailable =
        "Speech recognition is not available on this phone. Please type the notes instead."
    override val speechNoMic = "Could not read the microphone."
    override val speechPermission = "Microphone permission is needed to record a visit."
    override val speechNoNetwork =
        "No network for speech recognition. Use \"Record for later\" instead."
    override val speechNoMatch = "Nothing was recognised. Please try again."
    override val speechBusy = "The recogniser is busy. Try again."
    override val speechServerError = "The speech service returned an error."
    override val speechTimeout = "No speech was heard."
    override val speechFailed = "Speech recognition failed."
    override val speechStopped = "Recognition stopped unexpectedly."
    override val recordingTooShort = "That recording was too short. Please hold the button longer."
    override val couldNotStartRecording = { detail: String -> "Could not start recording: $detail" }
    override val connOk = { ms: Long, patients: Int, chunks: Int ->
        "Connected in $ms ms · $patients patients · $chunks guideline chunks"
    }
    override val connNoNetwork = "This phone has no network connection"
    override val connNoNetworkHint =
        "Turn on Wi-Fi, or connect by USB and use the \"USB cable\" preset."
    override val connEmulatorOnly = "10.0.2.2 only works on the emulator"
    override val connEmulatorOnlyHint =
        "On a real phone use the \"USB cable\" preset (with " +
            "adb reverse tcp:8010 tcp:8010), or enter your laptop's Wi-Fi IP address."
    override val connHttpStatus = { code: Int -> "Server answered with HTTP $code" }
    override val connHttpStatusHint =
        "Something is listening on that address, but it is not the SevakAI backend."
    override val connUnexpectedReply = "Unexpected reply from that address"
    override val connUnexpectedReplyHint =
        "Reachable, but it did not answer like the SevakAI backend."
    override val connTimedOutSlow = "The server did not answer in time"
    override val connTimedOutSlowHint = "It may be starting up, or blocked by a firewall."
    override val connUnknownHost = "That address could not be found"
    override val connUnknownHostHint = "Check the IP address is typed correctly."
    override val connRefused = "Nothing is listening on that address"
    override val connRefusedHint =
        "Check the backend is running with --host 0.0.0.0, and that your laptop " +
            "firewall allows port 8010."
    override val connTimedOut = "Timed out reaching the server"
    override val connTimedOutHint =
        "The phone and laptop may be on different networks, or a firewall is " +
            "dropping the connection."
    override val connGenericHint = "Check the address and that the backend is running."
    override val noOfflineCopy =
        "This profile has not been opened before, so there is no offline copy."
    override val couldNotLoadRoster = "Could not load the roster"
}
