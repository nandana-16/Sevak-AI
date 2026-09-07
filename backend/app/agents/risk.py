"""Agent 2 - Risk classification, grounded in retrieved NHM guidelines.

Order of operations matters here:

1. Retrieve guideline passages for this patient and these findings.
2. Run the deterministic rule check.
3. Ask the model to classify, showing it both the excerpts and the rule flags.
4. Take the MORE severe of the model's answer and the rules.

Step 4 is the point. The model adds nuance the rules cannot, but it can never
talk the system down below a documented danger sign.
"""

from __future__ import annotations

import logging
import re

from app.agents import prompts, rules
from app.agents.llm import LLMUsage, get_llm
from app.agents.state import PipelineState
from app.models.db import PatientCategory, RiskLevel
from app.rag import store

log = logging.getLogger("sevakai.agent.risk")

# Four excerpts is the sweet spot found in testing: five added little to the
# classification but pushed each visit's token cost past what the free tier
# allows in a minute, making back-to-back visits queue.
MAX_EXCERPTS = 4
# Excerpts are trimmed before they reach the prompt. The retrieved chunk is
# still stored in full for the citation the app displays.
EXCERPT_CHARS = 600


def _build_query(state: PipelineState) -> str:
    """Retrieval works better on the clinical findings than on raw speech."""
    parts = [state.get("findings_text", "")]
    category = state.get("category")
    if category == PatientCategory.pregnant:
        parts.append("pregnancy antenatal danger signs high risk")
    elif category in (PatientCategory.infant, PatientCategory.postnatal):
        parts.append("newborn young infant danger signs home based newborn care")
    elif category == PatientCategory.child:
        parts.append("sick child danger signs classification")
    return " ".join(part for part in parts if part)[:900]


def _format_excerpts(citations: list[store.Citation]) -> str:
    if not citations:
        return "(no guideline text could be retrieved)"
    blocks = []
    for index, citation in enumerate(citations, start=1):
        text = citation.text
        if len(text) > EXCERPT_CHARS:
            text = text[:EXCERPT_CHARS].rsplit(" ", 1)[0] + " ..."
        blocks.append(f"[{index}] {citation.title}, page {citation.page}\n{text}")
    return "\n\n".join(blocks)


def _format_rule_flags(result: rules.RuleResult) -> str:
    if not result.findings:
        return "No protocol threshold was crossed by the recorded values."
    return "\n".join(
        f"- [{finding.level.value.upper()}] {finding.reason} (per {finding.source})"
        for finding in result.findings
    )


def _parse_level(value) -> RiskLevel:
    try:
        return RiskLevel(str(value).strip().lower())
    except ValueError:
        return RiskLevel.unknown


