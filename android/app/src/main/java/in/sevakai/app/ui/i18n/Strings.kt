package `in`.sevakai.app.ui.i18n

import androidx.compose.runtime.staticCompositionLocalOf

/**
 * Every user-visible string in the app, in one place.
 *
 * Deliberately not Android's `values-hi/strings.xml`. Resource-based locales
 * are switched by the system, and changing one at runtime means recreating the
 * activity - which on this app would drop an in-progress visit, including a
 * recording that has not been uploaded yet. A worker who taps the wrong
 * language mid-round must not lose their work. Reading the language from a
 * CompositionLocal recomposes instantly and loses nothing.
 *
 * Translation rules followed here:
 *
 * * **Clinical abbreviations stay in Latin script** - BP, Hb, SpO2, MUAC, ANC,
 *   IFA, TT, EDD. These are what an ASHA worker is trained on and what is
 *   printed on the registers and cards she already carries. "रक्तचाप" would be
 *   a correct translation of blood pressure and the wrong word to put on this
 *   screen.
 * * **Numerals stay Arabic** (0-9), not Devanagari (०-९). Indian Hindi
 *   interfaces and government forms use Arabic numerals throughout.
 * * Plain, spoken Hindi over formal Sanskritised register: "ज़्यादा ख़तरा"
 *   rather than "उच्च जोखिम". The reader may have limited formal schooling.
 */
interface Strings {

    val languageName: String

    // --- Shared ------------------------------------------------------------
    val appName: String
    val appTagline: String
    val loading: String
    val back: String
    val done: String
    val cancel: String
    val retry: String
    val offlineBanner: String
    val notRecorded: String          // the em-dash placeholder

    // --- Risk levels -------------------------------------------------------
    val riskRedAction: String
    val riskAmberAction: String
    val riskGreenAction: String
    val riskUnknownAction: String
    val riskRedShort: String
    val riskAmberShort: String
    val riskGreenShort: String
    val riskUnknownShort: String

    // --- Categories --------------------------------------------------------
    val categoryPregnant: String
    val categoryInfant: String
    val categoryChild: String
    val categoryPostnatal: String
    val categoryAdult: String
    val categoryElderly: String

    // --- Sign in -----------------------------------------------------------
    val chooseLanguage: String
    val phoneNumber: String
    val pin: String
    val signIn: String
    val demoSignIn: String
    val serverLabel: (String) -> String
    val signInWrongPin: String
    val signInUnreachable: (String) -> String
    val signInFailed: (String) -> String

    // --- Roster ------------------------------------------------------------
    val myPatients: String
    val searchHint: String
    val visitPlan: String
    val syncQueue: String
    val serverSettings: String
    val signOut: String
    val filterDueNow: String
    val filterHighRisk: String
    val filterWatch: String
    val patientCount: (Int) -> String
    val loadingPatients: String
    val rosterOffline: String
    val noMatchingPatients: String
    val noMatchingPatientsBody: String
    val noPatientsYet: String
    val noPatientsYetBody: String
    val lastVisitPrefix: (String) -> String
    val nextVisitDue: (String) -> String

    // --- Patient profile ---------------------------------------------------
    val patientProfile: String
    val profileOffline: String
    val couldNotOpenProfile: String
    val couldNotOpenProfileBody: String
    val openingProfile: String
    val sectionLastVisit: String
    val sectionDetails: String
    val dateOfBirth: String
    val bloodGroup: String
    val phone: String
    val household: String
    val address: String
    val guardian: String
    val aadhaarLine: (String) -> String
    val aadhaarVerified: String
    val aadhaarNotLinked: String
    val sectionPregnancy: String
    val gestation: String
    val weeksSuffix: (Int) -> String
    val dueDate: String
    val gravidaPara: String
    val ancVisits: String
    val ancVisitsValue: (Int) -> String
    val lastHb: String
    val lastBp: String
    val ttDoses: String
    val ifaTablets: String
    val plannedDelivery: String
    val highRiskFactors: String
    val sectionNewborn: String
    val birthWeight: String
    val bornAt: String
    val currentWeight: String
    val muac: String
    val delivery: String
    val feeding: String
    val exclusiveBreastfeeding: String
    val mixedFeeding: String
    val sectionImmunisation: String
    val givenCount: (Int) -> String
    val overdueCount: (Int) -> String
    val comingUp: String
    val immunisationComplete: String
    val dueOn: (String) -> String
    val markGiven: String
    val sectionMedicalHistory: String
    val ongoing: String
    val pastHistory: String
    val sinceDate: (String) -> String
    val sectionPreviousVisits: String
    val recordVisit: String

    // --- Visit capture -----------------------------------------------------
    val recordVisitTitle: String
    val tabSpeak: String
    val tabType: String
    val micPrompt: String
    val micListening: String
    val micRecording: (Long) -> String
    val micTapToAdd: String
    val recordForLater: String
    val recordForLaterHint: String
    val recordingSaved: (Long) -> String
    val recordingSavedHint: String
    val discardRecording: String
    val whatWasHeard: String
    val whatWasHeardHint: String
    val sectionMeasurements: String
    val measurementsHint: String
    val visitNotes: String
    val extraNotes: String
    val notesPlaceholder: String
    val saveVisit: String
    val analysing: String
    val offlineSaveHint: String
    val queuedMessage: String
    val correctMeasurements: String
    val couldNotSaveVisit: String
    val enterANumber: String
    val expectedRange: (Double, Double) -> String

