import { useEffect, useRef, useState } from "react";
import { submitVoiceVisit } from "../api";
import { queueVisit } from "../offline";

const LANGUAGES = [
  { code: "hi", speech: "hi-IN", label: "हिन्दी Hindi" },
  { code: "mr", speech: "mr-IN", label: "मराठी Marathi" },
  { code: "ta", speech: "ta-IN", label: "தமிழ் Tamil" },
  { code: "te", speech: "te-IN", label: "తెలుగు Telugu" },
  { code: "bn", speech: "bn-IN", label: "বাংলা Bengali" },
  { code: "en", speech: "en-IN", label: "English" },
];

const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;

export default function RecordVisit({ auth, patient, isOnline, onBack, onProcessed, onQueuedOffline }) {
  const [language, setLanguage] = useState(LANGUAGES[0]);
  const [recording, setRecording] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [seconds, setSeconds] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const recognitionRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
      clearInterval(timerRef.current);
    };
  }, []);

  function startRecording() {
    setError("");
    if (!SpeechRecognitionAPI) {
      setError("Live speech recognition isn't supported in this browser. Type the observation below instead.");
      return;
    }
    const recognition = new SpeechRecognitionAPI();
    recognition.lang = language.speech;
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      let finalText = "";
      for (let i = 0; i < event.results.length; i++) {
        finalText += event.results[i][0].transcript + " ";
      }
      setTranscript(finalText.trim());
    };
    recognition.onerror = (e) => setError(`Speech recognition error: ${e.error}`);
    recognition.onend = () => setRecording(false);

    recognitionRef.current = recognition;
    recognition.start();
    setRecording(true);
    setSeconds(0);
    timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
  }

  function stopRecording() {
    recognitionRef.current?.stop();
    clearInterval(timerRef.current);
    setRecording(false);
  }

  async function handleConfirm() {
    if (!transcript.trim()) {
      setError("Please record or type an observation first.");
      return;
    }
    setSubmitting(true);
    setError("");

    const record = {
      workerId: auth.worker_id,
      patientId: patient.patient_id,
      transcript: transcript.trim(),
      languageCode: language.code,
    };

    if (!isOnline) {
      await queueVisit({ record_type: "visit", record_json: {
        patient_id: patient.patient_id, transcript: record.transcript, language_code: record.languageCode,
      }});
      onQueuedOffline(patient);
      setSubmitting(false);
      return;
    }

    try {
      const result = await submitVoiceVisit(record);
      onProcessed(patient, result);
    } catch (err) {
      // network hiccup even though we thought we were online — fall back to offline queue
      await queueVisit({ record_type: "visit", record_json: {
        patient_id: patient.patient_id, transcript: record.transcript, language_code: record.languageCode,
      }});
      onQueuedOffline(patient);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="screen">
      <button className="link-btn" onClick={onBack}>&larr; Back</button>
      <h2>{patient.name}</h2>
      <p className="subtitle">{patient.age ? `${patient.age} yrs` : ""} {patient.village ? `· ${patient.village}` : ""}</p>

      <div className="lang-picker">
        {LANGUAGES.map((l) => (
          <button
            key={l.code}
            className={`lang-chip ${language.code === l.code ? "active" : ""}`}
            onClick={() => setLanguage(l)}
            disabled={recording}
          >
            {l.label}
          </button>
        ))}
      </div>

      <div className="record-area">
        <button
          className={`mic-btn ${recording ? "recording" : ""}`}
          onClick={recording ? stopRecording : startRecording}
        >
          {recording ? "⏹" : "🎤"}
        </button>
        <p className="record-status">
          {recording ? `Recording... ${seconds}s` : "Tap to speak naturally about the visit"}
        </p>
      </div>

      <label>Transcript (edit if needed before confirming)</label>
      <textarea
        rows={5}
        value={transcript}
        onChange={(e) => setTranscript(e.target.value)}
        placeholder="Speak or type the observation, e.g. 'Meera Patil, 28 saal, 7 mahine ki pregnancy. Aaj BP 140 over 90 tha...'"
      />

      {error && <p className="error-text">{error}</p>}

      <button className="btn-primary" onClick={handleConfirm} disabled={submitting || recording}>
        {submitting ? "Processing..." : "Confirm & Process"}
      </button>
    </div>
  );
}
