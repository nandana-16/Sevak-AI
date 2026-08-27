import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Worker(Base):
    __tablename__ = "workers"

    worker_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    pin_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="asha")  # asha | anm | bmo | admin
    language_pref: Mapped[str] = mapped_column(String, default="hi")
    sub_centre_id: Mapped[str] = mapped_column(String, nullable=True)
    district: Mapped[str] = mapped_column(String, nullable=True)
    village: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.worker_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String, nullable=True)
    village: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, default="general")  # pregnant | child | general
    pregnancy_stage_months: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Visit(Base):
    __tablename__ = "visits"

    visit_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), nullable=False)
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.worker_id"), nullable=False)
    audio_url: Mapped[str] = mapped_column(String, nullable=True)
    language_code: Mapped[str] = mapped_column(String, default="hi")
    transcript: Mapped[str] = mapped_column(Text, nullable=True)
    structured_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string, Agent 1 output
    risk_score: Mapped[float] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String, nullable=True)  # HIGH | MEDIUM | LOW
    pipeline_status: Mapped[str] = mapped_column(String, default="pending")  # pending|processing|complete|failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class RiskFlag(Base):
    __tablename__ = "risk_flags"

    flag_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    visit_id: Mapped[str] = mapped_column(String, ForeignKey("visits.visit_id"), nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    drivers_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON list of {observation, protocol, reason}
    overridden_by: Mapped[str] = mapped_column(String, nullable=True)
    override_reason: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    escalated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    actioned_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Action(Base):
    __tablename__ = "actions"

    action_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    visit_id: Mapped[str] = mapped_column(String, ForeignKey("visits.visit_id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # referral | whatsapp | followup
    content: Mapped[str] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|sent|complete
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class HmisReport(Base):
    __tablename__ = "hmis_reports"

    report_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    worker_id: Mapped[str] = mapped_column(String, ForeignKey("workers.worker_id"), nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str] = mapped_column(String, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class RchRegisterEntry(Base):
    __tablename__ = "rch_register"

    entry_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    patient_id: Mapped[str] = mapped_column(String, ForeignKey("patients.patient_id"), nullable=False)
    visit_id: Mapped[str] = mapped_column(String, ForeignKey("visits.visit_id"), nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class SyncQueueEntry(Base):
    __tablename__ = "sync_queue"

    queue_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    worker_id: Mapped[str] = mapped_column(String, nullable=False)
    record_type: Mapped[str] = mapped_column(String, nullable=False)
    record_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    synced_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|synced|failed


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    record_id: Mapped[str] = mapped_column(String, nullable=True)
    record_type: Mapped[str] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now)
    ip_address: Mapped[str] = mapped_column(String, nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=True)
