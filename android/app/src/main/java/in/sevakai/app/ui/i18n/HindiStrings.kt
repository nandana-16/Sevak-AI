package `in`.sevakai.app.ui.i18n

/**
 * Hindi translation.
 *
 * BP, Hb, SpO2, MUAC, ANC, IFA, TT, EDD and PIN are deliberately left in Latin
 * script: they are what ASHA workers are trained on and what is printed on the
 * MCP card and the registers they already fill in. Translating them would be
 * linguistically correct and practically wrong.
 *
 * Numerals stay Arabic, as on Indian government forms.
 */
object HindiStrings : Strings {

    override val languageName = "हिन्दी"

    override val appName = "SevakAI"
    override val appTagline = "आशा कार्यकर्ताओं के लिए"
    override val loading = "लोड हो रहा है…"
    override val back = "वापस"
    override val done = "हो गया"
    override val cancel = "रद्द करें"
    override val retry = "फिर कोशिश करें"
    override val offlineBanner = "इंटरनेट नहीं है। फ़ोन में सहेजी गई जानकारी दिख रही है।"
    override val notRecorded = "—"

    override val riskRedAction = "आज ही अस्पताल ले जाएँ"
    override val riskAmberAction = "जल्दी डॉक्टर को दिखाएँ"
    override val riskGreenAction = "स्वस्थ है"
    override val riskUnknownAction = "जाँच नहीं हुई"
    override val riskRedShort = "ज़्यादा ख़तरा"
    override val riskAmberShort = "ध्यान दें"
    override val riskGreenShort = "स्वस्थ"
    override val riskUnknownShort = "नया"

    override val categoryPregnant = "गर्भवती"
    override val categoryInfant = "शिशु"
    override val categoryChild = "बच्चा"
    override val categoryPostnatal = "प्रसव के बाद"
    override val categoryAdult = "वयस्क"
    override val categoryElderly = "बुज़ुर्ग"

    override val chooseLanguage = "अपनी भाषा चुनें"
    override val phoneNumber = "फ़ोन नंबर"
    override val pin = "4 अंकों का PIN"
    override val signIn = "साइन इन करें"
    override val demoSignIn = "डेमो साइन-इन\n9000000002  ·  PIN 1234"
    override val serverLabel = { address: String -> "सर्वर: $address" }
    override val signInWrongPin = "फ़ोन नंबर या PIN ग़लत है।"
    override val signInUnreachable = { address: String ->
        "$address तक नहीं पहुँच पा रहे। नीचे \"सर्वर\" दबाकर पता जाँचें, " +
            "या कनेक्शन की जाँच करें।"
    }
    override val signInFailed = { detail: String -> "साइन इन नहीं हो सका। $detail".trim() }

    override val myPatients = "मेरे मरीज़"
    override val searchHint = "नाम या गाँव से खोजें"
    override val visitPlan = "दौरे की योजना"
    override val syncQueue = "भेजने की सूची"
    override val serverSettings = "सर्वर सेटिंग"
    override val signOut = "साइन आउट"
    override val filterDueNow = "अभी बाकी"
    override val filterHighRisk = "ज़्यादा ख़तरा"
    override val filterWatch = "ध्यान दें"
    override val patientCount = { n: Int -> "$n मरीज़" }
    override val loadingPatients = "आपके मरीज़ों की सूची आ रही है…"
    override val rosterOffline =
        "इंटरनेट नहीं है। फ़ोन में सहेजी गई मरीज़ों की सूची दिख रही है।"
    override val noMatchingPatients = "कोई मरीज़ नहीं मिला"
    override val noMatchingPatientsBody =
        "फ़िल्टर हटाकर देखें, या कोई दूसरा नाम खोजें।"
    override val noPatientsYet = "अभी कोई मरीज़ नहीं सौंपा गया"
    override val noPatientsYetBody =
        "आपकी ANM जो मरीज़ आपको सौंपेंगी, वे यहाँ दिखेंगे।"
    override val lastVisitPrefix = { summary: String -> "पिछला दौरा: $summary" }
    override val nextVisitDue = { date: String -> "अगला दौरा $date को" }

