"""The message outbox: what gets written, to whom, and who may read it.

The messages are a simulation, which is exactly why they need testing. The
thing most likely to go wrong with a mock is that it quietly stops resembling
the real flow - a message written to nobody, an alert repeated five times, or
an outbox that leaks one worker's families to another worker.

Every check here starts from a real visit going through the real pipeline, so
these are slow. That is the point: the outbox is a consequence of a
classification, not something written by hand.

Run:  python -m scripts.test_messages
"""

from __future__ import annotations

import sys
import uuid
import warnings

warnings.filterwarnings("ignore")

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"

ASHA = "9000000002"      # Sunita Devi, Bagru
OTHER_ASHA = "9000000004"  # Rekha Meena, Phagi - a different ANM's line
ANM = "9000000001"       # Dr. Anita Meena, supervises Sunita

failures = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global failures
    if not ok:
        failures += 1
    print(f"[{'  ok  ' if ok else ' FAIL '}] {label}{(' - ' + detail) if detail else ''}")


def sign_in(phone: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=300)
    response = client.post("/api/auth/login", json={"phone": phone, "pin": "1234"})
    response.raise_for_status()
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


def roster(client: httpx.Client) -> list[dict]:
    rows = client.get("/api/patients", params={"limit": 100}).json()
    return rows["items"] if isinstance(rows, dict) else rows


def detail(client: httpx.Client, patient_id: str) -> dict:
    """The roster row deliberately omits the phone number, so anything that
    needs one has to open the record - same as the app does."""
    return client.get(f"/api/patients/{patient_id}").json()


def record(client: httpx.Client, patient: dict, notes: str, language: str = "en") -> dict:
    response = client.post("/api/visits", json={
        "client_uuid": str(uuid.uuid4()),
        "patient_id": patient["id"],
        "typed_notes": notes,
        "input_mode": "typed",
        "language": language,
    })
    response.raise_for_status()
    return response.json()


def outbox(client: httpx.Client, **params) -> dict:
    return client.get("/api/messages", params={"limit": 200, **params}).json()


RED_NOTES = (
    "Heavy bleeding since last night, severe abdominal pain, very pale and "
    "feeling faint. BP 88/56, pulse 122."
)
WELL_NOTES = (
    "Mother feeling well. BP 110/70, no swelling, baby moving normally, "
    "taking IFA tablets daily."
)
# Danger signs for an infant rather than a mother, so the no-phone case is
# tested with symptoms that actually fit the patient.
INFANT_RED_NOTES = (
    "Baby is not feeding at all since yesterday, very drowsy and hard to wake, "
    "fast breathing, body feels cold to touch. Temperature 35.2."
)


