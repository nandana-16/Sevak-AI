# SevakAI

Agentic voice intelligence for India's last-mile ASHA health workers — built for the
Deloitte USI Capstone Program 2026 (Team GenSim, Manipal University Jaipur).

An ASHA worker speaks a home-visit observation naturally in Hindi/Marathi/Tamil/Telugu/
Bengali. A 5-agent AI pipeline extracts the clinical record, classifies risk against NHM
protocols (RAG-grounded), drafts referral/WhatsApp/follow-up actions, auto-fills the HMIS
monthly report, and monitors unactioned HIGH-risk cases for escalation — all visible live
on a supervisor dashboard.

## What's here

```
backend/          FastAPI + LangGraph 5-agent pipeline + ChromaDB RAG + SQLite/Postgres
web/worker-app/    ASHA worker PWA (React) — voice recording, offline queue, patient list
web/dashboard/     ANM/BMO/Admin district dashboard (React) — heatmap, escalations, HMIS PDF
docs/              Architecture & requirements-traceability notes
```

## Why a web app instead of React Native

The SRS/plan specify a React Native (Expo) Android app. This build uses a responsive
web app (PWA) instead — see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#worker-client-web-app-vs-react-native)
for the full comparison. Short version: it runs in any mobile browser today with zero
Android toolchain, replicates offline-first behavior via IndexedDB, and every backend
API it calls is the *same* API a native Expo client would call — so porting the UI to
React Native later is a frontend-only change, not an architecture change.

## Quick start

### 1. Backend

```bash
cd backend
python -m venv venv
venv/Scripts/activate          # venv\Scripts\Activate.ps1 on PowerShell; source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env           # defaults work out of the box (mock LLM/STT/WhatsApp, SQLite)
python -m synthetic_data.generate     # seeds 500 workers, 5,000 patients, ~3 months of visits
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/health to confirm it's up. API docs: http://localhost:8000/docs.

> **Port 8000 already bound / mystery process you can't kill?** On some Windows setups
> (seen with Docker Desktop's WSL2 backend running) port 8000 can end up with a phantom
> listener that `Stop-Process`/`taskkill` can't touch. Just run uvicorn on a different
> port (`--port 8010`) and update `VITE_API_BASE` in both `web/*/.env.development` files
> to match — takes 30 seconds, not worth debugging further.

### 2. Worker app (ASHA)

```bash
cd web/worker-app
npm install
npm run dev
```

Open the printed localhost URL. Log in with the demo ASHA account: **9999900001 / 1234**
(Sunita Sharma). Use Chrome/Edge for live speech-to-text (Web Speech API); other browsers
fall back to typing the observation.

### 3. Dashboard (ANM / BMO / Admin)

```bash
cd web/dashboard
npm install
npm run dev
```

Log in as BMO: **9999900003 / 1234**, ANM: **9999900002 / 1234**, or Admin: **9999900004 / 1234**.

## Running the demo script

The SRS's 5-minute demo walkthrough (Section 9) uses a patient named **Meera Patil**,
already seeded with a 7-day-old prior LOW-risk visit under Sunita Sharma's patient list.
Log into the worker app, open Meera Patil, record (or type) something like:

> "Meera Patil, 28 saal, 7 mahine ki pregnancy. Aaj BP 140 over 90 tha. Usne pichle 2
> hafte se iron tablets nahi li. Pati bahar gaya hua hai."

Confirm & Process — this runs the real 5-agent pipeline (extraction → RAG-grounded risk
classification → action generation → HMIS field mapping → escalation deadline) and shows
the HIGH-risk result with cited protocol drivers, the drafted referral/WhatsApp/follow-up,
and updates the dashboard heatmap/metrics/escalation list within the next 30-second
dashboard refresh.

## What's real vs. mocked today

| Component | Status | To go live |
|---|---|---|
| LangGraph 5-agent pipeline | Real | — already runs end-to-end |
| ChromaDB RAG over NHM protocols | Real (24 authored protocol docs, local embeddings) | Replace `backend/app/rag/nhm_protocols.py` with actual current NHM/RCH guideline text |
| LLM (agents' reasoning) | **Mock** (rule-based) by default | Set `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` in `backend/.env` (free tier: https://aistudio.google.com/apikey) |
| Speech-to-text | **Mock/client-side** — browser Web Speech API does STT directly | Set `STT_PROVIDER=bhashini` + credentials from https://bhashini.gov.in |
| WhatsApp delivery | **Mock** — drafts stored/returned, not sent | Set `WHATSAPP_PROVIDER=meta` + Meta Business API credentials |
| Database | SQLite (zero setup) | Change `DATABASE_URL` in `.env` to a Postgres URL — same SQLAlchemy models, no code changes. `docker-compose --profile postgres up` provided. |
| Auth / RBAC / audit log | Real (JWT, 4 roles, `audit_log` table on every action) | — |
| Encryption at rest/in transit | Not yet wired (SQLite file is unencrypted; use HTTPS via a reverse proxy for TLS) | Add SQLCipher for local DB, terminate TLS at your deploy target |

Nothing here blocks the pipeline from running today — mocks were chosen specifically so
the full voice → risk → action → report → escalation flow is demonstrable with zero API
keys and zero cost, per the SRS's own documented fallback plan (Section 9.1 / Risk Register).

## Team ownership (per the sprint plan)

- **AI/ML & Agentic Orchestration** (`backend/app/agents/`, `backend/app/rag/`) — Bhashini
  integration point, LangGraph pipeline, ChromaDB RAG, clinical extraction prompts.
- **Backend & Integration** (`backend/app/routers/`, `backend/app/models/`, `web/dashboard/`) —
  FastAPI, DB schema, WhatsApp integration, officer dashboard, cloud deploy.
- **Front-End & Mobile** (`web/worker-app/`) — worker UI/UX, offline sync, audio capture.
  Porting this to React Native/Expo for the Android build is a frontend-only task; the
  API contract in `backend/app/routers/` doesn't change.
