"""Agent 1 - Extraction.

Turns free speech or typed notes into structured clinical fields.

Anything the worker entered by hand in the structured form always overrides
the model: a number a human typed into a labelled box is better evidence than
the same number recovered from a noisy transcript.
"""

from __future__ import annotations

import logging
import re

from app.agents import prompts
from app.agents.llm import LLMUsage, get_llm
from app.agents.state import PipelineState

log = logging.getLogger("sevakai.agent.extraction")

VITAL_KEYS = (
    "temperature_c",
    "bp_systolic",
    "bp_diastolic",
    "pulse",
    "weight_kg",
    "hb",
    "spo2",
    "muac_cm",
)

# --- Rule-based fallback patterns ------------------------------------------
# Only used when the LLM is unreachable. Intentionally conservative: it is
# better to extract three certain values than eight guessed ones.

_BP = re.compile(r"\bbp\D{0,12}?(\d{2,3})\s*(?:/|by|bai|per)\s*(\d{2,3})", re.I)
_TEMP_F = re.compile(r"(\d{2,3}(?:\.\d)?)\s*(?:f\b|fahrenheit|degree|bukhar)", re.I)
_TEMP_C = re.compile(r"(\d{2}(?:\.\d)?)\s*(?:c\b|celsius|centigrade)", re.I)
_HB = re.compile(r"\b(?:hb|haemoglobin|hemoglobin)\D{0,10}(\d{1,2}(?:\.\d)?)", re.I)
_WEIGHT = re.compile(r"(\d{1,3}(?:\.\d)?)\s*(?:kg|kilo|kilogram|vazan)", re.I)
_PULSE = re.compile(r"\b(?:pulse|nabz|heart rate)\D{0,10}(\d{2,3})", re.I)
_SPO2 = re.compile(r"\b(?:spo2|oxygen|saturation)\D{0,10}(\d{2,3})", re.I)

SYMPTOM_LEXICON = {
    "fever": ["fever", "bukhar", "tap"],
    "headache": ["headache", "sar dard", "sir dard"],
    "abdominal pain": ["abdominal pain", "pet dard", "pet me dard"],
    "vomiting": ["vomit", "ulti"],
    "diarrhoea": ["diarrhoea", "diarrhea", "dast", "loose motion"],
    "cough": ["cough", "khansi"],
    "breathlessness": ["breathless", "saans", "difficulty breathing"],
    "oedema": ["swelling", "sujan", "oedema", "edema"],
    "weakness": ["weakness", "kamzori"],
    "dizziness": ["dizzy", "chakkar"],
    "bleeding": ["bleeding", "khoon"],
    "blurred vision": ["blurred vision", "dhundla"],
    "jaundice": ["jaundice", "peelia", "piliya"],
    "convulsions": ["convuls", "jhatke", "daura", "fits"],
    "reduced fetal movement": ["bachcha hil nahi", "no movement", "reduced movement"],
    "not feeding": ["not feeding", "doodh nahi", "refusing feed"],
}


def _fallback_extract(text: str) -> dict:
    data: dict = {"symptoms": [], "quotes": [], "unclear": []}
    lowered = text.lower()

    for name, needles in SYMPTOM_LEXICON.items():
        if any(needle in lowered for needle in needles):
            data["symptoms"].append(name)

    if match := _BP.search(text):
        data["bp_systolic"] = int(match.group(1))
        data["bp_diastolic"] = int(match.group(2))
    if match := _TEMP_C.search(text):
        data["temperature_c"] = float(match.group(1))
    elif match := _TEMP_F.search(text):
        fahrenheit = float(match.group(1))
        if 94 <= fahrenheit <= 108:
            data["temperature_c"] = round((fahrenheit - 32) * 5 / 9, 1)
    if match := _HB.search(text):
        data["hb"] = float(match.group(1))
    if match := _WEIGHT.search(text):
        data["weight_kg"] = float(match.group(1))
    if match := _PULSE.search(text):
        data["pulse"] = int(match.group(1))
    if match := _SPO2.search(text):
        value = int(match.group(1))
        if 50 <= value <= 100:
            data["spo2"] = value

    return data


def _coerce_number(value, *, integer: bool = False):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(round(number)) if integer else number


