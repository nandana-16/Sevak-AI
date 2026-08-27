# Architecture Notes & Requirement Traceability

## Worker client: web app (PWA) vs React Native

| | Web app (this build) | React Native / Expo (SRS default) |
|---|---|---|
| Runs today, no toolchain | Yes — any mobile browser | Needs Node, Java, Android SDK, and either an emulator or a physical device with Expo Go |
| Offline storage | IndexedDB (via a small wrapper in `web/worker-app/src/offline.js`) | SQLite (`expo-sqlite`) |
| Voice capture | Browser `SpeechRecognition` API (live transcript, Chrome/Edge) with manual-edit fallback | `expo-av` recording + server-side STT |
| Distribution | URL / "Add to Home Screen" | APK/AAB build, Play Store or sideload |
| Native device APIs (background sync while app is closed, push notifications) | Limited — foreground/service-worker only | Full native access |
| Backend contract | Identical — both call the same `/api/v1/*` endpoints | Identical |

**Recommendation**: keep the web app as the fast-iteration reference implementation and
for demoing on a laptop; build the Expo app in parallel once Android tooling is set up,
pointing it at the same backend. Since `POST /api/v1/visits/voice` accepts a `transcript`
string directly, Expo's client can either do on-device STT (Bhashini or a native STT lib)
or upload raw audio for server-side Bhashini transcription — no backend changes needed
either way.

## Speech-to-text: two supported paths

1. **Client-side transcript (default today)** — the browser's Web Speech API transcribes
   locally and the app sends plain text. Zero server-side STT cost/latency, but browser-
   dependent (Chrome/Edge only) and requires connectivity for Web Speech API itself in
   most browsers (a real offline gap — see Known Limitations below).
2. **Server-side Bhashini (`STT_PROVIDER=bhashini`)** — client uploads `audio_base64`,
   `backend/app/agents/stt_client.py`'s `BhashiniProvider` calls the ULCA pipeline API.
   This is the SRS's specified path and the one that genuinely works offline-to-online
   (record locally, sync audio later, transcribe server-side on sync).

For a real offline-first deployment, path 2 is the correct one — recorded audio queues
locally and transcription happens after sync. Path 1 is a fast way to demo the full
pipeline today without Bhashini credentials.

## RAG: ChromaDB + NHM protocols

`backend/app/rag/nhm_protocols.py` contains 24 original protocol summaries (maternal,
child, social, general — see file header) covering the clinical thresholds the demo
script exercises (PIH/pre-eclampsia at 140/90, anemia/IFA non-compliance, SAM via MUAC,
child danger signs, etc.). `chroma_store.py` embeds them locally via Chroma's bundled
ONNX MiniLM model (no API key, no cost) and Agent 2 retrieves the top-k most relevant
protocols per visit to ground the LLM's classification — genuine RAG, not a hardcoded
if/else, even though the fallback LLM is itself rule-based.

**Before any real clinical use**, replace this file's content with the actual current
NHM/RCH guideline text — it is explicitly a synthetic placeholder (see the file's
module docstring).

## LLM provider swap

Every agent calls `app/agents/llm_client.py::get_llm_client()`. Swapping providers is a
`.env` change (`LLM_PROVIDER=mock|gemini`), not a code change. The mock provider does
real (if simple) rule-based extraction/classification/action-generation so the pipeline
is meaningfully testable without any key — see its docstring for exactly what it does.

## Requirement traceability (SRS Section 3, P1 items)

| Req | Where implemented |
|---|---|
| FR-01.1–01.4 Voice input, Bhashini, offline, editable transcript | `web/worker-app/src/components/RecordVisit.jsx`, `app/agents/stt_client.py` |
| FR-02.1–02.5 Agent 1 extraction | `app/agents/agent1_extraction.py`, `app/agents/prompts.py` |
| FR-03.1–03.4 Agent 2 risk classification, RAG, override, alert | `app/agents/agent2_risk.py`, `app/rag/`, `app/routers/visits.py::override_risk`, `app/services/visit_pipeline.py` (supervisor alert on HIGH) |
| FR-04.1–04.3 Agent 3 referral/WhatsApp/follow-up | `app/agents/agent3_action.py`, `app/services/whatsapp.py` |
| FR-05.1–05.3 Agent 4 HMIS/RCH/PDF | `app/agents/agent4_reporting.py`, `app/routers/reports.py`, `app/services/pdf_report.py` |
| FR-06.1–06.2 Agent 5 escalation | `app/agents/agent5_escalation.py`, `app/services/escalation_monitor.py` (APScheduler sweep every 5 min), `app/routers/escalations.py` |
| FR-07.1–07.4 Mobile app offline/list/tasks | `web/worker-app/src/` (see note above on web vs. native) |
| FR-08.1–08.3 District dashboard | `web/dashboard/src/` |
| NFR-SC1–SC7 Security/compliance | JWT RBAC (`app/core/security.py`), `audit_log` table + `app/services/audit.py` on every state-changing action, synthetic-only data (`synthetic_data/generate.py`), Bhashini/LLM calls stateless (no audio/transcript persisted beyond this app's own DB) |
| NFR-S1–S4 Scalability | Stateless FastAPI (JWT, no server sessions), SQLAlchemy models portable to Postgres read replicas via a connection-string change |

## Known limitations (be upfront about these in the demo / judge Q&A)

- Web Speech API needs an internet connection in most browsers even though it's
  "client-side" — true offline voice capture needs either the Bhashini server-side path
  with locally-queued audio, or a native on-device STT engine (a native app's advantage).
- The mock LLM is rule-based, not a real language model — it demonstrates the pipeline
  shape and produces plausible outputs for the demo script's known phrasing, but won't
  generalize to arbitrary phrasing the way Gemini/GPT would. Flip `LLM_PROVIDER=gemini`
  before any evaluation that needs open-ended language understanding.
- No SQLCipher/at-rest encryption wired yet for the SQLite file (NFR-SC1 partially met —
  Postgres deployment + TLS termination gets closer to the full NFR-SC1–SC2 story).