    override val patientProfile = "मरीज़ की जानकारी"
    override val profileOffline = "इंटरनेट नहीं है — फ़ोन में सहेजी गई जानकारी दिख रही है।"
    override val couldNotOpenProfile = "यह जानकारी नहीं खुल सकी"
    override val couldNotOpenProfileBody = "इंटरनेट आने पर फिर कोशिश करें।"
    override val openingProfile = "जानकारी खुल रही है…"
    override val sectionLastVisit = "पिछला दौरा"
    override val sectionDetails = "जानकारी"
    override val dateOfBirth = "जन्म तिथि"
    override val bloodGroup = "ब्लड ग्रुप"
    override val phone = "फ़ोन"
    override val household = "परिवार संख्या"
    override val address = "पता"
    override val guardian = "अभिभावक"
    override val aadhaarLine = { masked: String -> "आधार $masked" }
    override val aadhaarVerified = "पंजीकरण के समय बिना इंटरनेट जाँचा गया"
    override val aadhaarNotLinked = "जुड़ा नहीं है"
    override val sectionPregnancy = "गर्भावस्था"
    override val gestation = "गर्भ की अवधि"
    override val weeksSuffix = { weeks: Int -> "$weeks हफ़्ते" }
    override val dueDate = "संभावित प्रसव तिथि"
    override val gravidaPara = "Gravida / Para"
    override val ancVisits = "ANC दौरे"
    override val ancVisitsValue = { done: Int -> "4 में से $done" }
    override val lastHb = "पिछला Hb"
    override val lastBp = "पिछला BP"
    override val ttDoses = "TT खुराक"
    override val ifaTablets = "IFA गोलियाँ"
    override val plannedDelivery = "प्रसव कहाँ होगा"
    override val highRiskFactors = "ख़तरे की बातें"
    override val sectionNewborn = "नवजात की जानकारी"
    override val birthWeight = "जन्म के समय वज़न"
    override val bornAt = "जन्म किस हफ़्ते"
    override val currentWeight = "अभी का वज़न"
    override val muac = "MUAC"
    override val delivery = "प्रसव"
    override val feeding = "दूध पिलाना"
    override val exclusiveBreastfeeding = "सिर्फ़ माँ का दूध"
    override val mixedFeeding = "माँ का दूध और ऊपर का दूध"
    override val sectionImmunisation = "टीकाकरण"
    override val givenCount = { n: Int -> "$n लग चुके" }
    override val overdueCount = { n: Int -> "$n बाकी हैं" }
    override val comingUp = "आने वाले टीके"
    override val immunisationComplete = "टीकाकरण पूरा हो चुका है।"
    override val dueOn = { date: String -> "$date को लगना है" }
    override val markGiven = "लग गया"
    override val sectionMedicalHistory = "बीमारी का इतिहास"
    override val ongoing = "अभी चल रही"
    override val pastHistory = "पहले हुई"
    override val sinceDate = { date: String -> "  ($date से)" }
    override val sectionPreviousVisits = "पिछले दौरे"
    override val recordVisit = "दौरा दर्ज करें"

    override val recordVisitTitle = "दौरा दर्ज करें"
    override val tabSpeak = "बोलें"
    override val tabType = "लिखें"
    override val micPrompt = "माइक दबाएँ और दौरे के बारे में अपने शब्दों में बताएँ।"
    override val micListening = "सुन रहे हैं… आराम से बोलें, फिर रोकने के लिए दबाएँ।"
    override val micRecording = { seconds: Long ->
        "रिकॉर्ड हो रहा है… ${seconds} सेकंड। रोकने के लिए दबाएँ।"
    }
    override val micTapToAdd = "और जोड़ने के लिए माइक दबाएँ।"
    override val recordForLater = "बाद के लिए आवाज़ रिकॉर्ड करें"
    override val recordForLaterHint =
        "जहाँ इंटरनेट के बिना आवाज़ नहीं पहचानी जाती, वहाँ इसका इस्तेमाल करें।"
    override val recordingSaved = { seconds: Long -> "रिकॉर्डिंग सहेजी गई (${seconds} सेकंड)" }
    override val recordingSavedHint = "दौरा भेजे जाने पर इसे लिखा जाएगा।"
    override val discardRecording = "रिकॉर्डिंग हटाएँ"
    override val whatWasHeard = "जो सुना गया"
    override val whatWasHeardHint = "सहेजने से पहले ग़लत लिखी बात सुधार लें।"
    override val sectionMeasurements = "माप"
    override val measurementsHint = "यहाँ जो आप लिखेंगी, वही हूबहू लिया जाएगा।"
    override val visitNotes = "दौरे की टिप्पणी"
    override val extraNotes = "और कुछ (ज़रूरी नहीं)"
    override val notesPlaceholder =
        "आपने क्या देखा? लक्षण, दी गई सलाह, कोई असामान्य बात।"
    override val saveVisit = "दौरा सहेजें"
    override val analysing = "जाँच हो रही है…"
    override val offlineSaveHint =
        "इंटरनेट न हो तो दौरा इसी फ़ोन में सहेजा जाएगा और बाद में भेजा जाएगा।"
    override val queuedMessage =
        "इसी फ़ोन में सहेज लिया गया। इंटरनेट आते ही अपने आप भेज दिया जाएगा।"
    override val correctMeasurements = "लाल दिख रहे माप सुधार लें।"
    override val couldNotSaveVisit = "दौरा सहेजा नहीं जा सका"
    override val enterANumber = "संख्या लिखें"
    override val expectedRange = { min: Double, max: Double -> "$min–$max के बीच होना चाहिए" }

