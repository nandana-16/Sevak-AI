"""Deterministic clinical rules.

Two jobs:

1. **Fallback.** When the LLM is unreachable, these produce a usable answer so
   a worker in a courtyard is never left with nothing.

2. **Safety floor.** Even when the LLM works, these run and can only escalate
   the final risk, never lower it. If a documented NHM danger sign is present,
   the visit comes back red regardless of what the model concluded. A language
   model being persuaded that severe chest indrawing is fine is a failure mode
   worth engineering out rather than hoping about.

Thresholds below are taken from the indexed guidelines - IMNCI danger signs,
PMSMA high-risk conditions, and Anemia Mukt Bharat cut-offs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models.db import PatientCategory, RiskLevel

RISK_ORDER = {RiskLevel.unknown: 0, RiskLevel.green: 1, RiskLevel.yellow: 2, RiskLevel.red: 3}


def escalate(current: RiskLevel, candidate: RiskLevel) -> RiskLevel:
    """Return whichever of the two is more severe."""
    return candidate if RISK_ORDER[candidate] > RISK_ORDER[current] else current


@dataclass
class RuleFinding:
    level: RiskLevel
    reason: str
    source: str


@dataclass
class RuleResult:
    level: RiskLevel = RiskLevel.green
    findings: list[RuleFinding] = field(default_factory=list)

    @property
    def danger_signs(self) -> list[str]:
        return [f.reason for f in self.findings if f.level == RiskLevel.red]

    def add(self, level: RiskLevel, reason: str, source: str) -> None:
        self.findings.append(RuleFinding(level, reason, source))
        self.level = escalate(self.level, level)


# ---------------------------------------------------------------------------
# Danger-sign vocabulary, in English plus the Hindi/Hinglish a worker actually
# says. Matching is on the transcript as well as the extracted symptom list,
# because extraction can miss a phrase that the raw speech contains.
# ---------------------------------------------------------------------------

GENERAL_DANGER_SIGNS: dict[str, list[str]] = {
    "convulsions / fits": ["convuls", "seizure", "fits", "jhatke", "mirgi", "daura"],
    "unconscious or unresponsive": ["unconscious", "unrespons", "behosh", "besudh"],
    "unable to drink or feed": ["unable to drink", "not able to drink", "cannot feed",
                                "not feeding", "refus", "doodh nahi", "pi nahi"],
    "vomiting everything": ["vomit everything", "vomits everything", "ulti ho rahi", "sab ulti"],
    "lethargic or very drowsy": ["lethargic", "very drowsy", "sust", "susti", "nidra"],
}

MATERNAL_DANGER_SIGNS: dict[str, list[str]] = {
    "vaginal bleeding in pregnancy": ["bleeding", "blood loss", "khoon", "rakt srav", "bleed"],
    "severe headache with blurred vision": ["blurred vision", "blurring", "dhundla",
                                            "dikhai nahi", "vision problem"],
    "convulsions (possible eclampsia)": ["convuls", "fits", "jhatke", "daura"],
    "reduced or absent fetal movement": ["no movement", "not moving", "reduced movement",
                                         "bachcha hil nahi", "harkat nahi"],
    "severe abdominal pain": ["severe abdominal pain", "tez pet dard", "pet me tez dard"],
    "leaking of fluid": ["water broke", "leaking", "pani nikal"],
}

NEWBORN_DANGER_SIGNS: dict[str, list[str]] = {
    "severe chest indrawing": ["chest indrawing", "chest in-drawing", "seene", "pasli chal"],
    "grunting or nasal flaring": ["grunting", "nasal flaring"],
    "cold to touch / hypothermia": ["cold to touch", "hypotherm", "thanda", "sard"],
    "umbilical redness or pus": ["umbilic", "pus", "naabhi", "nabhi", "mavaad"],
    "yellow palms and soles (severe jaundice)": ["jaundice", "yellow palms", "peelia", "piliya"],
    "no movement or moves only when stimulated": ["not moving", "no movement", "hil nahi"],
}


def _matches(haystack: str, needles: list[str]) -> bool:
    return any(needle in haystack for needle in needles)


def _searchable(transcript: str | None, symptoms: list | None, notes: str | None) -> str:
    parts = [transcript or "", notes or ""]
    parts.extend(str(s) for s in (symptoms or []))
    return " ".join(parts).lower()


def evaluate(
    *,
    category: PatientCategory,
    age_years: float | None,
    transcript: str | None = None,
    typed_notes: str | None = None,
    symptoms: list | None = None,
    temperature_c: float | None = None,
    bp_systolic: int | None = None,
    bp_diastolic: int | None = None,
    pulse: int | None = None,
    hb: float | None = None,
    spo2: int | None = None,
    muac_cm: float | None = None,
) -> RuleResult:
    result = RuleResult()
    text = _searchable(transcript, symptoms, typed_notes)

    is_infant = category in (PatientCategory.infant,) or (age_years is not None and age_years < 1)
    is_child = category == PatientCategory.child or (age_years is not None and age_years < 5)
    is_maternal = category in (PatientCategory.pregnant, PatientCategory.postnatal)

    # --- General danger signs (IMNCI) --------------------------------------
    for sign, needles in GENERAL_DANGER_SIGNS.items():
        if _matches(text, needles):
            result.add(RiskLevel.red, sign, "IMNCI general danger signs")

    if is_maternal:
        for sign, needles in MATERNAL_DANGER_SIGNS.items():
            if _matches(text, needles):
                result.add(RiskLevel.red, sign, "PMSMA maternal warning signs")

    if is_infant:
        for sign, needles in NEWBORN_DANGER_SIGNS.items():
            if _matches(text, needles):
                result.add(RiskLevel.red, sign, "HBNC / IMNCI newborn danger signs")

    # --- Blood pressure -----------------------------------------------------
    if bp_systolic and bp_diastolic:
        if is_maternal:
            # PMSMA: >=160/110 is severe hypertension; >=140/90 is hypertension.
            if bp_systolic >= 160 or bp_diastolic >= 110:
                result.add(
                    RiskLevel.red,
                    f"Severe hypertension in pregnancy ({bp_systolic}/{bp_diastolic})",
                    "PMSMA high-risk conditions",
                )
            elif bp_systolic >= 140 or bp_diastolic >= 90:
                result.add(
                    RiskLevel.yellow,
                    f"Raised blood pressure in pregnancy ({bp_systolic}/{bp_diastolic})",
                    "PMSMA high-risk conditions",
                )
        else:
            if bp_systolic >= 180 or bp_diastolic >= 120:
                result.add(
                    RiskLevel.red,
                    f"Hypertensive crisis ({bp_systolic}/{bp_diastolic})",
                    "Standard treatment guidelines",
                )
            elif bp_systolic >= 140 or bp_diastolic >= 90:
                result.add(
                    RiskLevel.yellow,
                    f"Raised blood pressure ({bp_systolic}/{bp_diastolic})",
                    "Standard treatment guidelines",
                )

    # --- Haemoglobin (Anemia Mukt Bharat) -----------------------------------
    if hb is not None:
        if hb < 7:
            result.add(
                RiskLevel.red,
                f"Severe anaemia (Hb {hb} g/dL) - needs facility referral",
                "Anemia Mukt Bharat",
            )
        elif hb < 11 and (is_maternal or is_child):
            result.add(
                RiskLevel.yellow,
                f"Anaemia (Hb {hb} g/dL)",
                "Anemia Mukt Bharat",
            )
        elif hb < 12:
            result.add(RiskLevel.yellow, f"Low haemoglobin (Hb {hb} g/dL)", "Anemia Mukt Bharat")

    # --- Temperature --------------------------------------------------------
    if temperature_c is not None:
        if is_infant and (temperature_c >= 37.5 or temperature_c < 35.5):
            result.add(
                RiskLevel.red,
                f"Abnormal temperature in young infant ({temperature_c} C)",
                "IMNCI young infant",
            )
        elif temperature_c >= 39.0:
            result.add(RiskLevel.red, f"High fever ({temperature_c} C)", "IMNCI fever")
        elif temperature_c >= 38.0:
            result.add(RiskLevel.yellow, f"Fever ({temperature_c} C)", "IMNCI fever")

    # --- Oxygen saturation --------------------------------------------------
    if spo2 is not None:
        if spo2 < 90:
            result.add(RiskLevel.red, f"Low oxygen saturation ({spo2}%)", "Standard treatment guidelines")
        elif spo2 < 94:
            result.add(RiskLevel.yellow, f"Borderline oxygen saturation ({spo2}%)", "Standard treatment guidelines")

    # --- MUAC (severe acute malnutrition) -----------------------------------
    if muac_cm is not None and is_child:
        if muac_cm < 11.5:
            result.add(RiskLevel.red, f"Severe acute malnutrition (MUAC {muac_cm} cm)", "IMNCI malnutrition")
        elif muac_cm < 12.5:
            result.add(RiskLevel.yellow, f"Moderate acute malnutrition (MUAC {muac_cm} cm)", "IMNCI malnutrition")

    # --- Pulse --------------------------------------------------------------
    if pulse is not None and not is_infant:
        if pulse > 120 or pulse < 50:
            result.add(RiskLevel.yellow, f"Abnormal pulse ({pulse}/min)", "Standard treatment guidelines")

    # --- Fever duration mentioned in speech ---------------------------------
    duration = re.search(r"(\d+)\s*(?:din|days?)\b", text)
    mentions_fever = "fever" in text or "bukhar" in text
    if duration and mentions_fever and int(duration.group(1)) >= 7:
        result.add(RiskLevel.yellow, "Fever lasting a week or more", "IMNCI fever")

    return result