def run(state: PipelineState, usage: LLMUsage) -> PipelineState:
    vitals = state.get("vitals") or {}

    # 1. Retrieve.
    citations = store.search(
        _build_query(state), k=MAX_EXCERPTS, topics=state.get("topics") or None
    )
    state["citations"] = [c.to_dict() for c in citations]
    if not citations:
        usage.note("risk", "no guideline corpus indexed")

    # 2. Deterministic rules.
    rule_result = rules.evaluate(
        category=state.get("category", PatientCategory.adult),
        age_years=state.get("age_years"),
        transcript=state.get("transcript"),
        typed_notes=state.get("typed_notes"),
        symptoms=state.get("symptoms"),
        temperature_c=vitals.get("temperature_c"),
        bp_systolic=vitals.get("bp_systolic"),
        bp_diastolic=vitals.get("bp_diastolic"),
        pulse=vitals.get("pulse"),
        hb=vitals.get("hb"),
        spo2=vitals.get("spo2"),
        muac_cm=vitals.get("muac_cm"),
    )
    state["rule_level"] = rule_result.level.value

    # 3. Ask the model.
    llm = get_llm()
    result = llm.json(
        "risk",
        prompts.RISK_SYSTEM,
        prompts.risk_user(
            state.get("patient_context", ""),
            state.get("findings_text", ""),
            _format_excerpts(citations),
            _format_rule_flags(rule_result),
        ),
        usage,
        max_tokens=3200,
        # The clinically load-bearing step: worth the extra seconds.
        reasoning_effort="medium",
    )

    if result.degraded:
        level = rule_result.level
        rationale = _rule_rationale(rule_result)
        confidence = 0.5
        danger_signs = rule_result.danger_signs
        family_message = _family_message(level)
        cited_indices: list[int] = []
    else:
        data = result.data
        level = _parse_level(data.get("risk_level"))
        if level == RiskLevel.unknown:
            level = rule_result.level
        rationale = str(data.get("rationale") or "").strip() or _rule_rationale(rule_result)
        try:
            confidence = min(max(float(data.get("confidence", 0.7)), 0.0), 1.0)
        except (TypeError, ValueError):
            confidence = 0.7
        danger_signs = [
            str(s).strip() for s in (data.get("danger_signs") or []) if str(s).strip()
        ]
        family_message = str(data.get("what_to_tell_the_family") or "").strip()
        cited_indices = [
            i for i in (data.get("cited_excerpts") or []) if isinstance(i, int)
        ]

    # 4. Safety floor: rules can raise the level, never lower it.
    final = rules.escalate(level, rule_result.level)
    if final != level:
        log.info(
            "Rule floor raised risk from %s to %s for visit %s",
            level.value, final.value, state.get("visit_id"),
        )
        extra = "; ".join(rule_result.danger_signs) or rule_result.findings[0].reason
        rationale = (
            f"{rationale} Protocol check also flagged: {extra}."
        ).strip()
    level = final

    # Merge rule danger signs in, without duplicating what the model said.
    danger_signs = _dedupe_signs(danger_signs, rule_result.danger_signs)

    # Keep only the excerpts the model actually cited, when it named any.
    if cited_indices:
        kept = [
            state["citations"][i - 1]
            for i in cited_indices
            if 1 <= i <= len(state["citations"])
        ]
        if kept:
            state["citations"] = kept

    state["risk_level"] = level.value
    state["risk_rationale"] = rationale
    state["risk_confidence"] = confidence
    state["danger_signs"] = danger_signs
    state["family_message"] = family_message or _family_message(level)
    return state


_STOPWORDS = {
    "the", "a", "an", "of", "or", "and", "to", "in", "is", "with", "for",
    "needs", "need", "sign", "signs", "severe", "very",
}


def _sign_key(text: str) -> frozenset[str]:
    """Loose fingerprint of a danger sign, for spotting near-duplicates.

    The model and the rules describe the same finding differently - "unable to
    feed" against "unable to drink or feed", "Severe anemia (Hb < 7 g/dL)"
    against "Severe anaemia (Hb 6.2 g/dL)". Showing both to a worker is noise,
    so compare on meaningful words with spellings and numbers normalised away.
    """
    lowered = re.sub(r"[^a-z ]+", " ", text.lower())
    lowered = lowered.replace("anaemia", "anemia").replace("oedema", "edema")
    words = {w for w in lowered.split() if len(w) > 2 and w not in _STOPWORDS}
    return frozenset(words)


def _dedupe_signs(primary: list[str], extra: list[str]) -> list[str]:
    kept: list[str] = []
    seen: list[frozenset[str]] = []
    for sign in [*primary, *extra]:
        key = _sign_key(sign)
        if not key:
            continue
        # Treat as a duplicate when one description's words are largely
        # contained in another's.
        if any(
            len(key & previous) >= min(len(key), len(previous)) * 0.6
            for previous in seen
        ):
            continue
        seen.append(key)
        kept.append(sign)
    return kept


def _rule_rationale(result: rules.RuleResult) -> str:
    if not result.findings:
        return (
            "No danger signs or abnormal readings were found in what was recorded. "
            "Continue the routine schedule."
        )
    reasons = "; ".join(f.reason for f in result.findings[:4])
    if result.level == RiskLevel.red:
        return f"Danger signs found that need care today: {reasons}."
    if result.level == RiskLevel.yellow:
        return f"Findings that need a doctor's review soon: {reasons}."
    return f"Minor findings noted: {reasons}."


def _family_message(level: RiskLevel) -> str:
    return {
        RiskLevel.red: (
            "Take the patient to the health facility today. Do not wait for "
            "the symptoms to settle on their own."
        ),
        RiskLevel.yellow: (
            "Please see the doctor or ANM within the next few days, and call "
            "if anything gets worse."
        ),
        RiskLevel.green: (
            "Everything looks fine for now. Keep up the usual care and the "
            "next visit is scheduled as normal."
        ),
    }.get(level, "Follow the usual advice and contact the ASHA if anything changes.")
