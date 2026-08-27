"""Agent 2 — Risk Classification via NHM-protocol RAG (FR-03)."""
import json

from app.agents.llm_client import get_llm_client
from app.agents.prompts import RISK_CLASSIFICATION_SYSTEM_PROMPT
from app.rag.chroma_store import query_protocols


def _build_retrieval_query(structured: dict) -> str:
    terms = []
    vitals = structured.get("vitals", {})
    if vitals.get("bp_systolic"):
        terms.append(f"blood pressure {vitals['bp_systolic']}/{vitals.get('bp_diastolic')} hypertension pregnancy")
    if vitals.get("temperature_f"):
        terms.append(f"fever {vitals['temperature_f']}")
    if structured.get("medication_compliance") == "non_compliant":
        terms.append("medication non-compliance iron folic acid anemia")
    if structured.get("social_risk_factors"):
        terms.append(" ".join(structured["social_risk_factors"]))
    if structured.get("symptoms_mentioned"):
        terms.append(" ".join(structured["symptoms_mentioned"]))
    if structured.get("pregnancy_stage_months"):
        terms.append(f"pregnancy month {structured['pregnancy_stage_months']} antenatal")
    return " ".join(terms) if terms else "routine antenatal screening normal"


def run_risk_classification(structured: dict) -> dict:
    retrieved = query_protocols(_build_retrieval_query(structured), n_results=4)

    client = get_llm_client()
    payload = json.dumps({**structured, "retrieved_protocols": retrieved})
    result = client.generate_json(RISK_CLASSIFICATION_SYSTEM_PROMPT, payload)

    result.setdefault("risk_level", "LOW")
    result.setdefault("drivers", [])
    result["retrieved_protocols"] = retrieved
    return result
