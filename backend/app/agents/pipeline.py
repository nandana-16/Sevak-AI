"""The LangGraph pipeline wiring the three agents together.

    extraction -> risk -> scheduling

It is a straight sequence rather than anything cleverer because each stage
genuinely needs the previous stage's output: you cannot classify risk from
unstructured speech, and you cannot schedule without a risk level. The graph
earns its place by giving one shared state object, one place to record
degradation, and a natural spot to add branches later (an escalation node, or
a second retrieval pass when confidence is low).
"""

from __future__ import annotations

import logging
import time
from contextvars import ContextVar

from langgraph.graph import END, StateGraph

from app.agents import context as patient_context
from app.agents import extraction, risk, scheduling
from app.agents.llm import LLMUsage
from app.agents.state import PipelineState
from app.models.db import Patient, Visit

log = logging.getLogger("sevakai.pipeline")


# LangGraph validates state against the schema, so the per-run degradation
# recorder cannot ride along inside the state dict. A ContextVar keeps it
# out of the graph while staying correct under concurrent requests.
_current_usage: ContextVar[LLMUsage] = ContextVar("sevakai_llm_usage")


def _build_graph():
    graph = StateGraph(PipelineState)

    def extraction_node(state: PipelineState) -> PipelineState:
        return extraction.run(state, _current_usage.get())

    def risk_node(state: PipelineState) -> PipelineState:
        return risk.run(state, _current_usage.get())

    def scheduling_node(state: PipelineState) -> PipelineState:
        return scheduling.run(state, _current_usage.get())

    graph.add_node("extraction", extraction_node)
    graph.add_node("risk", risk_node)
    graph.add_node("scheduling", scheduling_node)

    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "risk")
    graph.add_edge("risk", "scheduling")
    graph.add_edge("scheduling", END)

    return graph.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def initial_state(patient: Patient, visit: Visit) -> PipelineState:
    return PipelineState(
        visit_id=visit.id,
        patient_id=patient.id,
        patient_context=patient_context.build(patient),
        category=patient.category,
        age_years=patient_context.age_years(patient),
        gestation_weeks=patient_context.gestation_weeks(patient),
        topics=patient_context.topics_for(patient),
        transcript=visit.transcript or "",
        typed_notes=visit.typed_notes,
        manual_fields=visit.manual_fields or {},
        language=visit.language,
        degraded_steps=[],
    )


def run(patient: Patient, visit: Visit) -> PipelineState:
    """Run all three agents. Never raises: a failure still produces a state
    the caller can persist and show, with the failure recorded."""
    started = time.time()
    usage = LLMUsage()
    state = initial_state(patient, visit)
    token = _current_usage.set(usage)

    try:
        state = get_graph().invoke(state)
    except Exception as exc:
        log.exception("Pipeline failed for visit %s", visit.id)
        usage.note("pipeline", f"unexpected error: {type(exc).__name__}")
        state.setdefault("risk_level", "unknown")
        state.setdefault(
            "risk_rationale",
            "This visit could not be analysed automatically. Please review it manually.",
        )
        state.setdefault("summary", "Visit recorded but not analysed.")
        state.setdefault("actions", [])
        state.setdefault("follow_up_in_days", 7)
    finally:
        _current_usage.reset(token)

    state["degraded_steps"] = usage.degraded_steps
    state["total_tokens"] = usage.total_tokens
    state["processing_ms"] = int((time.time() - started) * 1000)
    return state
