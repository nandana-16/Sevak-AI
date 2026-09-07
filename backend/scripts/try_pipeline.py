"""Run the agent pipeline against seeded patients without going through HTTP.

Useful for tuning prompts and for checking the rule floor still bites.

Run:  python -m scripts.try_pipeline
"""

from __future__ import annotations

import logging
import sys
import warnings

warnings.filterwarnings("ignore")

from app.agents import pipeline
from app.core.database import SessionLocal
from app.models.db import Patient, PatientCategory, Visit

logging.basicConfig(level=logging.WARNING)

RESET = "\033[0m"
COLOURS = {"red": "\033[91m", "yellow": "\033[93m", "green": "\033[92m", "unknown": "\033[90m"}

CASES = [
    (
        PatientCategory.pregnant,
        "hi",
        "Sunita ji ko teen din se bahut tez sar dard hai aur aankhon ke aage dhundla "
        "dikhai de raha hai. Pair me bahut sujan hai. BP naapa to 158 by 104 aaya. "
        "Bola ki bachcha kal se kam hil raha hai.",
    ),
    (
        PatientCategory.pregnant,
        "hi",
        "Aaj routine check tha. Koi shikayat nahi hai. BP 112 by 74. Vazan 54 kilo. "
        "IFA goli roz le rahi hai. Khana theek kha rahi hai.",
    ),
    (
        PatientCategory.infant,
        "hi",
        "Bachcha do din se doodh nahi pi raha, bahut susti hai, chhune par thanda lag "
        "raha hai. Saans tez chal rahi hai aur pasli chal rahi hai. Naabhi ke paas "
        "laal hai thoda mavaad bhi hai.",
    ),
    (
        PatientCategory.adult,
        "en",
        "She says she feels weak and dizzy for about two weeks. Looks pale. "
        "Haemoglobin card shows 6.2. No fever, no bleeding.",
    ),
]


def pick(db, category: PatientCategory) -> Patient | None:
    return db.query(Patient).filter(Patient.category == category).first()


def main() -> int:
    db = SessionLocal()
    try:
        for category, language, transcript in CASES:
            patient = pick(db, category)
            if patient is None:
                print(f"no seeded patient for {category.value}; run python -m app.seed")
                continue

            visit = Visit(
                client_uuid="dry-run",
                patient_id=patient.id,
                worker_id=patient.assigned_worker_id,
                transcript=transcript,
                language=language,
            )

            print("=" * 100)
            print(f"PATIENT  {patient.name} ({category.value})")
            print(f"SAID     {transcript[:180]}")
            state = pipeline.run(patient, visit)

            level = state.get("risk_level", "unknown")
            colour = COLOURS.get(level, "")
            print(f"\n  RISK     {colour}{level.upper()}{RESET} "
                  f"(confidence {state.get('risk_confidence', 0):.2f}, "
                  f"rules said {state.get('rule_level')})")
            print(f"  WHY      {state.get('risk_rationale', '')}")
            if state.get("danger_signs"):
                print(f"  SIGNS    {', '.join(state['danger_signs'])}")
            print(f"  VITALS   {state.get('vitals')}")
            print(f"  SYMPTOMS {', '.join(state.get('symptoms') or []) or '-'}")
            print("  ACTIONS")
            for action in state.get("actions", []):
                print(f"    [{action['urgency']:>10}] {action['action']}")
            print(f"  FOLLOW-UP in {state.get('follow_up_in_days')} days "
                  f"- {state.get('follow_up_reason')}")
            print(f"  SUMMARY  {state.get('summary')}")
            print("  CITED")
            for citation in state.get("citations", [])[:3]:
                print(f"    - {citation['title'][:60]} p.{citation['page']} "
                      f"({citation['score']:.2f})")
            if state.get("degraded_steps"):
                print(f"  DEGRADED {state['degraded_steps']}")
            print(f"  TOOK     {state.get('processing_ms')} ms, {state.get('total_tokens')} tokens")
            print()
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