    override val vitalTemperature = "बुख़ार"
    override val vitalBpSystolic = "BP ऊपर का"
    override val vitalBpDiastolic = "BP नीचे का"
    override val vitalPulse = "नाड़ी"
    override val vitalWeight = "वज़न"
    override val vitalHaemoglobin = "Hb"
    override val vitalSpo2 = "SpO₂"
    override val vitalMuac = "MUAC"

    override val visitResult = "दौरे का नतीजा"
    override val couldNotLoadVisit = "यह दौरा नहीं खुल सका"
    override val couldNotLoadVisitBody = "इंटरनेट आने पर फिर कोशिश करें।"
    override val degradedWarning = { steps: String ->
        "इसका कुछ हिस्सा AI ने नहीं, तय नियमों से निकाला गया है ($steps)। " +
            "कृपया आप ख़ुद भी देख लें।"
    }
    override val visitFailed = "इस दौरे की जाँच अपने आप नहीं हो सकी।"
    override val dangerSignsFound = "ख़तरे के लक्षण मिले"
    override val whatToDoNow = "अब क्या करना है"
    override val nextVisit = "अगला दौरा"
    override val nextVisitAuto = "आपकी दौरा योजना में अपने आप जुड़ गया।"
    override val recordedInThisVisit = "इस दौरे में दर्ज"
    override val noFindings = "कोई ख़ास बात दर्ज नहीं हुई।"
    override val basedOnGuidelines = "NHM दिशानिर्देशों के आधार पर"
    override val passagesCount = { n: Int -> "सरकारी दस्तावेज़ों से $n अंश" }
    override val show = "दिखाएँ"
    override val hide = "छिपाएँ"
    override val pageLabel = { page: Int -> "पृष्ठ $page" }
    override val urgencyNow = "अभी"
    override val urgencyToday = "आज"
    override val urgencyThisWeek = "इस हफ़्ते"
    override val urgencyRoutine = "सामान्य"

    override val visitPlanTitle = "दौरे की योजना"
    override val visitPlanSubtitle = "हर दौरे के ख़तरे के स्तर से तय"
    override val rangeDueNow = "अभी बाकी"
    override val rangeNext7 = "अगले 7 दिन"
    override val rangeNext30 = "अगले 30 दिन"
    override val loadingPlan = "आपकी योजना आ रही है…"
    override val planOffline = "इंटरनेट नहीं है — पिछली सहेजी योजना दिख रही है।"
    override val nothingScheduled = "कोई दौरा तय नहीं है"
    override val nothingScheduledBody =
        "दौरा दर्ज करने के बाद अगली मुलाक़ातें यहाँ अपने आप दिखेंगी।"
    override val overdueHeading = { n: Int -> "समय निकल चुका ($n)" }
    override val upcoming = "आने वाले"
    override val dueOnDate = { date: String -> "$date को" }
    override val snoozeOneDay = "कोई घर पर नहीं — 1 दिन आगे बढ़ाएँ"

