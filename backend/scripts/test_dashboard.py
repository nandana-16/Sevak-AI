"""Supervisor dashboard: scoping boundaries and the numbers behind them.

The dashboard is the one place where a user legitimately sees other people's
patients, so its scope rules are the thing most worth guarding. An ANM must see
her own workers and nobody else's; a BMO must see exactly the union of the ANMs
in his block; a field worker must not reach it at all.

Run:  python -m scripts.test_dashboard
"""

from __future__ import annotations

import sys
import warnings

warnings.filterwarnings("ignore")

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"

ASHA = "9000000002"      # Sunita Devi
ANM_1 = "9000000001"     # Dr. Anita Meena, Sanganer PHC
ANM_2 = "9000000006"     # Dr. Priya Yadav, Phagi PHC
BMO = "9000000000"       # Dr. Rajesh Sharma, Sanganer block

failures = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global failures
    if not ok:
        failures += 1
    print(f"[{'  ok  ' if ok else ' FAIL '}] {label}{(' - ' + detail) if detail else ''}")


def sign_in(phone: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=90)
    response = client.post("/api/auth/login", json={"phone": phone, "pin": "1234"})
    response.raise_for_status()
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


def main() -> int:
    asha = sign_in(ASHA)
    anm1 = sign_in(ANM_1)
    anm2 = sign_in(ANM_2)
    bmo = sign_in(BMO)

    # --- Access ------------------------------------------------------------
    for path in ("/api/dashboard/summary", "/api/dashboard/workers", "/api/dashboard/areas"):
        check(f"field worker refused {path}", asha.get(path).status_code == 403)

    check("dashboard needs a token",
          httpx.get(f"{BASE}/api/dashboard/summary", timeout=30).status_code == 401)

    # --- Scope -------------------------------------------------------------
    s1 = anm1.get("/api/dashboard/summary").json()
    s2 = anm2.get("/api/dashboard/summary").json()
    sb = bmo.get("/api/dashboard/summary").json()

    check("ANM scope is her PHC", s1["scope_label"].endswith("PHC"), s1["scope_label"])
    check("BMO scope is the block", "block" in sb["scope_label"], sb["scope_label"])

    w1 = {r["worker_id"] for r in anm1.get("/api/dashboard/workers").json()}
    w2 = {r["worker_id"] for r in anm2.get("/api/dashboard/workers").json()}
    wb = {r["worker_id"] for r in bmo.get("/api/dashboard/workers").json()}

    check("each ANM sees only her own workers", len(w1) == 2 and len(w2) == 2,
          f"{len(w1)} and {len(w2)}")
    check("the two ANM scopes do not overlap", not (w1 & w2))
    check("BMO sees exactly the union of both", wb == (w1 | w2),
          f"{len(wb)} vs {len(w1 | w2)}")

    check("patient counts add up",
          s1["total_patients"] + s2["total_patients"] == sb["total_patients"],
          f"{s1['total_patients']} + {s2['total_patients']} = {sb['total_patients']}")
    check("high-risk counts add up",
          s1["red"] + s2["red"] == sb["red"],
          f"{s1['red']} + {s2['red']} = {sb['red']}")

    # --- Areas -------------------------------------------------------------
    a1 = {a["village"] for a in anm1.get("/api/dashboard/areas").json()}
    ab = {a["village"] for a in bmo.get("/api/dashboard/areas").json()}
    check("ANM sees only her villages", a1 < ab, f"{sorted(a1)} within {sorted(ab)}")

    # --- Worker rows -------------------------------------------------------
    rows = bmo.get("/api/dashboard/workers").json()
    check("workers are ordered by what needs attention",
          rows == sorted(rows, key=lambda r: (-r["open_escalations"], -r["overdue_visits"],
                                              -r["red_patients"], r["name"])))
    check("only field workers are listed, not ANMs",
          all(r["name"].startswith(("Sunita", "Kamla", "Rekha", "Pushpa")) for r in rows),
          ", ".join(r["name"] for r in rows))

    # A worker whose last visit predates the activity window must still report
    # a real last-activity date, not read as though they had never worked.
    quiet = [r for r in rows if r["visits_in_window"] == 0]
    if quiet:
        check("an inactive worker still shows a real last-visit date",
              all(r["days_since_last_visit"] is not None for r in quiet),
              f"{quiet[0]['name']}: {quiet[0]['days_since_last_visit']} days")

    # --- The page itself ---------------------------------------------------
    page = httpx.get(f"{BASE}/dashboard", timeout=30)
    check("dashboard page is served", page.status_code == 200 and "SevakAI" in page.text)

    print()
    print(f"{failures} check(s) failed" if failures else "Dashboard scoping is correct")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