def main() -> int:
    asha = sign_in(ASHA)
    anm = sign_in(ANM)
    other = sign_in(OTHER_ASHA)

    # --- Honesty ------------------------------------------------------------
    # The single most important property: nothing may claim to have been sent
    # for real while the mock provider is in use.
    box = outbox(anm)
    check("the outbox declares itself simulated", box["simulated"] is True,
          f"provider={box['provider']}")

    # --- Access -------------------------------------------------------------
    check("the outbox needs a token",
          httpx.get(f"{BASE}/api/messages", timeout=30).status_code == 401)

    escalated = {e["patient_id"] for e in anm.get("/api/escalations").json()}
    candidates = [
        detail(asha, p["id"])
        for p in roster(asha)
        if p["id"] not in escalated
        and p.get("category") in ("pregnant", "infant")
    ]
    # Infants have no phone of their own, so the undeliverable path is not a
    # rare edge case - it is most of the roster's under-ones.
    fresh = [p for p in candidates if p.get("phone") and p["category"] == "pregnant"]
    without_phone = [p for p in candidates if not p.get("phone")]
    check("the demo data contains patients with no phone", bool(without_phone),
          f"{len(without_phone)} of {len(candidates)} candidates")
    if len(fresh) < 2:
        print("Not enough un-escalated patients to test with; run demo_reset first.")
        return 1

    # --- A red visit writes to the family and to the supervisor -------------
    subject = fresh[0]
    before = {m["id"] for m in outbox(anm)["messages"]}
    visit = record(asha, subject, RED_NOTES)
    check("the test visit classified red", visit["risk_level"] == "red",
          visit["risk_level"])

    new = [m for m in outbox(anm)["messages"] if m["id"] not in before]
    kinds = {m["message_type"] for m in new}
    check("a red visit writes to the family", "referral" in kinds, str(sorted(kinds)))
    check("a red visit alerts the supervisor", "escalation" in kinds, str(sorted(kinds)))

    referral = next(m for m in new if m["message_type"] == "referral")
    alert = next(m for m in new if m["message_type"] == "escalation")
    check("the referral goes to the patient's own number",
          referral["to_phone"] == subject["phone"], str(referral["to_phone"]))
    check("the alert goes to the supervising ANM",
          alert["to_phone"] == ANM, str(alert["to_phone"]))
    check("the referral carries the agent's advice, not a template stub",
          len(referral["body"]) > 120 and subject["name"] in referral["body"])
    check("the alert names the patient and the worker",
          subject["name"] in alert["body"] and "Sunita" in alert["body"])

    # --- The same red again must not re-alert -------------------------------
    before = {m["id"] for m in outbox(anm)["messages"]}
    record(asha, subject, RED_NOTES)
    repeat = [m for m in outbox(anm)["messages"] if m["id"] not in before]
    repeat_kinds = {m["message_type"] for m in repeat}
    check("a repeat red does not send a second alert about the same case",
          "escalation" not in repeat_kinds, str(sorted(repeat_kinds)))
    check("a repeat red still tells the family again",
          "referral" in repeat_kinds, str(sorted(repeat_kinds)))

    # --- A routine visit schedules a reminder, not a referral ---------------
    routine = fresh[1]
    before = {m["id"] for m in outbox(anm)["messages"]}
    visit = record(asha, routine, WELL_NOTES)
    new = [m for m in outbox(anm)["messages"] if m["id"] not in before]
    kinds = {m["message_type"] for m in new}
    check("a routine visit sends no referral", "referral" not in kinds,
          str(sorted(kinds)))
    if visit["risk_level"] != "red":
        reminder = next((m for m in new if m["message_type"] == "reminder"), None)
        check("a routine visit schedules a reminder", reminder is not None)
        if reminder:
            check("the reminder waits rather than sending immediately",
                  reminder["status"] == "scheduled", reminder["status"])
            check("the reminder is held until shortly before the visit",
                  reminder["send_after"] is not None, str(reminder["send_after"]))

    # --- A patient with no phone ---------------------------------------------
    # This must not be silently dropped: somebody still has to be told.
    if without_phone:
        before = {m["id"] for m in outbox(anm)["messages"]}
        record(asha, without_phone[0], INFANT_RED_NOTES)
        new = [m for m in outbox(anm)["messages"] if m["id"] not in before]
        family = [m for m in new if m["message_type"] == "referral"]
        check("a patient with no phone still gets a message written",
              bool(family), f"{len(new)} messages")
        if family:
            check("that message is marked undeliverable rather than sent",
                  family[0]["status"] == "no_contact", family[0]["status"])
            check("and it says why, so the worker knows to deliver it by hand",
                  bool(family[0]["error"]), str(family[0]["error"]))

    # --- Dispatch -----------------------------------------------------------
    result = anm.post("/api/messages/dispatch").json()
    check("dispatch reports itself as simulated", result["simulated"] is True)
    check("dispatch sent the messages that were due", result["sent"] >= 1, str(result))
    still_due = [m for m in outbox(anm, status="scheduled")["messages"]
                 if m["send_after"] and m["send_after"] <= str(__import__("datetime").date.today())]
    check("nothing due is left behind after a dispatch", not still_due,
          f"{len(still_due)} left")
    check("a message with no number is never marked sent",
          all(m["to_phone"] for m in outbox(anm, status="sent")["messages"]))

    # --- Scope ---------------------------------------------------------------
    # Give the unrelated worker a message of her own, so the isolation checks
    # below compare two populated outboxes rather than passing vacuously.
    other_roster = [p for p in roster(other) if p.get("category") == "pregnant"]
    if other_roster:
        record(other, detail(other, other_roster[0]["id"]), RED_NOTES)

    mine = {m["id"] for m in outbox(asha)["messages"]}
    theirs = {m["id"] for m in outbox(other)["messages"]}
    supervisor = {m["id"] for m in outbox(anm)["messages"]}
    check("a worker does not see another worker's messages", not (mine & theirs),
          f"{len(mine & theirs)} shared")
    check("the ANM sees her own worker's messages", mine <= supervisor,
          f"{len(mine - supervisor)} missing")

    # An id from outside the caller's scope must not be reachable directly.
    if theirs:
        foreign = next(iter(theirs))
        check("one worker cannot send another worker's message",
              asha.post(f"/api/messages/{foreign}/send").status_code == 404)

    print()
    print(f"{failures} check(s) failed" if failures else "The outbox behaves correctly")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
