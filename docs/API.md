# API reference

27 endpoints. The backend is FastAPI, so a live interactive version is always
at **<http://localhost:8010/docs>** while the server is running. This page is
the readable summary.

Everything except `/api/health` and `/api/auth/login` needs a bearer token:

```
Authorization: Bearer <token>
```

**Scoping applies to every endpoint below.** What you get back depends on who
you are. An ASHA sees her own patients, an ANM sees her workers', a BMO sees
his block. Asking for something outside your scope returns **404, not 403**,
so that a worker cannot learn a patient exists by being told she may not see
them. See [FEATURES.md, section 22](FEATURES.md#22-who-can-see-what).

---

## Health and reference

### `GET /api/health`

No token needed. Returns whether the model and the corpus are ready.

```json
{
  "status": "ok",
  "llm_provider": "groq",
  "llm_ready": true,
  "stt_provider": "bhashini",
  "guideline_chunks": 594,
  "patients": 158
}
```

Useful before a demo. It does not tell you whether the daily token quota is
exhausted, only whether the key works. For that, record a visit and check
`degraded_steps`.

### `GET /api/guidelines`

Lists the eight source documents with title, publisher, year and the
government URL each came from.

---

## Auth

### `POST /api/auth/login`

```json
{ "phone": "9000000002", "pin": "1234" }
```

Returns a JWT and the worker record. The token lasts 14 days by default.

### `GET /api/auth/me`

The signed in worker: name, role, village, block, district, preferred language.

---

## Patients

### `GET /api/patients`

The roster, already sorted riskiest first then most overdue.

| Parameter | Meaning |
|---|---|
| `search` | matches name or village |
| `village` | exact village |
| `category` | `infant`, `child`, `pregnant`, `postnatal`, `adult`, `elderly` |
| `risk` | `red`, `yellow`, `green`, `unknown` |
| `due_only` | only patients with a visit due today or earlier |
| `limit` | default 200, maximum 500 |

Rows are deliberately light. They carry the last visit summary and the next due
date but **not** the phone number or the full history, because a worker
scrolling forty patients on a slow phone should not be downloading full
records.

### `GET /api/patients/{patient_id}`

The full record: demographics, blood group, masked Aadhaar, pregnancy block,
infant block, immunisation list, conditions and recent visits.

### `GET /api/patients/{patient_id}/stats`

Counts and trends for one patient.

### `GET /api/patients/villages`

The villages inside your scope, for the filter dropdown.

### `POST /api/patients`

Registers a patient. Creates the pregnancy or infant record if the category
needs one, and writes out the full immunisation schedule for an infant with
real due dates.

### `POST /api/patients/aadhaar/check`

```json
{ "aadhaar": "456789012341" }
```

Checks structure and the Verhoeff checksum, and reports whether this number is
already registered. It does this by comparing hashes, so it never needs to
hold the number. Called before registration so a typo is caught at the point
of entry.

### `POST /api/patients/{patient_id}/vaccinations/{vaccination_id}/given`

Marks a dose given today. Optional `batch_no`.

---

## Visits

### `POST /api/visits`

The main endpoint. Submits a visit as text and runs the three agents.

```json
{
  "client_uuid": "generated-on-the-phone",
  "patient_id": "...",
  "transcript": "बहुत तेज़ सर दर्द है, आँखों के आगे धुंधला दिख रहा है",
  "typed_notes": null,
  "manual_fields": { "bp_systolic": 168, "bp_diastolic": 112 },
  "input_mode": "voice",
  "language": "hi"
}
```

At least one of `transcript`, `typed_notes` or `manual_fields` is required.

`client_uuid` is generated on the phone and is what makes the offline queue
safe. Submitting the same uuid twice returns the visit that already exists
instead of creating a second one. That is the whole idempotency mechanism.

Anything in `manual_fields` is kept exactly as given and is never overwritten
by the model.

Returns the full visit: risk level, reason, danger signs, actions, citations,
next visit date, degraded steps, and the messages the visit produced.

### `POST /api/visits/audio`

The same thing as multipart form data, with an audio file. This is the path a
visit takes when it was recorded with no network and the phone could not
transcribe it locally.

Accepts `.m4a`, `.mp4`, `.aac`, `.wav`, `.ogg`, `.opus`, `.mp3`, `.webm`,
`.flac`, up to 25 MB. The server transcribes it and then runs the same
pipeline. Same `client_uuid` idempotency.

### `GET /api/visits`

Visits for one patient, newest first. Takes `patient_id` and `limit`.

### `GET /api/visits/{visit_id}`

One visit in full, including its messages.

---

## Schedule

### `GET /api/schedule/today`

What is due today, ordered with overdue and high risk first.

### `GET /api/schedule`

The next `days` days, default 14.

### `POST /api/schedule/{schedule_id}/complete`

Marks a scheduled visit done.

### `POST /api/schedule/{schedule_id}/snooze`

Pushes a visit by `days`, between 1 and 30.

**Returns 400 for a high risk follow up.** The rule lives here rather than only
in the app, so it cannot be bypassed. The error text tells the worker to record
the visit or escalate it to her ANM.

---

## Escalations

### `GET /api/escalations`

Open escalations in your scope, newest first. `include_resolved=true` includes
closed ones. Each carries the patient name, the worker who raised it, the
reason, and any resolution note.

### `POST /api/escalations/{escalation_id}/acknowledge`

Marks it acknowledged and resolved, with an optional `note`.

---

## Messages

Every response from these endpoints carries `simulated: true` while the mock
provider is in use. See
[FEATURES.md, section 17](FEATURES.md#17-messages-to-families).

### `GET /api/messages`

The outbox, newest first.

| Parameter | Meaning |
|---|---|
| `status` | `scheduled`, `sent`, `failed`, `no_contact` |
| `message_type` | `referral`, `escalation`, `reminder` |
| `patient_id` | one patient's thread |
| `limit` | default 50, maximum 200 |

Returns `simulated`, `provider`, `total` and the messages. `total` is
everything in scope, not just the page returned, so a caller can tell whether
the handful shown is the whole story.

### `POST /api/messages/dispatch`

Sends everything whose date has arrived. Returns how many were considered,
sent and failed.

In a real deployment this would be a scheduled job. It is exposed as an
endpoint so the queue can be pushed on demand, both for a demo and because a
supervisor watching a red case should not have to wait for a timer.

### `POST /api/messages/{message_id}/send`

Sends one message now, ignoring its scheduled date.

Returns 409 if it has already been sent, or if there is no phone number to send
it to.

---

## Dashboard

All three refuse a field worker with **403**. They use the phone app.

### `GET /api/dashboard/summary`

The headline counts: patients, risk spread, field workers, visits in the
window, visits today, failed visits, rule-only visits, open escalations, stale
escalations, overdue visits, due today. Takes `days`, default 7.

Also returns `scope_label`, the human description of what this user is seeing,
for example "Sanganer block" or "Sanganer PHC".

### `GET /api/dashboard/workers`

One row per field worker, ordered by what needs attention: open escalations
first, then overdue visits, then high risk patients.

`days_since_last_visit` is asked of the database separately from the activity
window, so an inactive worker reads as a real number of days and not as "no
visits recorded".

### `GET /api/dashboard/areas`

A village roll up: patients, high risk, medium, overdue, pregnant, infants.
Ordered by what needs attention.

---

## Status codes

| Code | Meaning here |
|---|---|
| 200, 201 | fine |
| 400 | bad input, or a rule refused it, like snoozing a high risk follow up |
| 401 | no token, or an expired one |
| 403 | a field worker asking for a supervisor endpoint |
| 404 | does not exist, **or is outside your scope** |
| 409 | a message already sent, or one with nobody to send it to |
| 413 | audio file too large |
