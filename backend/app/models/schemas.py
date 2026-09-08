"""Pydantic request and response models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.db import (
    InputMode,
    PatientCategory,
    RiskLevel,
    Role,
    ScheduleStatus,
    VisitStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth -------------------------------------------------------------------

class LoginRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=15)
    pin: str = Field(min_length=4, max_length=6)


class WorkerOut(ORMModel):
    id: str
    name: str
    phone: str
    role: Role
    village: str | None = None
    block: str | None = None
    district: str | None = None
    preferred_language: str = "hi"


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    worker: WorkerOut


# --- Patients ---------------------------------------------------------------

class PatientSummary(ORMModel):
    """The roster list row. Deliberately light - a worker scrolling forty
    patients on a slow phone should not be downloading full histories."""

    id: str
    name: str
    age_label: str = ""
    gender: str
    category: PatientCategory
    village: str | None = None
    current_risk: RiskLevel
    last_visit_at: datetime | None = None
    last_visit_summary: str | None = None
    next_visit_due: date | None = None
    aadhaar_verified: bool = False


class ConditionOut(ORMModel):
    id: str
    name: str
    diagnosed_on: date | None = None
    ongoing: bool
    notes: str | None = None


class VaccinationOut(ORMModel):
    id: str
    vaccine: str
    dose_label: str | None = None
    due_date: date | None = None
    given_date: date | None = None
    given: bool
    overdue: bool = False


class PregnancyOut(ORMModel):
    lmp: date | None = None
    edd: date | None = None
    gravida: int | None = None
    para: int | None = None
    anc_visits_completed: int = 0
    tt_doses: int = 0
    ifa_tablets_given: int = 0
    last_hb: float | None = None
    last_bp_systolic: int | None = None
    last_bp_diastolic: int | None = None
    last_weight_kg: float | None = None
    high_risk_factors: list[str] = []
    planned_delivery_place: str | None = None
    gestation_weeks: int | None = None


class InfantOut(ORMModel):
    birth_weight_kg: float | None = None
    gestation_weeks: int | None = None
    delivery_type: str | None = None
    place_of_birth: str | None = None
    exclusive_breastfeeding: bool | None = None
    last_weight_kg: float | None = None
    last_muac_cm: float | None = None


class PatientDetail(PatientSummary):
    dob: date | None = None
    blood_group: str | None = None
    phone: str | None = None
    address: str | None = None
    guardian_name: str | None = None
    household_id: str | None = None
    block: str | None = None
    district: str | None = None
    aadhaar_masked: str = "Not linked"
    conditions: list[ConditionOut] = []
    vaccinations: list[VaccinationOut] = []
    pregnancy: PregnancyOut | None = None
    infant: InfantOut | None = None
    recent_visits: list["VisitSummary"] = []


class AadhaarCheckRequest(BaseModel):
    aadhaar: str


class AadhaarCheckResponse(BaseModel):
    valid: bool
    reason: str
    last4: str | None = None
    already_registered: bool = False
    method: str = "offline_verhoeff"


class PatientCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    gender: str
    dob: date | None = None
    age_years_approx: int | None = None
    blood_group: str | None = None
    phone: str | None = None
    category: PatientCategory = PatientCategory.adult
    village: str | None = None
    address: str | None = None
    guardian_name: str | None = None
    household_id: str | None = None

    aadhaar: str | None = None
    # Recorded explicitly. Registration is refused without it when an Aadhaar
    # number is supplied.
    aadhaar_consent_given: bool = False

    conditions: list[str] = []
    # Pregnancy fields, used when category is `pregnant`.
    lmp: date | None = None
    gravida: int | None = None
    para: int | None = None
    # Infant fields, used when category is `infant`.
    birth_weight_kg: float | None = None
    gestation_weeks: int | None = None
    mother_name: str | None = None


# --- Visits -----------------------------------------------------------------

class VisitCreate(BaseModel):
    """A visit submitted from the phone.

    `client_uuid` is generated on the device before anything is sent, so a
    visit queued offline and retried on a flaky connection lands exactly once.
    """

    client_uuid: str = Field(min_length=8, max_length=36)
    patient_id: str
    transcript: str | None = None
    typed_notes: str | None = None
    manual_fields: dict[str, Any] = {}
    input_mode: InputMode = InputMode.voice
    language: str = "hi"
    visited_at: datetime | None = None


class CitationOut(BaseModel):
    text: str
    title: str
    page: int
    url: str
    score: float


class ActionOut(BaseModel):
    action: str
    urgency: str


class VisitSummary(ORMModel):
    id: str
    visited_at: datetime
    risk_level: RiskLevel
    summary: str | None = None
    status: VisitStatus
    input_mode: InputMode


class VisitDetail(VisitSummary):
    client_uuid: str
    patient_id: str
    worker_id: str
    language: str
    transcript: str | None = None
    typed_notes: str | None = None
    symptoms: list[str] = []
    temperature_c: float | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    pulse: int | None = None
    weight_kg: float | None = None
    hb: float | None = None
    spo2: int | None = None
    risk_rationale: str | None = None
    risk_confidence: float | None = None
    danger_signs: list[str] = []
    guideline_citations: list[CitationOut] = []
    recommended_actions: list[ActionOut] = []
    next_visit_due: date | None = None
    refer_to_facility: bool = False
    # Steps that fell back to rules because the model was unavailable. Shown
    # in the app so canned output is never mistaken for live reasoning.
    degraded_steps: list[str] = []
    processing_ms: int | None = None
    error_message: str | None = None


# --- Schedule ---------------------------------------------------------------

class ScheduledVisitOut(ORMModel):
    id: str
    patient_id: str
    patient_name: str = ""
    patient_village: str | None = None
    due_date: date
    reason: str
    priority: RiskLevel
    status: ScheduleStatus
    overdue: bool = False


class CompleteScheduleRequest(BaseModel):
    visit_id: str | None = None


# --- Escalations ------------------------------------------------------------

class EscalationOut(ORMModel):
    id: str
    patient_id: str
    patient_name: str = ""
    visit_id: str
    worker_id: str
    worker_name: str = ""
    raised_at: datetime
    reason: str
    acknowledged_at: datetime | None = None
    resolved: bool = False
    # Carries either a supervisor's sign-off note, or an automatic note that a
    # later visit found the patient improved. Without this the annotation is
    # written to the database and never seen by anyone.
    resolution_note: str | None = None


# --- Misc -------------------------------------------------------------------

class GuidelineSourceOut(BaseModel):
    filename: str
    title: str
    publisher: str
    year: str
    url: str
    chunks: int


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_ready: bool
    stt_provider: str
    guideline_chunks: int
    patients: int


PatientDetail.model_rebuild()
