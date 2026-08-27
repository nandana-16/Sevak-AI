"""Pluggable LLM client used by every agent node.

Swap providers purely via .env (LLM_PROVIDER=mock|gemini) — no code changes needed.
The mock provider does lightweight rule-based extraction so the full pipeline is
demonstrable end-to-end with zero API keys and zero cost.
"""
import json
import logging
import re
import time
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger("sevakai.llm")


class LLMClient(ABC):
    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Return a parsed JSON dict from the model, following the system prompt's schema."""
        raise NotImplementedError


class GeminiClient(LLMClient):
    def __init__(self):
        from google import genai

        self._genai = genai
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        response = self._client.models.generate_content(
            model=settings.gemini_model,
            contents=f"{system_prompt}\n\n{user_prompt}",
            config={"response_mime_type": "application/json"},
        )
        text = response.text or "{}"
        return json.loads(text)


class ResilientLLMClient(LLMClient):
    """Wraps a primary provider with one short retry, then falls back to the rule-based
    mock rather than raising — so a rate-limited/transient API failure degrades the
    quality of one step instead of crashing the whole visit. Mirrors the SRS's own
    documented fallback philosophy (Section 9.1 / Risk Register) for external API
    outages during a live demo."""

    def __init__(self, primary: LLMClient, fallback: LLMClient, retry_delay_seconds: float = 3.0):
        self._primary = primary
        self._fallback = fallback
        self._retry_delay = retry_delay_seconds

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        for attempt in range(2):
            try:
                return self._primary.generate_json(system_prompt, user_prompt)
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"LLM call failed (attempt 1/2), retrying in {self._retry_delay}s: {e}")
                    time.sleep(self._retry_delay)
                else:
                    logger.warning(f"LLM call failed twice, falling back to mock for this step: {e}")
        return self._fallback.generate_json(system_prompt, user_prompt)


