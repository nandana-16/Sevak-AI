"""SQLAlchemy models.

Design notes:
* Patient access is scoped by Patient.assigned_worker_id. Every query that
  returns patient data goes through app.core.scoping rather than raw filters
  in routers, so the roster rule cannot be forgotten in one endpoint.
* Aadhaar numbers are never stored. Only a salted hash (for duplicate
  detection) and the last four digits (for human confirmation).
* Visit.client_uuid is generated on the phone, so a visit queued offline and
  retried three times still lands once.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Role(str, enum.Enum):
    asha = "asha"          # field worker
    anm = "anm"            # auxiliary nurse midwife, supervises a few ASHAs
    bmo = "bmo"            # block medical officer, oversees the whole block
    admin = "admin"


class RiskLevel(str, enum.Enum):
    red = "red"            # refer to a facility now
    yellow = "yellow"      # doctor consult soon
    green = "green"        # routine
    unknown = "unknown"    # not yet classified


class PatientCategory(str, enum.Enum):
    infant = "infant"
    child = "child"
    pregnant = "pregnant"
    postnatal = "postnatal"
    adult = "adult"
    elderly = "elderly"


class VisitStatus(str, enum.Enum):
    queued = "queued"          # accepted, waiting for the pipeline
    processing = "processing"
    complete = "complete"
    failed = "failed"


class InputMode(str, enum.Enum):
    voice = "voice"
    typed = "typed"
    voice_offline = "voice_offline"   # audio captured with no network


class ScheduleStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    missed = "missed"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    pin_hash: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.asha)

    # Geography, used for the region filter on the roster.
    village: Mapped[str | None] = mapped_column(String(120))
    block: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))

    supervisor_id: Mapped[str | None] = mapped_column(ForeignKey("workers.id"))
    preferred_language: Mapped[str] = mapped_column(String(10), default="hi")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    patients: Mapped[list["Patient"]] = relationship(back_populates="assigned_worker")
    supervisor: Mapped["Worker | None"] = relationship(remote_side=[id])


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120), index=True)
    dob: Mapped[date | None] = mapped_column(Date)
    # Kept for the many rural cases where only an approximate age is known.
    age_years_approx: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(10))            # female | male | other
    blood_group: Mapped[str | None] = mapped_column(String(5))
    phone: Mapped[str | None] = mapped_column(String(15))

    category: Mapped[PatientCategory] = mapped_column(
        Enum(PatientCategory), default=PatientCategory.adult
    )

    village: Mapped[str | None] = mapped_column(String(120), index=True)
    block: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)

    household_id: Mapped[str | None] = mapped_column(String(40), index=True)
    guardian_name: Mapped[str | None] = mapped_column(String(120))

    # --- Aadhaar: hash + last4 only, never the number itself ---------------
    aadhaar_hash: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4))
    aadhaar_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    aadhaar_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    aadhaar_consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    aadhaar_verification_method: Mapped[str | None] = mapped_column(String(30))

    assigned_worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    assigned_worker: Mapped["Worker"] = relationship(back_populates="patients")

    current_risk: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.unknown)
    last_visit_at: Mapped[datetime | None] = mapped_column(DateTime)
    # One-line recap shown at the top of the profile so the worker knows what
    # happened last time before they knock on the door.
    last_visit_summary: Mapped[str | None] = mapped_column(Text)

    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    visits: Mapped[list["Visit"]] = relationship(
        back_populates="patient", order_by="Visit.visited_at.desc()"
    )
    conditions: Mapped[list["MedicalCondition"]] = relationship(back_populates="patient")
    vaccinations: Mapped[list["Vaccination"]] = relationship(back_populates="patient")
    pregnancy: Mapped["PregnancyRecord | None"] = relationship(
        back_populates="patient", uselist=False
    )
    infant_record: Mapped["InfantRecord | None"] = relationship(
        back_populates="patient", uselist=False
    )


# ---------------------------------------------------------------------------
# Clinical history
# ---------------------------------------------------------------------------

class MedicalCondition(Base):
    """Past and ongoing disease history."""

    __tablename__ = "medical_conditions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    diagnosed_on: Mapped[date | None] = mapped_column(Date)
    ongoing: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    # Set when an agent inferred this from speech rather than a worker typing it.
    source_visit_id: Mapped[str | None] = mapped_column(String(36))

    patient: Mapped["Patient"] = relationship(back_populates="conditions")


class Vaccination(Base):
    """Immunisation schedule. Rows are pre-created from the national schedule
    at registration for infants, then marked as given."""

    __tablename__ = "vaccinations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    vaccine: Mapped[str] = mapped_column(String(80))
    dose_label: Mapped[str | None] = mapped_column(String(40))   # e.g. "Pentavalent-2"
    due_date: Mapped[date | None] = mapped_column(Date)
    given_date: Mapped[date | None] = mapped_column(Date)
    given: Mapped[bool] = mapped_column(Boolean, default=False)
    batch_no: Mapped[str | None] = mapped_column(String(40))

    patient: Mapped["Patient"] = relationship(back_populates="vaccinations")


class PregnancyRecord(Base):
    __tablename__ = "pregnancy_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), unique=True, index=True)

    lmp: Mapped[date | None] = mapped_column(Date)          # last menstrual period
    edd: Mapped[date | None] = mapped_column(Date)          # expected delivery date
    gravida: Mapped[int | None] = mapped_column(Integer)    # total pregnancies
    para: Mapped[int | None] = mapped_column(Integer)       # prior births
    anc_visits_completed: Mapped[int] = mapped_column(Integer, default=0)
    tt_doses: Mapped[int] = mapped_column(Integer, default=0)
    ifa_tablets_given: Mapped[int] = mapped_column(Integer, default=0)

    last_hb: Mapped[float | None] = mapped_column(Float)
    last_bp_systolic: Mapped[int | None] = mapped_column(Integer)
    last_bp_diastolic: Mapped[int | None] = mapped_column(Integer)
    last_weight_kg: Mapped[float | None] = mapped_column(Float)

    high_risk_factors: Mapped[list | None] = mapped_column(JSON, default=list)
    planned_delivery_place: Mapped[str | None] = mapped_column(String(160))
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    delivery_date: Mapped[date | None] = mapped_column(Date)

    patient: Mapped["Patient"] = relationship(back_populates="pregnancy")


class InfantRecord(Base):
    __tablename__ = "infant_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), unique=True, index=True)

    birth_weight_kg: Mapped[float | None] = mapped_column(Float)
    gestation_weeks: Mapped[int | None] = mapped_column(Integer)
    delivery_type: Mapped[str | None] = mapped_column(String(40))
    place_of_birth: Mapped[str | None] = mapped_column(String(160))
    mother_patient_id: Mapped[str | None] = mapped_column(String(36))

    exclusive_breastfeeding: Mapped[bool | None] = mapped_column(Boolean)
    last_weight_kg: Mapped[float | None] = mapped_column(Float)
    last_muac_cm: Mapped[float | None] = mapped_column(Float)   # mid-upper arm circumference

    patient: Mapped["Patient"] = relationship(back_populates="infant_record")


# ---------------------------------------------------------------------------
# Visits and the agent pipeline
# ---------------------------------------------------------------------------

class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Generated on the device. Makes offline retries idempotent.
    client_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True)

    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)

    visited_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    input_mode: Mapped[InputMode] = mapped_column(Enum(InputMode), default=InputMode.voice)
    language: Mapped[str] = mapped_column(String(10), default="hi")

    # Raw capture. One of these is populated depending on input mode.
    transcript: Mapped[str | None] = mapped_column(Text)
    audio_filename: Mapped[str | None] = mapped_column(String(200))
    typed_notes: Mapped[str | None] = mapped_column(Text)
    # Structured values the worker entered by hand, which always win over
    # anything the extraction agent inferred from speech.
    manual_fields: Mapped[dict | None] = mapped_column(JSON, default=dict)

    status: Mapped[VisitStatus] = mapped_column(
        Enum(VisitStatus), default=VisitStatus.queued, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    # --- Agent 1: extraction ------------------------------------------------
    extracted: Mapped[dict | None] = mapped_column(JSON)
    symptoms: Mapped[list | None] = mapped_column(JSON, default=list)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    bp_systolic: Mapped[int | None] = mapped_column(Integer)
    bp_diastolic: Mapped[int | None] = mapped_column(Integer)
    pulse: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    hb: Mapped[float | None] = mapped_column(Float)
    spo2: Mapped[int | None] = mapped_column(Integer)

    # --- Agent 2: risk classification --------------------------------------
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.unknown)
    risk_rationale: Mapped[str | None] = mapped_column(Text)
    risk_confidence: Mapped[float | None] = mapped_column(Float)
    # Guideline chunks the classifier actually retrieved and cited.
    guideline_citations: Mapped[list | None] = mapped_column(JSON, default=list)
    danger_signs: Mapped[list | None] = mapped_column(JSON, default=list)

    # --- Agent 3: scheduling / actions -------------------------------------
    recommended_actions: Mapped[list | None] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text)

    # Pipeline steps that fell back to rules because the LLM was unavailable.
    # Surfaced in the app so a demo never passes mock output off as real.
    degraded_steps: Mapped[list | None] = mapped_column(JSON, default=list)
    processing_ms: Mapped[int | None] = mapped_column(Integer)

    patient: Mapped["Patient"] = relationship(back_populates="visits")


class ScheduledVisit(Base):
    """Follow-ups produced by the scheduling agent, plus routine due visits."""

    __tablename__ = "scheduled_visits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)

    due_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str] = mapped_column(Text)
    # Mirrors the risk level that triggered it, so the plan can be colour-coded
    # without re-reading the visit.
    priority: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.green)
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus), default=ScheduleStatus.pending, index=True
    )

    created_by_visit_id: Mapped[str | None] = mapped_column(String(36))
    completed_by_visit_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Escalation(Base):
    """Raised when a visit comes back red. Cleared when a supervisor acts."""

    __tablename__ = "escalations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    visit_id: Mapped[str] = mapped_column(ForeignKey("visits.id"), index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)

    raised_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    reason: Mapped[str] = mapped_column(Text)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    acknowledged_by: Mapped[str | None] = mapped_column(String(36))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class AuditLog(Base):
    """Who looked at or changed which patient record, and when."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    detail: Mapped[str | None] = mapped_column(Text)
