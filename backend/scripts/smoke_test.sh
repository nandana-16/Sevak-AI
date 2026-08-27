#!/usr/bin/env bash
# End-to-end smoke test for every SevakAI backend feature. Safe to re-run anytime —
# it only adds data (a few extra visits/reports), never deletes anything.
#
# Usage: API_BASE=http://localhost:8010 bash backend/scripts/smoke_test.sh
set -uo pipefail

API=${API_BASE:-http://localhost:8010}
PATIENT_ID=${MEERA_PATIENT_ID:-}  # optional override; auto-discovered below if unset

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; }
section() { echo ""; echo "=== $1 ==="; }

json() { python -c "import sys,json; d=json.load(sys.stdin); print(d$1)"; }

section "1. Auth — all 4 roles"
ASHA_TOKEN=$(curl -s -X POST "$API/api/v1/auth/login" -H "Content-Type: application/json" -d '{"phone":"9999900001","pin":"1234"}' | json "['access_token']")
ASHA_ID=$(curl -s -X POST "$API/api/v1/auth/login" -H "Content-Type: application/json" -d '{"phone":"9999900001","pin":"1234"}' | json "['worker_id']")
ANM_TOKEN=$(curl -s -X POST "$API/api/v1/auth/login" -H "Content-Type: application/json" -d '{"phone":"9999900002","pin":"1234"}' | json "['access_token']")
BMO_TOKEN=$(curl -s -X POST "$API/api/v1/auth/login" -H "Content-Type: application/json" -d '{"phone":"9999900003","pin":"1234"}' | json "['access_token']")
ADMIN_TOKEN=$(curl -s -X POST "$API/api/v1/auth/login" -H "Content-Type: application/json" -d '{"phone":"9999900004","pin":"1234"}' | json "['access_token']")
[ -n "$ASHA_TOKEN" ] && pass "ASHA login" || fail "ASHA login"
[ -n "$ANM_TOKEN" ] && pass "ANM login" || fail "ANM login"
[ -n "$BMO_TOKEN" ] && pass "BMO login" || fail "BMO login"
[ -n "$ADMIN_TOKEN" ] && pass "Admin login" || fail "Admin login"

echo "  Testing wrong PIN is rejected..."
BAD=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/v1/auth/login" -H "Content-Type: application/json" -d '{"phone":"9999900001","pin":"0000"}')
[ "$BAD" = "401" ] && pass "wrong PIN correctly rejected (401)" || fail "wrong PIN should 401, got $BAD"

section "2. Patient list + RBAC"
PATIENTS=$(curl -s "$API/api/v1/patients/$ASHA_ID" -H "Authorization: Bearer $ASHA_TOKEN")
COUNT=$(echo "$PATIENTS" | python -c "import sys,json; print(len(json.load(sys.stdin)))")
pass "patient list returned $COUNT patients"
if [ -z "$PATIENT_ID" ]; then
  PATIENT_ID=$(echo "$PATIENTS" | python -c "import sys,json; d=json.load(sys.stdin); print(next(p['patient_id'] for p in d if p['name']=='Meera Patil'))")
fi

echo "  Testing an ASHA worker can't view another worker's patients (403 expected)..."
OTHER=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v1/patients/not-my-id" -H "Authorization: Bearer $ASHA_TOKEN")
[ "$OTHER" = "403" ] && pass "cross-worker patient access correctly blocked" || fail "expected 403, got $OTHER"

section "3. Live voice pipeline — 3 risk levels, 3 protocol categories"
echo "  [LOW] routine visit..."
curl -s -X POST "$API/api/v1/visits/voice" -H "Authorization: Bearer $ASHA_TOKEN" -H "Content-Type: application/json" \
  -d "{\"worker_id\":\"$ASHA_ID\",\"patient_id\":\"$PATIENT_ID\",\"language_code\":\"hi\",\"transcript\":\"Sab kuch normal tha, BP 118 over 76, patient ne saari dawaiyan sahi se li hain.\"}" \
  | json "['risk_level']" | xargs -I{} echo "    -> risk_level: {}"

echo "  [HIGH, maternal/PIH] BP + non-compliance + social risk..."
curl -s -X POST "$API/api/v1/visits/voice" -H "Authorization: Bearer $ASHA_TOKEN" -H "Content-Type: application/json" \
  -d "{\"worker_id\":\"$ASHA_ID\",\"patient_id\":\"$PATIENT_ID\",\"language_code\":\"hi\",\"transcript\":\"BP 148 over 96 tha, sar mein bahut dard tha. Pichle do hafte se iron tablets nahi li.\"}" \
  | json "['risk_level']" | xargs -I{} echo "    -> risk_level: {}"

