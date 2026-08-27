"""Agent 3 — Action Generation: referral, WhatsApp draft, follow-up task (FR-04)."""
import json

from app.agents.llm_client import get_llm_client
from app.agents.prompts import ACTION_GENERATION_SYSTEM_PROMPT


def run_action_generation(structured: dict, risk_result: dict) -> dict:
    client = get_llm_client()
    payload = json.dumps({
        **structured,
        "risk_level": risk_result.get("risk_level"),
        "drivers": risk_result.get("drivers", []),
    })
    result = client.generate_json(ACTION_GENERATION_SYSTEM_PROMPT, payload)
    result.setdefault("actions", [])
    return result
