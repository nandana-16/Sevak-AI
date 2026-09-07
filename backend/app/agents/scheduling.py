"""Agent 3 - Actions and scheduling.

Decides what the worker does now, and when they come back. The follow-up
interval the model proposes is clamped to the interval the risk level allows,
so a red case can never be scheduled three weeks out because the model was
feeling relaxed.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from app.agents import prompts
from app.agents.llm import LLMUsage, get_llm
from app.agents.state import PipelineState
from app.models.db import PatientCategory, RiskLevel

log = logging.getLogger("sevakai.agent.scheduling")

# (minimum, default, maximum) days until the next visit, by risk level.
FOLLOW_UP_BOUNDS = {
    RiskLevel.red: (1, 1, 2),
    RiskLevel.yellow: (2, 4, 7),
    RiskLevel.green: (7, 30, 45),
}

URGENCY_ORDER = {"now": 0, "today": 1, "this_week": 2, "routine": 3}


def _routine_interval(state: PipelineState) -> int:
    """The green-path interval for this kind of patient."""
    category = state.get("category")
    if category == PatientCategory.pregnant:
        weeks = state.get("gestation_weeks")
        # ANC: monthly, then fortnightly in the third trimester.
        return 14 if isinstance(weeks, int) and weeks >= 28 else 30
    if category == PatientCategory.infant:
        age = state.get("age_years") or 0
        # HBNC visits are dense in the first six weeks.
        return 3 if age < 0.12 else 14
    if category == PatientCategory.postnatal:
        return 7
    if category == PatientCategory.child:
        return 30
    return 30


def _fallback_actions(state: PipelineState, level: RiskLevel) -> list[dict]:
    if level == RiskLevel.red:
        return [
            {"action": "Accompany the patient to the nearest health facility today",
             "urgency": "now"},
            {"action": "Arrange transport and inform the family what to carry",
             "urgency": "now"},
            {"action": "Record the referral and check on the patient this evening",
             "urgency": "today"},
        ]
    if level == RiskLevel.yellow:
        return [
            {"action": "Advise a doctor or ANM consultation within the next few days",
             "urgency": "this_week"},
            {"action": "Explain the warning signs that mean going to the facility at once",
             "urgency": "today"},
            {"action": "Re-check the abnormal readings at the follow-up visit",
             "urgency": "this_week"},
        ]
    return [
        {"action": "Continue routine counselling on diet, rest and hygiene", "urgency": "routine"},
        {"action": "Confirm the next scheduled visit with the family", "urgency": "routine"},
    ]


def _clamp_follow_up(level: RiskLevel, proposed, state: PipelineState) -> int:
    low, default, high = FOLLOW_UP_BOUNDS.get(level, (7, 30, 45))
    if level == RiskLevel.green:
        default = _routine_interval(state)
        high = max(high, default)
    try:
        days = int(proposed)
    except (TypeError, ValueError):
        return default
    return max(low, min(days, high))


def _fallback_summary(state: PipelineState, level: RiskLevel) -> str:
    symptoms = state.get("symptoms") or []
    lead = ", ".join(symptoms[:3]) if symptoms else "no new complaints"
    label = {
        RiskLevel.red: "referred urgently",
        RiskLevel.yellow: "needs doctor review",
        RiskLevel.green: "stable",
    }.get(level, "reviewed")
    return f"Visit noted {lead}; {label}."


def run(state: PipelineState, usage: LLMUsage) -> PipelineState:
    try:
        level = RiskLevel(state.get("risk_level", "green"))
    except ValueError:
        level = RiskLevel.green

    llm = get_llm()
    result = llm.json(
        "scheduling",
        prompts.ACTION_SYSTEM,
        prompts.action_user(
            state.get("patient_context", ""),
            state.get("findings_text", ""),
            level.value,
            state.get("risk_rationale", ""),
        ),
        usage,
        max_tokens=2400,
        reasoning_effort="low",
    )

    if result.degraded:
        actions = _fallback_actions(state, level)
        follow_up = _clamp_follow_up(level, None, state)
        follow_up_reason = state.get("risk_rationale") or "Routine follow-up"
        summary = _fallback_summary(state, level)
        refer = level == RiskLevel.red
        referral_reason = state.get("risk_rationale") if refer else None
    else:
        data = result.data
        actions = []
        for item in data.get("actions") or []:
            if isinstance(item, dict) and str(item.get("action", "")).strip():
                urgency = str(item.get("urgency", "routine")).lower()
                actions.append(
                    {
                        "action": str(item["action"]).strip(),
                        "urgency": urgency if urgency in URGENCY_ORDER else "routine",
                    }
                )
            elif isinstance(item, str) and item.strip():
                actions.append({"action": item.strip(), "urgency": "routine"})
        actions = actions[:5] or _fallback_actions(state, level)
        actions.sort(key=lambda a: URGENCY_ORDER.get(a["urgency"], 3))

        follow_up = _clamp_follow_up(level, data.get("follow_up_in_days"), state)
        follow_up_reason = (
            str(data.get("follow_up_reason") or "").strip() or "Scheduled follow-up"
        )
        summary = str(data.get("summary") or "").strip() or _fallback_summary(state, level)
        refer = bool(data.get("refer_to_facility")) or level == RiskLevel.red
        referral_reason = str(data.get("referral_reason") or "").strip() or None
        if refer and not referral_reason:
            referral_reason = state.get("risk_rationale")

    # A red visit always carries a referral, whatever the model returned.
    if level == RiskLevel.red:
        refer = True

    state["actions"] = actions
    state["follow_up_in_days"] = follow_up
    state["follow_up_reason"] = follow_up_reason
    state["summary"] = summary[:400]
    state["refer_to_facility"] = refer
    state["referral_reason"] = referral_reason
    return state


def follow_up_date(days: int, from_date: date | None = None) -> date:
    return (from_date or date.today()) + timedelta(days=days)