class MockLLMClient(LLMClient):
    """Rule-based stand-in so the pipeline is fully runnable with no LLM key.

    Each agent module passes a `task` hint via the system prompt's first line
    (e.g. "TASK: extraction") so this mock can route to a small heuristic per task,
    instead of trying to be one generic fake model.
    """

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        task = system_prompt.split("\n", 1)[0].replace("TASK:", "").strip()
        handler = getattr(self, f"_handle_{task}", None)
        if handler is None:
            return {}
        return handler(user_prompt)

    # ---- heuristic extraction from a Hindi/English mixed transcript ----
    def _handle_extraction(self, transcript: str) -> dict:
        t = transcript.lower()

        age_match = re.search(r"(\d{1,3})\s*(saal|years?|yrs?|साल)", t)
        age = int(age_match.group(1)) if age_match else None

        bp_match = re.search(r"(\d{2,3})\s*(?:/|over|se)\s*(\d{2,3})", t)
        bp_systolic, bp_diastolic = (int(bp_match.group(1)), int(bp_match.group(2))) if bp_match else (None, None)

        months_match = re.search(r"(\d{1,2})\s*(mahine|month)", t)
        pregnancy_months = int(months_match.group(1)) if months_match else None

        temp_match = re.search(r"(\d{2,3}(?:\.\d)?)\s*(?:f|fahrenheit|degree)", t)
        temperature = float(temp_match.group(1)) if temp_match else None

        weight_match = re.search(r"(\d{2,3}(?:\.\d)?)\s*(?:kg|kilo)", t)
        weight = float(weight_match.group(1)) if weight_match else None

        non_compliance_markers = ["nahi li", "nahi le", "skip", "chhod", "not taken", "missed"]
        compliance = "non_compliant" if any(m in t for m in non_compliance_markers) else (
            "compliant" if any(k in t for k in ["iron", "tablet", "medicine", "dawai"]) else "unknown"
        )

        social_risk = []
        if any(m in t for m in ["akela", "akeli", "isolat", "alone"]):
            social_risk.append("household_isolation")
        if any(m in t for m in ["pati bahar", "husband away", "spouse absent", "pati nahi"]):
            social_risk.append("absent_spouse")
        if any(m in t for m in ["paisa nahi", "garib", "economic", "financial stress"]):
            social_risk.append("economic_stress")

        name_match = re.search(r"^([a-zA-Zऀ-ॿ]+ [a-zA-Zऀ-ॿ]+)", transcript.strip())
        name = name_match.group(1) if name_match else "Unknown Patient"

        return {
            "patient_name": name,
            "age": age,
            "vitals": {
                "bp_systolic": bp_systolic,
                "bp_diastolic": bp_diastolic,
                "temperature_f": temperature,
                "weight_kg": weight,
            },
            "pregnancy_stage_months": pregnancy_months,
            "medication_compliance": compliance,
            "social_risk_factors": social_risk,
            "symptoms_mentioned": [],
            "confidence": 0.6,
        }

    def _handle_risk_classification(self, payload: str) -> dict:
        data = json.loads(payload)
        vitals = data.get("vitals", {})
        drivers = []
        risk_level = "LOW"

        systolic = vitals.get("bp_systolic")
        diastolic = vitals.get("bp_diastolic")
        if systolic and diastolic and (systolic >= 140 or diastolic >= 90):
            risk_level = "HIGH"
            drivers.append({
                "observation": f"BP {systolic}/{diastolic}",
                "protocol_reference": "NHM-MH-04: Pregnancy-Induced Hypertension Screening",
                "reason": f"Blood pressure {systolic}/{diastolic} meets or exceeds the "
                          f"140/90 mmHg threshold for suspected pre-eclampsia and requires immediate referral.",
            })

        if data.get("medication_compliance") == "non_compliant":
            if risk_level == "LOW":
                risk_level = "MEDIUM"
            drivers.append({
                "observation": "Iron/folic acid non-compliance",
                "protocol_reference": "NHM-MH-02: Anemia Prevention in Pregnancy",
                "reason": "Missed iron-folic acid supplementation increases anemia and "
                          "low-birth-weight risk and should be flagged for counselling.",
            })

        if data.get("social_risk_factors"):
            if risk_level == "LOW":
                risk_level = "MEDIUM"
            drivers.append({
                "observation": ", ".join(data["social_risk_factors"]),
                "protocol_reference": "NHM-SOC-01: Social Determinants Screening",
                "reason": "Social risk factors present (isolation/absent support/economic "
                          "stress) correlate with delayed care-seeking and warrant closer follow-up.",
            })

        if not drivers:
            drivers.append({
                "observation": "No abnormal vitals or compliance issues recorded",
                "protocol_reference": "NHM-MH-01: Routine Antenatal Screening",
                "reason": "All recorded observations are within normal range for this visit.",
            })

        return {"risk_level": risk_level, "drivers": drivers}

    def _handle_action_generation(self, payload: str) -> dict:
        data = json.loads(payload)
        risk_level = data.get("risk_level", "LOW")
        patient = data.get("patient_name", "the patient")
        actions = []
        if risk_level == "HIGH":
            actions.append({
                "type": "referral",
                "content": f"Referral: {patient} presents with high-risk findings "
                            f"({'; '.join(d['observation'] for d in data.get('drivers', []))}). "
                            f"Please review urgently at the nearest PHC.",
            })
        actions.append({
            "type": "whatsapp",
            "content": f"Namaste, this is a summary of {patient}'s health visit today. "
                        f"Risk level: {risk_level}. Please follow the ASHA worker's guidance "
                        f"and attend any scheduled follow-up.",
        })
        due_days = {"HIGH": 2, "MEDIUM": 7, "LOW": 30}[risk_level]
        actions.append({"type": "followup", "content": f"Follow-up visit in {due_days} day(s).", "due_days": due_days})
        return {"actions": actions}


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return ResilientLLMClient(primary=GeminiClient(), fallback=MockLLMClient())
    return MockLLMClient()