    override val queueTitle = "भेजने की सूची"
    override val queueAllSent = "सब भेजा जा चुका है"
    override val queueWaiting = { n: Int -> "$n भेजने बाकी हैं" }
    override val queueNothingWaiting = "कुछ बाकी नहीं है"
    override val queueNothingWaitingBody =
        "इंटरनेट के बिना दर्ज किए गए दौरे यहाँ रखे जाते हैं और सिग्नल आते ही " +
            "अपने आप भेज दिए जाते हैं।"
    override val queueExplainer =
        "दौरे अपने आप भेजे जाते हैं। ऐप बंद करने या फ़ोन दोबारा चालू करने पर " +
            "भी कुछ नहीं खोता।"
    override val trySendingNow = "अभी भेजकर देखें"
    override val sending = "भेजा जा रहा है…"
    override val statusWaiting = "इंटरनेट का इंतज़ार"
    override val statusSending = "भेजा जा रहा है…"
    override val statusSent = "भेज दिया"
    override val statusWillRetry = "फिर कोशिश होगी"
    override val queueVoiceRecording = "आवाज़ रिकॉर्डिंग, सर्वर पर लिखी जाएगी"
    override val queueMeasurementsOnly = "सिर्फ़ माप"
    override val attemptLabel = { n: Int, error: String -> "कोशिश $n: $error" }

    override val registerPatient = "नया मरीज़ जोड़ें"
    override val sectionAadhaar = "आधार जाँच"
    override val aadhaarExplainer =
        "नंबर की जाँच इसी फ़ोन पर होती है। सिर्फ़ आख़िरी 4 अंक और एक कोड " +
            "सहेजा जाता है — पूरा नंबर कभी नहीं।"
    override val aadhaarNumber = "आधार नंबर"
    override val aadhaarPlaceholder = "XXXX XXXX XXXX"
    override val aadhaarConsent = "मरीज़ ने आधार जोड़ने की सहमति दी है"
    override val aadhaarValidMessage = { last4: String ->
        "जाँच हो गई। सिर्फ़ आख़िरी अंक $last4 सहेजे जाएँगे।"
    }
    override val aadhaarOfflineMessage =
        "इंटरनेट के बिना नंबर जाँचा नहीं जा सका। नया मरीज़ जोड़ने के लिए इंटरनेट चाहिए।"
    override val sectionPatientDetails = "मरीज़ की जानकारी"
    override val fullName = "पूरा नाम"
    override val genderFemale = "महिला"
    override val genderMale = "पुरुष"
    override val genderOther = "अन्य"
    override val dobPlaceholder = "YYYY-MM-DD"
    override val phoneOptional = "फ़ोन (ज़रूरी नहीं)"
    override val sectionCategory = "श्रेणी"
    override val categoryHint = "इससे तय होता है कि कौन-से दिशानिर्देश और कार्यक्रम लागू होंगे।"
    override val lastMenstrualPeriod = "आख़िरी माहवारी की तारीख़"
    override val lmpHint = "इससे प्रसव की तारीख़ और ANC दौरों का समय तय होता है।"
    override val birthWeightKg = "जन्म के समय वज़न (किलो)"
    override val infantScheduleHint =
        "जन्म तिथि से पूरा राष्ट्रीय टीकाकरण कार्यक्रम अपने आप बन जाता है।"
    override val registerButton = "मरीज़ जोड़ें"
    override val dateFormatError = "YYYY-MM-DD इस रूप में लिखें"
    override val dateFutureError = "तारीख़ आगे की नहीं हो सकती"
    override val registerFailed = "मरीज़ नहीं जुड़ सका। इसके लिए इंटरनेट चाहिए।"

    override val serverTitle = "सर्वर"
    override val serverSubtitle = "यह ऐप दौरे कहाँ भेजता है"
    override val howConnected = "यह फ़ोन कैसे जुड़ा है?"
    override val presetUsb = "USB केबल"
    override val presetUsbHint = "127.0.0.1:8010 — चलाएँ  adb reverse tcp:8010 tcp:8010"
    override val presetEmulator = "एमुलेटर"
    override val presetEmulatorHint = "10.0.2.2:8010 — सिर्फ़ एमुलेटर पर चलता है"
    override val presetWifi = "वही Wi-Fi"
    override val presetWifiHint = "नीचे अपने लैपटॉप का IP पता लिखें"
    override val addressLabel = "पता"
    override val willConnectTo = { address: String -> "जुड़ेगा  $address" }
    override val addressHint =
        "सिर्फ़ IP लिखना काफ़ी है — पोर्ट और http:// अपने आप जुड़ जाते हैं।"
    override val testConnection = "कनेक्शन जाँचें"
    override val save = "सहेजें"
    override val saved = "सहेज लिया।"
    override val connected = "जुड़ गया"
    override val noLlmWarning =
        "सर्वर मिल गया, पर उसमें AI सेट नहीं है। दौरे सिर्फ़ तय नियमों से " +
            "जाँचे जाएँगे। backend/.env में GROQ_API_KEY डालें।"
    override val findingYourIp = "लैपटॉप का IP कैसे पता करें"
    override val findingYourIpBody =
        "Windows:  ipconfig  — IPv4 Address देखें\n" +
            "macOS / Linux:  ifconfig | grep inet\n\n" +
            "फ़ोन और लैपटॉप एक ही Wi-Fi पर होने चाहिए, और बैकएंड " +
            "--host 0.0.0.0 से चलना चाहिए।"

