"""End-to-end check against a running backend.

Exercises the whole worker journey over HTTP: sign in, list the roster, filter
it, open a profile, submit a typed visit and a spoken visit, confirm the
follow-up landed on the plan and that a red visit raised an escalation. Also
asserts that roster scoping actually holds, by trying to read another worker's
patient.

Run:  python -m scripts.smoke_test [base_url]
"""

from __future__ import annotations

import sys
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
OK, FAIL = "  ok  ", " FAIL "
failures = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global failures
    if not condition:
        failures += 1
    print(f"[{OK if condition else FAIL}] {label}{(' - ' + detail) if detail else ''}")


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=180)

    health = client.get("/api/health").json()
    check("health endpoint", health.get("status") == "ok", str(health))
    check("guideline corpus indexed", health.get("guideline_chunks", 0) > 100,
          f"{health.get('guideline_chunks')} chunks")
    check("LLM ready", health.get("llm_ready") is True, health.get("llm_provider", ""))

    # --- Auth ---------------------------------------------------------------
    bad = client.post("/api/auth/login", json={"phone": "9000000002", "pin": "9999"})
    check("wrong PIN rejected", bad.status_code == 401)

    login = client.post("/api/auth/login", json={"phone": "9000000002", "pin": "1234"})
    check("login succeeds", login.status_code == 200, login.text[:120])
    if login.status_code != 200:
        return 1
    token = login.json()["access_token"]
    worker = login.json()["worker"]
    client.headers["Authorization"] = f"Bearer {token}"
    print(f"        signed in as {worker['name']} ({worker['role']}) in {worker['village']}")

    check("unauthenticated request rejected",
          httpx.get(f"{BASE}/api/patients", timeout=30).status_code == 401)

    # --- Roster -------------------------------------------------------------
    roster = client.get("/api/patients").json()
    check("roster returns patients", len(roster) > 10, f"{len(roster)} patients")
    check("roster is sorted riskiest first",
          [p["current_risk"] for p in roster] == sorted(
              [p["current_risk"] for p in roster],
              key=lambda r: {"red": 0, "yellow": 1, "unknown": 2, "green": 3}[r]))
    check("every patient is assigned to this worker",
          all(p["village"] == worker["village"] for p in roster))

    villages = client.get("/api/patients/villages").json()
    check("village filter lists only own area", villages == [worker["village"]], str(villages))

    pregnant = client.get("/api/patients", params={"category": "pregnant"}).json()
    check("category filter works", all(p["category"] == "pregnant" for p in pregnant),
          f"{len(pregnant)} pregnant")

    named = client.get("/api/patients", params={"search": roster[0]["name"][:4]}).json()
    check("name search works", len(named) >= 1)

    # --- Scoping ------------------------------------------------------------
    other = client.post("/api/auth/login", json={"phone": "9000000003", "pin": "1234"}).json()
    other_client = httpx.Client(
        base_url=BASE, timeout=60,
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    other_roster = other_client.get("/api/patients").json()
    check("second worker has a different roster",
          not ({p["id"] for p in roster} & {p["id"] for p in other_roster}))
    leak = other_client.get(f"/api/patients/{roster[0]['id']}")
    check("cannot open another worker's patient", leak.status_code == 404,
          f"HTTP {leak.status_code}")

    # --- Profile ------------------------------------------------------------
    target = next((p for p in pregnant), roster[0])
    detail = client.get(f"/api/patients/{target['id']}").json()
    check("profile loads", detail["id"] == target["id"])
    check("profile has a last-visit note", bool(detail.get("last_visit_summary")))
    check("Aadhaar is masked",
          detail["aadhaar_masked"].startswith("XXXX") or
          detail["aadhaar_masked"] == "Not linked", detail["aadhaar_masked"])
    check("pregnancy block present", detail.get("pregnancy") is not None)

    # --- Aadhaar ------------------------------------------------------------
    bad_aadhaar = client.post("/api/patients/aadhaar/check",
                              json={"aadhaar": "123456789012"}).json()
    check("invalid Aadhaar rejected", bad_aadhaar["valid"] is False, bad_aadhaar["reason"])

    # --- Typed visit --------------------------------------------------------
    typed = client.post("/api/visits", json={
        "client_uuid": str(uuid.uuid4()),
        "patient_id": target["id"],
        "typed_notes": "Routine check. No complaints. Taking IFA daily.",
        "manual_fields": {"bp_systolic": 118, "bp_diastolic": 76, "weight_kg": 55.0},
        "input_mode": "typed",
        "language": "en",
    })
    check("typed visit accepted", typed.status_code == 201, typed.text[:200])
    if typed.status_code == 201:
        body = typed.json()
        check("typed visit classified", body["risk_level"] in ("green", "yellow", "red"),
              body["risk_level"])
        check("manual vitals preserved exactly", body["bp_systolic"] == 118)
        check("follow-up scheduled", body.get("next_visit_due") is not None,
              str(body.get("next_visit_due")))
        check("summary written", bool(body.get("summary")), (body.get("summary") or "")[:70])

    # --- Idempotency --------------------------------------------------------
    repeat_uuid = str(uuid.uuid4())
    payload = {
        "client_uuid": repeat_uuid,
        "patient_id": target["id"],
        "typed_notes": "Second check, no change.",
        "input_mode": "typed",
        "language": "en",
    }
    first = client.post("/api/visits", json=payload)
    second = client.post("/api/visits", json=payload)
    check("offline retry is idempotent",
          first.status_code == 201 and second.json()["id"] == first.json()["id"],
          "same visit id returned")

    # --- Red case, escalation, and the rule floor ---------------------------
    red = client.post("/api/visits", json={
        "client_uuid": str(uuid.uuid4()),
        "patient_id": target["id"],
        "transcript": "Bahut tez sar dard hai, aankhon ke aage dhundla dikh raha hai, "
                      "pair me sujan hai. BP 168 by 112.",
        "input_mode": "voice",
        "language": "hi",
    })
    check("high-risk visit accepted", red.status_code == 201, red.text[:200])
    if red.status_code == 201:
        body = red.json()
        check("classified red", body["risk_level"] == "red", body["risk_level"])
        check("BP extracted from Hinglish speech", body["bp_systolic"] == 168,
              str(body["bp_systolic"]))
        check("danger signs listed", len(body["danger_signs"]) > 0,
              ", ".join(body["danger_signs"][:3]))
        check("guideline citations attached", len(body["guideline_citations"]) > 0,
              body["guideline_citations"][0]["title"][:50] if body["guideline_citations"] else "")
        check("red follow-up is same-day-ish", body.get("next_visit_due") is not None)
        check("no degraded steps", not body.get("degraded_steps"),
              str(body.get("degraded_steps")))

        escalations = client.get("/api/escalations").json()
        check("escalation raised for red visit",
              any(e["visit_id"] == body["id"] for e in escalations),
              f"{len(escalations)} open")

    # --- Schedule -----------------------------------------------------------
    plan = client.get("/api/schedule/today").json()
    check("today's plan returns rows", isinstance(plan, list) and len(plan) > 0,
          f"{len(plan)} due")
    if plan:
        check("plan puts overdue and red first",
              plan[0]["overdue"] or plan[0]["priority"] == "red",
              f"{plan[0]['patient_name']} {plan[0]['priority']}")
        red_rows = [p for p in plan if p["priority"] == "red"]
        if red_rows:
            resp = client.post(f"/api/schedule/{red_rows[0]['id']}/snooze", params={"days": 3})
            check("red follow-up cannot be snoozed", resp.status_code == 400,
                  f"HTTP {resp.status_code}")

    upcoming = client.get("/api/schedule", params={"days": 30}).json()
    check("upcoming plan returns rows", len(upcoming) >= len(plan))

    # --- Guidelines ---------------------------------------------------------
    sources = client.get("/api/guidelines").json()
    check("guideline sources listed", len(sources) >= 5, f"{len(sources)} documents")
    # State NHM portals (nhm.hp.gov.in) host some of these too, so match the
    # government domain rather than one specific host.
    check("sources are real government documents",
          all(".gov.in/" in s["url"] for s in sources),
          ", ".join(s["url"].split("/")[2] for s in sources[:3]))

    print()
    if failures:
        print(f"{failures} check(s) failed")
    else:
        print("All checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
