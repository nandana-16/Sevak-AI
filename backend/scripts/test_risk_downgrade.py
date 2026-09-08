"""Does a patient's risk actually come back down?

A risk level is a statement about *today*, not a label the patient keeps. If a
red patient is well at the next visit, the classification must fall - otherwise
the roster fills with permanent red and the colour stops meaning anything.

This is easy to get wrong: the agent sees the patient's recent visit history in
its context, so it can anchor on a previous red and refuse to let go.

Run:  python -m scripts.test_risk_downgrade
"""

from __future__ import annotations

import sys
import time
import uuid
import warnings

warnings.filterwarnings("ignore")

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
# Groq's free tier is 8k tokens/minute and a visit costs ~3.9k, so pace the
# sequence rather than letting it queue.
PACE_SECONDS = 32

# A deliberately unremarkable visit. No danger signs, normal vitals.
NORMAL = {
    "transcript": "Aaj routine jaanch thi. Koi shikayat nahi hai. Achha mahsoos kar "
                  "rahi hai, khana theek kha rahi hai, IFA goli roz le rahi hai. "
                  "Koi dard, bukhar ya sujan nahi hai.",
    "manual_fields": {"bp_systolic": 112, "bp_diastolic": 74, "hb": 12.1, "pulse": 78},
}

ALARMING = {
    "transcript": "Bahut tez sar dard hai, aankhon ke aage dhundla dikh raha hai, "
                  "pair me bahut sujan hai.",
    "manual_fields": {"bp_systolic": 168, "bp_diastolic": 112},
}


def submit(client: httpx.Client, patient_id: str, case: dict) -> dict:
    response = client.post("/api/visits", json={
        "client_uuid": str(uuid.uuid4()),
        "patient_id": patient_id,
        "transcript": case["transcript"],
        "manual_fields": case["manual_fields"],
        "input_mode": "voice",
        "language": "hi",
    })
    response.raise_for_status()
    return response.json()


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=180)
    login = client.post("/api/auth/login", json={"phone": "9000000002", "pin": "1234"})
    login.raise_for_status()
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    # Pick a pregnant patient - the category where anchoring is most likely,
    # because the record carries standing high-risk factors.
    roster = client.get("/api/patients", params={"category": "pregnant"}).json()
    if not roster:
        print("No pregnant patients seeded; run python -m app.seed --reset")
        return 1
    patient = roster[0]
    print(f"Patient: {patient['name']} (currently {patient['current_risk']})\n")

    failures = 0

    # 1. Drive the patient to red.
    print("1. Submitting an alarming visit (BP 168/112, headache, blurred vision)...")
    red = submit(client, patient["id"], ALARMING)
    print(f"   -> {red['risk_level'].upper()}  {red['risk_rationale'][:110]}")
    if red["risk_level"] != "red":
        print("   FAIL: expected red")
        failures += 1

    after_red = client.get(f"/api/patients/{patient['id']}").json()
    print(f"   patient.current_risk is now: {after_red['current_risk']}")
    if after_red["current_risk"] != "red":
        print("   FAIL: patient record did not pick up the red classification")
        failures += 1

    print(f"\n   (pausing {PACE_SECONDS}s for the free-tier token window)\n")
    time.sleep(PACE_SECONDS)

    # 2. Now a completely normal visit. The risk must come down.
    print("2. Submitting a normal visit (BP 112/74, Hb 12.1, no complaints)...")
    normal = submit(client, patient["id"], NORMAL)
    print(f"   -> {normal['risk_level'].upper()}  {normal['risk_rationale'][:110]}")
    if normal["risk_level"] == "red":
        print("   FAIL: still red after an unremarkable visit - the classifier is "
              "anchoring on history")
        failures += 1
    else:
        print(f"   ok: came down from red to {normal['risk_level']}")

    after_normal = client.get(f"/api/patients/{patient['id']}").json()
    print(f"   patient.current_risk is now: {after_normal['current_risk']}")
    if after_normal["current_risk"] != normal["risk_level"]:
        print("   FAIL: patient record does not match the latest visit")
        failures += 1
    if after_normal["current_risk"] == "red":
        print("   FAIL: patient is still flagged red on the roster")
        failures += 1

    print(f"\n   follow-up moved to {normal.get('next_visit_due')} "
          f"(was {red.get('next_visit_due')})")

    print(f"\n   (pausing {PACE_SECONDS}s)\n")
    time.sleep(PACE_SECONDS)

    # 3. A well patient with nothing on file must be able to reach green.
    #    If standing conditions pin everyone at yellow, the level stops
    #    distinguishing anyone just as surely as permanent red would.
    print("3. Checking a patient with a clean record can reach green...")
    clean = None
    # Search the whole roster, not just pregnancies - every seeded pregnant
    # patient happens to carry a condition or a high-risk factor.
    for row in client.get("/api/patients").json():
        detail = client.get(f"/api/patients/{row['id']}").json()
        ongoing = [c for c in detail.get("conditions", []) if c["ongoing"]]
        high_risk = (detail.get("pregnancy") or {}).get("high_risk_factors") or []
        if not ongoing and not high_risk:
            clean = detail
            break

    if clean is None:
        print("   (no seeded pregnant patient has a clean record - skipping)")
    else:
        print(f"   Patient: {clean['name']} (no ongoing conditions, no high-risk factors)")
        result = submit(client, clean["id"], NORMAL)
        print(f"   -> {result['risk_level'].upper()}  {result['risk_rationale'][:110]}")
        if result["risk_level"] == "green":
            print("   ok: a well patient with a clean record classifies green")
        else:
            print(f"   FAIL: expected green, got {result['risk_level']} - standing "
                  "context is inflating the level")
            failures += 1

    print()
    print("FAILED" if failures else "Risk moves in both directions correctly")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
