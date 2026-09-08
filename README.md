# SevakAI

An Android app for ASHA workers — India's last-mile community health workers —
that turns a spoken home-visit note into a structured record, a risk
classification grounded in real National Health Mission guidelines, and a
scheduled follow-up.

Built to work where the network does not.

---

## What it does

An ASHA worker opens a patient from her own roster, presses the mic, and
describes the visit in Hindi or Hinglish. Three agents then run:

| Agent | Job |
|---|---|
| **Extraction** | Pulls symptoms and vitals out of free speech. *"pair me sujan"* becomes `pedal oedema`; *"BP 150 by 100"* becomes `150/100`. |
| **Risk classification** | Retrieves the relevant passages from an indexed corpus of real Government of India guidelines and classifies 🔴 red / 🟡 yellow / 🟢 green, citing the document and page it used. |
| **Scheduling** | Decides what the worker should do now, and when to come back. Red gets a same-day check, yellow 2–7 days, green the routine interval for that patient type. |

If there is no signal, the visit is written to a local queue and uploaded
automatically when connectivity returns. Nothing is lost.

## Screens

Roster → patient profile → visit capture → result. Plus a visit plan, an
offline queue, and Aadhaar-verified registration.

The roster is sorted riskiest-first and every row carries the last visit's
one-line summary, so a worker knows what happened last time before she knocks.

---

## Running it

### 1. Backend

```bash
cd backend
python -m venv venv && ./venv/Scripts/activate      # Windows
pip install -r requirements.txt
cp .env.example .env                                 # then add your Groq key
python -m scripts.fetch_guidelines                   # downloads 8 NHM PDFs (~28 MB)
python -m app.rag.ingest --reset                     # builds the vector index
python -m app.seed --reset                           # 5 workers, ~150 patients
uvicorn app.main:app --host 0.0.0.0 --port 8010
```

