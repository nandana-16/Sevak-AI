"""Shared state passed between the agents in the LangGraph pipeline."""

from __future__ import annotations

from typing import Any, TypedDict

from app.models.db import PatientCategory


class PipelineState(TypedDict, total=False):
    # --- Inputs -------------------------------------------------------------
    visit_id: str
    patient_id: str
    patient_context: str
    category: PatientCategory
    age_years: float | None
    gestation_weeks: int | None
    topics: list[str]
    transcript: str
    typed_notes: str | None
    manual_fields: dict[str, Any]
    language: str

    # --- Agent 1: extraction ------------------------------------------------
    extracted: dict[str, Any]
    symptoms: list[str]
    vitals: dict[str, Any]
    findings_text: str

    # --- Agent 2: risk ------------------------------------------------------
    citations: list[dict[str, Any]]
    risk_level: str
    risk_rationale: str
    risk_confidence: float
    danger_signs: list[str]
    family_message: str
    rule_level: str

    # --- Agent 3: actions and scheduling ------------------------------------
    actions: list[dict[str, Any]]
    follow_up_in_days: int
    follow_up_reason: str
    summary: str
    refer_to_facility: bool
    referral_reason: str | None

    # --- Bookkeeping --------------------------------------------------------
    degraded_steps: list[str]
    processing_ms: int
    total_tokens: int