def _sanitise(data: dict) -> dict:
    """Guard against a model returning a plausible-looking impossible vital."""
    bounds = {
        "temperature_c": (30.0, 45.0, False),
        "bp_systolic": (50, 260, True),
        "bp_diastolic": (30, 180, True),
        "pulse": (30, 220, True),
        "weight_kg": (0.5, 200.0, False),
        "hb": (2.0, 20.0, False),
        "spo2": (50, 100, True),
        "muac_cm": (5.0, 30.0, False),
    }
    clean = dict(data)
    for key, (low, high, is_int) in bounds.items():
        value = _coerce_number(clean.get(key), integer=is_int)
        clean[key] = value if value is not None and low <= value <= high else None

    symptoms = clean.get("symptoms") or []
    clean["symptoms"] = [
        str(s).strip().lower() for s in symptoms if isinstance(s, (str, int)) and str(s).strip()
    ][:15]
    for key in ("medications_given", "medications_reported", "counselling_given",
                "quotes", "unclear"):
        value = clean.get(key) or []
        clean[key] = [str(v).strip() for v in value if str(v).strip()][:10]
    return clean


def _describe(state: PipelineState, data: dict) -> str:
    """A compact findings block reused by the risk and action prompts."""
    lines = []
    if data.get("symptoms"):
        lines.append("Symptoms: " + ", ".join(data["symptoms"]))
    vitals = []
    if data.get("temperature_c") is not None:
        vitals.append(f"temperature {data['temperature_c']} C")
    if data.get("bp_systolic"):
        vitals.append(f"BP {data['bp_systolic']}/{data.get('bp_diastolic')}")
    if data.get("pulse"):
        vitals.append(f"pulse {data['pulse']}/min")
    if data.get("hb") is not None:
        vitals.append(f"Hb {data['hb']} g/dL")
    if data.get("spo2"):
        vitals.append(f"SpO2 {data['spo2']}%")
    if data.get("weight_kg") is not None:
        vitals.append(f"weight {data['weight_kg']} kg")
    if data.get("muac_cm") is not None:
        vitals.append(f"MUAC {data['muac_cm']} cm")
    if vitals:
        lines.append("Vitals: " + ", ".join(vitals))
    if data.get("complaints_duration_days"):
        lines.append(f"Duration: {data['complaints_duration_days']} days")
    for key, label in (
        ("pregnancy_notes", "Pregnancy notes"),
        ("infant_notes", "Infant notes"),
        ("immunisation_notes", "Immunisation"),
    ):
        if data.get(key):
            lines.append(f"{label}: {data[key]}")
    if data.get("medications_reported"):
        lines.append("Medicines reported: " + ", ".join(data["medications_reported"]))
    if data.get("unclear"):
        lines.append("Unclear from the recording: " + ", ".join(data["unclear"]))
    if not lines:
        lines.append("No specific findings were extracted.")
    return "\n".join(lines)


def run(state: PipelineState, usage: LLMUsage) -> PipelineState:
    transcript = (state.get("transcript") or "").strip()
    typed = (state.get("typed_notes") or "").strip()
    combined = "\n".join(part for part in (transcript, typed) if part)

    if not combined and not state.get("manual_fields"):
        state["extracted"] = {"symptoms": [], "unclear": ["No input was provided"]}
        state["symptoms"] = []
        state["vitals"] = {}
        state["findings_text"] = "No input was provided for this visit."
        return state

    llm = get_llm()
    result = llm.json(
        "extraction",
        prompts.EXTRACTION_SYSTEM,
        prompts.extraction_user(state.get("patient_context", ""), transcript, typed or None),
        usage,
        max_tokens=2600,
        reasoning_effort="low",
    )

    data = result.data if not result.degraded else _fallback_extract(combined)
    data = _sanitise(data)

    # Structured values the worker typed into the form beat everything above.
    manual = state.get("manual_fields") or {}
    for key in VITAL_KEYS:
        if manual.get(key) is not None:
            data[key] = manual[key]
    if manual.get("symptoms"):
        merged = list(dict.fromkeys([*manual["symptoms"], *data.get("symptoms", [])]))
        data["symptoms"] = merged

    state["extracted"] = data
    state["symptoms"] = data.get("symptoms", [])
    state["vitals"] = {key: data.get(key) for key in VITAL_KEYS}
    state["findings_text"] = _describe(state, data)
    return state