Get a free Groq key at [console.groq.com/keys](https://console.groq.com/keys)
and put it in `backend/.env` as `GROQ_API_KEY`.

Verify everything is wired:

```bash
python -m scripts.smoke_test          # 40 checks over the whole worker journey
python -m scripts.test_risk_downgrade # risk moves both directions, not just up
python -m scripts.test_escalations    # one open alert per patient, not duplicates
python -m scripts.try_pipeline        # run the agents directly, for prompt tuning
```

The smoke test covers roster isolation (a worker gets 404 on someone else's
patient) and offline-retry idempotency. The two behavioural tests each submit
real visits through the live pipeline, so they pace themselves around the free
tier's token window and take a couple of minutes.

### 2. Android app

```bash
cd android
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Needs JDK 17+ and the Android SDK. `local.properties` must point at your SDK
(use forward slashes — `sdk.dir=C:/Users/you/AppData/Local/Android/Sdk`).

**On the emulator** the app reaches the backend at `10.0.2.2:8010`, which is
already the default. Use a *Google Play* system image — plain AOSP images have
no speech recogniser.

**On a physical phone**, plug it in and run:

```bash
adb reverse tcp:8010 tcp:8010
```

The same `10.0.2.2` address keeps working, with no config change.

### Demo sign-in

| Phone | PIN | Role |
|---|---|---|
| `9000000002` | `1234` | ASHA (Sunita Devi, Bagru — 40 patients) |
| `9000000001` | `1234` | ANM supervisor (sees her four workers' rosters) |

---

## Design decisions worth knowing

**Aadhaar is verified offline, not through UIDAI.** Live e-KYC is available
only to licensed AUA/KUA entities; there is no public API and no legitimate way
for a student project to call one. So the app does what can be done honestly:
validates the 12-digit structure and the Verhoeff checksum UIDAI actually uses,
records explicit consent, and stores **only a salted hash and the last four
digits** — never the number. Swapping in a real KUA integration means replacing
one function in `backend/app/core/aadhaar.py`; nothing else changes.

→ **[docs/AADHAAR.md](docs/AADHAAR.md)** explains this in full: why the Verhoeff
checksum is a real check and not a formality, why the hash is salted, what is
and is not stored, and the two upgrade paths (UIDAI Offline e-KYC XML, and
ABHA/ABDM). Read this before presenting — it is the design decision most likely
to be challenged.

**Deterministic rules are a safety floor, not just a fallback.** The clinical
thresholds in `backend/app/agents/rules.py` run on every visit, and they can
only *raise* the final risk level, never lower it. If a documented IMNCI danger
sign or a PMSMA severe-hypertension reading is present, the visit comes back
red regardless of what the model concluded. A language model being talked out
of a danger sign is a failure mode worth engineering away rather than hoping
about.

**Risk describes today, and moves in both directions.** The floor applies
*within* a visit, never across visits. A risk level is a statement about the
patient's condition at that visit, not a label they keep — so a red patient who
is well next week is classified green next week, and the roster updates. This
is load-bearing: if red were sticky, the roster would fill with permanent red
and the colour would stop carrying information.

Two things make it work. The classifier is told explicitly that visit history
is background, and that a stable, already-managed chronic condition is context
rather than a live concern. And `patient.current_risk` is overwritten by every
visit rather than being maxed with the previous value.

Verified by `scripts/test_risk_downgrade.py`, which drives a patient to red,
then submits an unremarkable visit and asserts the level comes down and the
follow-up interval stretches back out (1 day → 14 days).

Escalations are handled slightly differently on purpose: repeated red visits
**update** the patient's single open escalation instead of stacking duplicates
in the supervisor's queue, and a later non-red visit annotates it with the
improvement — but does **not** auto-resolve it. A red event still needs a human
to sign it off. See `scripts/test_escalations.py`.

**Degradation is never silent.** When the LLM is unreachable and rules stand in
for it, the step is recorded and shown on the result screen in the app. A demo
can never pass canned output off as live clinical reasoning.

**The queue is the source of truth, the cache is disposable.** Room holds two
different kinds of data. Cached patients are a mirror of the server and can be
thrown away. Pending visits are work the server has never seen — losing a row
means losing a home visit — so a visit is written locally *before* upload is
attempted, and rows are only cleared after the server confirms receipt.
Idempotency is keyed on a UUID the phone generates, so retrying is always safe.

**Roster scoping lives in one module.** Every query touching patient data goes
through `backend/app/core/scoping.py`. Requesting another worker's patient
returns 404, not 403 — a 403 would confirm the patient exists.

**Colour is never the only signal.** Every risk chip carries a word as well as
a colour, because red/green is precisely the pair that roughly one man in
twelve cannot distinguish, and it is the most consequential thing on screen.

---

## The guideline corpus

594 page-anchored chunks from eight real Government of India documents:

- Home Based Newborn Care — Operational Guidelines (2014)
- Handbook for ASHA Facilitator and ANM/MPW on HBNC and HBYC (2022)
- High Risk Conditions in Pregnancy (PMSMA)
- Pradhan Mantri Surakshit Matritva Abhiyan — Guidelines
- Guidance Note for Extended PMSMA — Tracking High Risk Pregnancies (2022)
- Anemia Mukt Bharat — Operational Guidelines
- National Immunization Schedule
- IMNCI Chart Booklet

Every citation the app shows names the document and the page, so a supervisor
can open the real PDF and check it. The PDFs are downloaded by
`scripts/fetch_guidelines.py` rather than committed — they belong to their
publisher.

---

## Cost and limits

Everything runs on free tiers.

- **LLM**: Groq, `openai/gpt-oss-120b`. About **3,900 tokens and ~4 seconds per
  visit** across the three agents.
- **Speech**: Android's on-device recogniser when online (free, no key, works
  offline once the Hindi language pack is installed). Audio queued offline is
  transcribed by Groq's `whisper-large-v3`.

The binding constraint is Groq's free tier at **8,000 tokens/minute** — roughly
**two visits per minute** sustained. A single visit is never slow; only
back-to-back submissions queue.

In practice this is not a real limit: a home visit takes 5–10 minutes, so one
worker generates at most ~12 visits an hour, an order of magnitude below the
ceiling. It matters only when a scripted demo fires several visits back to back
(pace them ~30 s apart), or when many workers share one API key.

→ **[docs/SCALING.md](docs/SCALING.md)** has the measured per-visit cost, what
to buy first when the free tier does bite, and the alternatives considered and
rejected. Headline: at paid Groq rates a visit costs roughly **₹0.10–0.20**, so
a 200-worker district runs at under ₹10,000/month. Cost is not what stops this
scaling.

---

## Known gaps

- Local patient data in Room is **not encrypted at rest**. A real deployment
  should use SQLCipher. Cloud backup and device transfer are already disabled
  so the data cannot leave the phone that way.
- The auth token is long-lived (14 days) on purpose, because workers go days
  without signal. That trades security for not being logged out mid-round.
- Two IMNCI PDFs are scanned images with no text layer, so they are not
  indexed. The IMNCI Chart Booklet covers the same ground.
- No supervisor dashboard or HMIS report export yet; escalations are raised and
  stored, and the API serves them, but only the app consumes them today.

---

## Layout

```
backend/
  app/
    agents/       extraction, risk, scheduling, rules, LangGraph pipeline
    core/         config, db, security, aadhaar, roster scoping
    rag/          corpus registry, PDF ingestion, Chroma retrieval
    routers/      auth, patients, visits, schedule, escalations
    services/     visit persistence, speech-to-text
  scripts/        fetch_guidelines, ingest, seed, smoke_test, try_pipeline
android/
  app/src/main/java/in/sevakai/app/
    data/         Retrofit API, Room cache + queue, repository
    speech/       on-device recognition, audio recorder
    sync/         WorkManager queue drain
    ui/           theme, components, screens
```

The previous web prototype is preserved on the `legacy/pwa-prototype` branch.