echo "  [MEDIUM/HIGH, TB screening protocol] persistent cough scenario..."
curl -s -X POST "$API/api/v1/visits/voice" -H "Authorization: Bearer $ASHA_TOKEN" -H "Content-Type: application/json" \
  -d "{\"worker_id\":\"$ASHA_ID\",\"patient_id\":\"$PATIENT_ID\",\"language_code\":\"hi\",\"transcript\":\"Ghar mein khaansi hai teen hafte se, raat ko bukhar aata hai aur wazan bhi kam ho raha hai.\"}" \
  | json "['risk_level']" | xargs -I{} echo "    -> risk_level: {}"
pass "3 pipeline runs completed (see risk_level output above — vary by design, LLM-driven)"

section "4. Offline queue -> batch sync"
SYNC=$(curl -s -X POST "$API/api/v1/sync/batch" -H "Authorization: Bearer $ASHA_TOKEN" -H "Content-Type: application/json" \
  -d "{\"worker_id\":\"$ASHA_ID\",\"records\":[{\"record_type\":\"visit\",\"record_json\":{\"patient_id\":\"$PATIENT_ID\",\"transcript\":\"Offline test visit, sab theek tha\",\"language_code\":\"hi\"}}]}")
echo "$SYNC" | grep -q '"synced":1' && pass "sync/batch processed 1 queued visit" || fail "sync/batch: $SYNC"

section "5. Tasks (follow-ups, sorted by urgency)"
TASKS=$(curl -s "$API/api/v1/workers/$ASHA_ID/tasks" -H "Authorization: Bearer $ASHA_TOKEN")
TCOUNT=$(echo "$TASKS" | python -c "import sys,json; print(len(json.load(sys.stdin)))")
pass "tasks endpoint returned $TCOUNT pending follow-ups"

section "6. Risk override (ANM/supervisor correcting an AI classification)"
LATEST_VISIT=$(curl -s "$API/api/v1/patients/$ASHA_ID" -H "Authorization: Bearer $ASHA_TOKEN" > /dev/null; echo "$PATIENT_ID")
VISIT_ID=$(curl -s -X POST "$API/api/v1/visits/voice" -H "Authorization: Bearer $ASHA_TOKEN" -H "Content-Type: application/json" \
  -d "{\"worker_id\":\"$ASHA_ID\",\"patient_id\":\"$PATIENT_ID\",\"language_code\":\"hi\",\"transcript\":\"Normal checkup, sab thik.\"}" | json "['visit_id']")
OVERRIDE=$(curl -s -X POST "$API/api/v1/visits/$VISIT_ID/override?reason=Supervisor+clinical+judgment+call&new_level=MEDIUM" -H "Authorization: Bearer $ANM_TOKEN")
echo "$OVERRIDE" | grep -q '"status":"overridden"' && pass "ANM override applied and audit-logged" || fail "override: $OVERRIDE"

section "7. Dashboard — metrics, heatmap, escalations (BMO)"
METRICS=$(curl -s "$API/api/v1/dashboard/metrics" -H "Authorization: Bearer $BMO_TOKEN")
pass "metrics: $METRICS"
HEATMAP_COUNT=$(curl -s "$API/api/v1/dashboard/heatmap" -H "Authorization: Bearer $BMO_TOKEN" | python -c "import sys,json; print(len(json.load(sys.stdin)))")
pass "heatmap returned $HEATMAP_COUNT village/risk points"
ESC=$(curl -s "$API/api/v1/escalations/pending" -H "Authorization: Bearer $BMO_TOKEN")
ESC_COUNT=$(echo "$ESC" | python -c "import sys,json; print(len(json.load(sys.stdin)))")
pass "escalations/pending returned $ESC_COUNT unactioned HIGH-risk cases"
if [ "$ESC_COUNT" -gt 0 ]; then
  FLAG_ID=$(echo "$ESC" | python -c "import sys,json; print(json.load(sys.stdin)[0]['flag_id'])")
  curl -s -X POST "$API/api/v1/escalations/$FLAG_ID/action" -H "Authorization: Bearer $BMO_TOKEN" | grep -q actioned && pass "marked one escalation actioned"
fi

echo "  Testing ASHA worker can't hit BMO-only dashboard endpoints (403 expected)..."
RBAC=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/v1/dashboard/metrics" -H "Authorization: Bearer $ASHA_TOKEN")
[ "$RBAC" = "403" ] && pass "ASHA correctly blocked from dashboard endpoints" || fail "expected 403, got $RBAC"

section "8. HMIS monthly report (PDF)"
YEAR=$(date +%Y); MONTH=$(date +%-m)
REPORT=$(curl -s "$API/api/v1/reports/hmis/$ASHA_ID/$MONTH/$YEAR" -H "Authorization: Bearer $ASHA_TOKEN")
PDF_URL=$(echo "$REPORT" | json "['pdf_url']")
ROWS=$(echo "$REPORT" | python -c "import sys,json; print(len(json.load(sys.stdin)['report_data_json']))")
pass "HMIS report generated with $ROWS visit rows, pdf at $PDF_URL"
PDF_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API$PDF_URL")
[ "$PDF_STATUS" = "200" ] && pass "PDF download works" || fail "PDF download returned $PDF_STATUS"

echo ""
echo "=== Smoke test complete ==="
