"""LangGraph StateGraph wiring the 5-agent SevakAI pipeline:
Extraction -> Risk Classification -> Action Generation -> Reporting -> Escalation.
"""
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from app.agents.state import PipelineState
from app.agents.agent1_extraction import run_extraction
from app.agents.agent2_risk import run_risk_classification
from app.agents.agent3_action import run_action_generation
from app.agents.agent4_reporting import build_hmis_fields
from app.agents.agent5_escalation import compute_escalation_deadline


def node_extraction(state: PipelineState) -> dict:
    return {"structured": run_extraction(state["transcript"])}


def node_risk(state: PipelineState) -> dict:
    return {"risk_result": run_risk_classification(state["structured"])}


def node_action(state: PipelineState) -> dict:
    return {"actions_result": run_action_generation(state["structured"], state["risk_result"])}


def node_reporting(state: PipelineState) -> dict:
    return {"hmis_fields": build_hmis_fields(state["structured"], state["risk_result"])}


def node_escalation(state: PipelineState) -> dict:
    deadline = compute_escalation_deadline(state["risk_result"].get("risk_level"), datetime.now(timezone.utc))
    return {"escalation_deadline": deadline.isoformat() if deadline else None}


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("extraction", node_extraction)
    graph.add_node("risk", node_risk)
    graph.add_node("action", node_action)
    graph.add_node("reporting", node_reporting)
    graph.add_node("escalation", node_escalation)

    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "risk")
    graph.add_edge("risk", "action")
    graph.add_edge("action", "reporting")
    graph.add_edge("reporting", "escalation")
    graph.add_edge("escalation", END)
    return graph.compile()


_compiled = None


def get_pipeline():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