    // --- Vitals (labels; units stay in Latin) ------------------------------
    val vitalTemperature: String
    val vitalBpSystolic: String
    val vitalBpDiastolic: String
    val vitalPulse: String
    val vitalWeight: String
    val vitalHaemoglobin: String
    val vitalSpo2: String
    val vitalMuac: String

    // --- Visit result ------------------------------------------------------
    val visitResult: String
    val couldNotLoadVisit: String
    val couldNotLoadVisitBody: String
    val degradedWarning: (String) -> String
    val visitFailed: String
    val dangerSignsFound: String
    val whatToDoNow: String
    val nextVisit: String
    val nextVisitAuto: String
    val recordedInThisVisit: String
    val noFindings: String
    val basedOnGuidelines: String
    val passagesCount: (Int) -> String
    val show: String
    val hide: String
    val pageLabel: (Int) -> String
    val urgencyNow: String
    val urgencyToday: String
    val urgencyThisWeek: String
    val urgencyRoutine: String

    // --- Plan --------------------------------------------------------------
    val visitPlanTitle: String
    val visitPlanSubtitle: String
    val rangeDueNow: String
    val rangeNext7: String
    val rangeNext30: String
    val loadingPlan: String
    val planOffline: String
    val nothingScheduled: String
    val nothingScheduledBody: String
    val overdueHeading: (Int) -> String
    val upcoming: String
    val dueOnDate: (String) -> String
    val snoozeOneDay: String

    // --- Queue -------------------------------------------------------------
    val queueTitle: String
    val queueAllSent: String
    val queueWaiting: (Int) -> String
    val queueNothingWaiting: String
    val queueNothingWaitingBody: String
    val queueExplainer: String
    val trySendingNow: String
    val sending: String
    val statusWaiting: String
    val statusSending: String
    val statusSent: String
    val statusWillRetry: String
    val queueVoiceRecording: String
    val queueMeasurementsOnly: String
    val attemptLabel: (Int, String) -> String

    // --- Registration ------------------------------------------------------
    val registerPatient: String
    val sectionAadhaar: String
    val aadhaarExplainer: String
    val aadhaarNumber: String
    val aadhaarPlaceholder: String
    val aadhaarConsent: String
    val aadhaarValidMessage: (String) -> String
    val aadhaarOfflineMessage: String
    val sectionPatientDetails: String
    val fullName: String
    val genderFemale: String
    val genderMale: String
    val genderOther: String
    val dobPlaceholder: String
    val phoneOptional: String
    val sectionCategory: String
    val categoryHint: String
    val lastMenstrualPeriod: String
    val lmpHint: String
    val birthWeightKg: String
    val infantScheduleHint: String
    val registerButton: String
    val dateFormatError: String
    val dateFutureError: String
    val registerFailed: String

    // --- Server settings ---------------------------------------------------
    val serverTitle: String
    val serverSubtitle: String
    val howConnected: String
    val presetUsb: String
    val presetUsbHint: String
    val presetEmulator: String
    val presetEmulatorHint: String
    val presetWifi: String
    val presetWifiHint: String
    val addressLabel: String
    val willConnectTo: (String) -> String
    val addressHint: String
    val testConnection: String
    val save: String
    val saved: String
    val connected: String
    val noLlmWarning: String
    val findingYourIp: String
    val findingYourIpBody: String

    // --- Speech / connection errors ----------------------------------------
    val speechUnavailable: String
    val speechNoMic: String
    val speechPermission: String
    val speechNoNetwork: String
    val speechNoMatch: String
    val speechBusy: String
    val speechServerError: String
    val speechTimeout: String
    val speechFailed: String
    val speechStopped: String
    val recordingTooShort: String
    val couldNotStartRecording: (String) -> String
    // --- Connection diagnostics -------------------------------------------
    val connOk: (Long, Int, Int) -> String
    val connNoNetwork: String
    val connNoNetworkHint: String
    val connEmulatorOnly: String
    val connEmulatorOnlyHint: String
    val connHttpStatus: (Int) -> String
    val connHttpStatusHint: String
    val connUnexpectedReply: String
    val connUnexpectedReplyHint: String
    val connTimedOutSlow: String
    val connTimedOutSlowHint: String
    val connUnknownHost: String
    val connUnknownHostHint: String
    val connRefused: String
    val connRefusedHint: String
    val connTimedOut: String
    val connTimedOutHint: String
    val connGenericHint: String
    val noOfflineCopy: String
    val couldNotLoadRoster: String
}

val LocalStrings = staticCompositionLocalOf<Strings> { EnglishStrings }

/** Resolve a language code to a string table. Used by view models, which
 *  cannot read a CompositionLocal. */
fun stringsFor(language: String?): Strings =
    if (language?.startsWith("hi") == true) HindiStrings else EnglishStrings
