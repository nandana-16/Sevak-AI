"""Escalation lifecycle: one open alert per patient, annotated when they improve.

Run:  python -m scripts.test_escalations
"""

from __future__ import annotations

import sys
import time
import uuid
import warnings

warnings.filterwarnings("ignore")

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
PACE_SECONDS = 32
failures = 0

ALARMING = {
    "transcript": "Bahut tez sar dard hai, dhundla dikh raha hai, pair me sujan hai.",
    "manual_fields": {"bp_systolic": 172, "bp_diastolic": 114},
}
ALARMING_AGAIN = {
    "transcript": "Aaj bhi sar dard hai aur sujan badh gayi hai.",
    "manual_fields": {"bp_systolic": 178, "bp_diastolic": 118},
}
NORMAL = {
    "transcript": "Aaj koi shikayat nahi hai, achha mahsoos kar rahi hai.",
    "manual_fields": {"bp_systolic": 114, "bp_diastolic": 76, "hb": 12.2},
}


def check(label: str, ok: bool, detail: str = "") -> None:
    global failures
    if not ok:
        failures += 1
    print(f"[{'  ok  ' if ok else ' FAIL '}] {label}{(' - ' + detail) if detail else ''}")


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=180)
    login = client.post("/api/auth/login", json={"phone": "9000000002", "pin": "1234"})
    login.raise_for_status()
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    patient = client.get("/api/patients", params={"category": "pregnant"}).json()[-1]
    pid = patient["id"]
    print(f"Patient: {patient['name']}\n")

    def submit(case: dict) -> dict:
        response = client.post("/api/visits", json={
            "client_uuid": str(uuid.uuid4()), "patient_id": pid,
            "transcript": case["transcript"], "manual_fields": case["manual_fields"],
            "input_mode": "voice", "language": "hi",
        })
        response.raise_for_status()
        return response.json()

    def open_for_patient() -> list[dict]:
        return [e for e in client.get("/api/escalations").json() if e["patient_id"] == pid]

    before = len(open_for_patient())

    print("1. First red visit...")
    first = submit(ALARMING)
    check("classified red", first["risk_level"] == "red", first["risk_level"])
    after_first = open_for_patient()
    check("escalation raised", len(after_first) == before + 1,
          f"{before} -> {len(after_first)} open")

    print(f"\n   (pausing {PACE_SECONDS}s)\n")
    time.sleep(PACE_SECONDS)

    print("2. Second red visit for the same patient...")
    second = submit(ALARMING_AGAIN)
    check("classified red again", second["risk_level"] == "red", second["risk_level"])
    after_second = open_for_patient()
    check("no duplicate escalation", len(after_second) == len(after_first),
          f"{len(after_second)} open (expected {len(after_first)})")
    if after_second:
        check("escalation points at the newest visit",
              after_second[0]["visit_id"] == second["id"])

    print(f"\n   (pausing {PACE_SECONDS}s)\n")
    time.sleep(PACE_SECONDS)

    print("3. Patient improves...")
    third = submit(NORMAL)
    check("risk came down", third["risk_level"] != "red", third["risk_level"])
    after_third = open_for_patient()
    check("escalation stays open for a human to acknowledge",
          len(after_third) == len(after_second),
          "a red event still needs sign-off")

    profile = client.get(f"/api/patients/{pid}").json()
    check("patient no longer flagged red on the roster",
          profile["current_risk"] != "red", profile["current_risk"])

    print()
    print(f"{failures} check(s) failed" if failures else "Escalation lifecycle is correct")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