    override val speechUnavailable =
        "इस फ़ोन पर आवाज़ पहचान उपलब्ध नहीं है। कृपया टाइप करके लिखें।"
    override val speechNoMic = "माइक नहीं पढ़ा जा सका।"
    override val speechPermission = "दौरा रिकॉर्ड करने के लिए माइक की अनुमति चाहिए।"
    override val speechNoNetwork =
        "आवाज़ पहचान के लिए इंटरनेट नहीं है। \"बाद के लिए रिकॉर्ड करें\" का इस्तेमाल करें।"
    override val speechNoMatch = "कुछ समझ नहीं आया। फिर कोशिश करें।"
    override val speechBusy = "आवाज़ पहचान व्यस्त है। फिर कोशिश करें।"
    override val speechServerError = "आवाज़ सेवा में गड़बड़ी हुई।"
    override val speechTimeout = "कोई आवाज़ सुनाई नहीं दी।"
    override val speechFailed = "आवाज़ पहचान नहीं हो सकी।"
    override val speechStopped = "आवाज़ पहचान अचानक रुक गई।"
    override val recordingTooShort = "रिकॉर्डिंग बहुत छोटी थी। बटन थोड़ी देर और दबाए रखें।"
    override val couldNotStartRecording = { detail: String ->
        "रिकॉर्डिंग शुरू नहीं हो सकी: $detail"
    }
    override val connOk = { ms: Long, patients: Int, chunks: Int ->
        "$ms ms में जुड़ गया · $patients मरीज़ · $chunks दिशानिर्देश अंश"
    }
    override val connNoNetwork = "इस फ़ोन में इंटरनेट नहीं है"
    override val connNoNetworkHint =
        "Wi-Fi चालू करें, या USB से जोड़कर \"USB केबल\" चुनें।"
    override val connEmulatorOnly = "10.0.2.2 सिर्फ़ एमुलेटर पर चलता है"
    override val connEmulatorOnlyHint =
        "असली फ़ोन पर \"USB केबल\" चुनें (और adb reverse tcp:8010 tcp:8010 चलाएँ), " +
            "या अपने लैपटॉप का Wi-Fi IP पता लिखें।"
    override val connHttpStatus = { code: Int -> "सर्वर ने HTTP $code लौटाया" }
    override val connHttpStatusHint =
        "उस पते पर कुछ चल तो रहा है, पर वह SevakAI बैकएंड नहीं है।"
    override val connUnexpectedReply = "उस पते से अनपेक्षित जवाब मिला"
    override val connUnexpectedReplyHint =
        "पता मिल गया, पर जवाब SevakAI बैकएंड जैसा नहीं था।"
    override val connTimedOutSlow = "सर्वर ने समय पर जवाब नहीं दिया"
    override val connTimedOutSlowHint = "शायद अभी चालू हो रहा है, या फ़ायरवॉल रोक रहा है।"
    override val connUnknownHost = "यह पता नहीं मिला"
    override val connUnknownHostHint = "देखें कि IP पता सही लिखा है।"
    override val connRefused = "उस पते पर कुछ नहीं चल रहा"
    override val connRefusedHint =
        "देखें कि बैकएंड --host 0.0.0.0 से चल रहा है, और लैपटॉप का फ़ायरवॉल " +
            "पोर्ट 8010 खोलता है।"
    override val connTimedOut = "सर्वर तक पहुँचने में समय ख़त्म हो गया"
    override val connTimedOutHint =
        "फ़ोन और लैपटॉप शायद अलग नेटवर्क पर हैं, या फ़ायरवॉल कनेक्शन रोक रहा है।"
    override val connGenericHint = "पता जाँचें और देखें कि बैकएंड चल रहा है।"
    override val noOfflineCopy =
        "यह जानकारी पहले कभी नहीं खोली गई, इसलिए फ़ोन में इसकी कोई प्रति नहीं है।"
    override val couldNotLoadRoster = "मरीज़ों की सूची नहीं आ सकी"
}
