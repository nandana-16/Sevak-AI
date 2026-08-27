"""Agent 4 — Reporting: maps a visit into HMIS/RCH report fields (FR-05).

Deterministic by design (not an LLM call): government reporting fields must be
derived predictably from structured data, not generated creatively.
"""


def build_hmis_fields(structured: dict, risk_result: dict) -> dict:
    is_maternal = structured.get("pregnancy_stage_months") is not None
    vitals = structured.get("vitals", {})
    return {
        "reporting_category": "maternal" if is_maternal else "general",
        "anc_visit_recorded": is_maternal,
        "high_risk_pregnancy_flagged": is_maternal and risk_result.get("risk_level") == "HIGH",
        "ifa_non_compliance_flagged": structured.get("medication_compliance") == "non_compliant",
        "referral_generated": risk_result.get("risk_level") == "HIGH",
        "bp_recorded": vitals.get("bp_systolic") is not None,
        "social_risk_noted": bool(structured.get("social_risk_factors")),
    }
