# Testing Workflow — Every Feature, Manually

Two ways to test: this doc (click through the actual UI, ~15 min, good for rehearsing
the demo) or `backend/scripts/smoke_test.sh` (hits every API endpoint via curl in ~3
min, good for a quick regression check after code changes). Both assume the backend,
worker app, and dashboard are already running (see [README.md](../README.md)).

Each live voice submission calls Gemini 3 times in sequence (extraction → risk →
actions) and takes **~30-40 seconds**. That's normal, not a hang.

---

## Part 1 — ASHA Worker App (http://localhost:5173)

### 1. Login
Log in as `9999900001` / `1234` (Sunita Sharma). Confirms auth + JWT issuance.

### 2. Patient list
Confirms `GET /patients/{worker_id}` and risk badges (RED/YELLOW/GREEN) render from
each patient's most recent visit.

### 3. Record a LOW-risk visit
Open **Meera Patil** → type or speak:
> "Sab kuch normal tha, BP 118 over 76, patient ne saari dawaiyan sahi se li hain."

Expect: GREEN/LOW, drivers citing `NHM-MH-01` (routine screening, nothing abnormal),
only `whatsapp` + `followup` actions (no referral).

### 4. Record a HIGH-risk visit (the SRS demo script)
Same patient →
> "Meera Patil, 28 saal, 7 mahine ki pregnancy. Aaj BP 140 over 90 tha. Usne pichle 2
> hafte se iron tablets nahi li. Pati bahar gaya hua hai."

Expect: RED/HIGH, drivers citing `NHM-MH-04` (pre-eclampsia), `NHM-MH-02` (anemia/IFA),
`NHM-SOC-01` (social isolation), and all three actions including a `referral`.

### 5. Record a visit exercising a *different* protocol category
Proves the RAG retrieval isn't hardcoded to pregnancy/BP — try a child-health or
general-symptom scenario, e.g.:
> "Bacha 2 saal ka hai, dast ho rahe hain, aankhen andar dhasi hui lagti hain aur bacha
> sust hai."

Expect drivers citing `NHM-CH-03` (dehydration assessment), likely HIGH.

### 6. Edit-before-confirm
Record/type something, then edit the transcript text box before hitting **Confirm &
Process** — confirms FR-01.4 (worker can correct the transcript before it's processed).

### 7. Tasks screen
Tap **Tasks** — confirms follow-ups are aggregated across patients and sorted HIGH →
MEDIUM → LOW.

### 8. Offline mode + auto-sync
1. Open DevTools → Network tab → set to "Offline" (or just disconnect network).
2. Record a visit and confirm. You should see the yellow "Saved offline" toast, not a
   processed result — this proves the app degrades gracefully instead of erroring.
3. Go back online. Within moments the offline banner should show "N visit(s) pending
   sync" with a **Sync now** button — click it (or wait for the automatic `online`
   event listener to fire sync itself).
4. Confirm the visit now appears with a processed risk badge — this is the same
   pipeline running server-side after the fact, proving offline-to-online parity.

### 9. Role boundary
Log out, try logging in with a BMO account (`9999900003` / `1234`) — the app should
refuse with "This is the ASHA worker app" rather than silently letting a supervisor in.

---

## Part 2 — District Dashboard (http://localhost:5174)

### 1. Login as BMO
`9999900003` / `1234` (Rajesh Kulkarni).

### 2. Metrics row
Confirms `visits_today`, `high_risk_cases` (today-scoped), `pending_followups`, and
`hmis_completion_rate` all populate.

### 3. Heatmap
Confirms villages render as colored circle markers (red/yellow/green by risk) on the
Leaflet/OpenStreetMap base layer — zoom/pan to confirm tiles load.

### 4. Escalations table
Shows the top 20 oldest unactioned HIGH-risk cases with hours-elapsed and an OVERDUE
tag past 48h. Click **Mark Actioned** on one — it should disappear from the list on
the next 30-second auto-refresh (or reload the page immediately to see it right away).

### 5. HMIS report
Scroll to the HMIS panel, paste in Sunita's worker ID (visible in the worker app's
browser localStorage under `sevakai_auth`, or grab it from `GET /api/v1/patients/...`
responses), set month/year to the current month, click **Generate** — confirms the PDF
downloads and lists the visits recorded above.

### 6. Login as ANM instead
`9999900002` / `1234` (Kavita Joshi) — same dashboard, confirms the role check accepts
ANM too, not just BMO.

### 7. Role boundary
Try logging in with the ASHA account (`9999900001` / `1234`) — should be refused with
"This dashboard is for ANM/BMO/Admin roles."

---

## Part 3 — Things with no UI yet (API-only, use curl or /docs)

- **Escalation sweep**: runs automatically every 5 minutes in the background
  (`app/services/escalation_monitor.py`); 174 seeded overdue cases already demonstrate
  its output without waiting. To watch it fire live, temporarily lower
  `ESCALATION_THRESHOLD_HOURS` in `.env` to something small (e.g. `0.01`) and restart.
- **Audit log**: every state-changing action (login, visit processed, override,
  escalation fired) writes to the `audit_log` table. No viewer UI yet — inspect via
  `sqlite3 backend/data/sevakai.db "select * from audit_log order by timestamp desc limit 20;"`.
- **Risk override**: `POST /api/v1/visits/{visit_id}/override?reason=...&new_level=...`
  — exercised in `smoke_test.sh` Part 6; no dashboard button wired up yet.

---

## Automated version

```bash
API_BASE=http://localhost:8010 bash backend/scripts/smoke_test.sh
```

Hits auth (all 4 roles + a rejected-login check), patient list + cross-worker RBAC
block, 3 live pipeline runs across different risk levels/protocols, offline sync,
tasks, risk override + audit log, dashboard metrics/heatmap/escalations + a
BMO-only-endpoint RBAC block, and HMIS PDF generation+download. Prints PASS/FAIL per
check — rerun anytime after a code change as a fast regression check.
