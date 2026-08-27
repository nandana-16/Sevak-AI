from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class LoginRequest(BaseModel):
    phone: str
    pin: str


class LoginResponse(BaseModel):
    access_token: str
    role: str
    worker_id: str
    name: str


class PatientOut(BaseModel):
    patient_id: str
    name: str
    age: Optional[int] = None
    village: Optional[str] = None
    category: str
    last_risk_level: Optional[str] = None
    last_visit_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VoiceVisitRequest(BaseModel):
    worker_id: str
    patient_id: str
    audio_base64: Optional[str] = None
    transcript: Optional[str] = None  # set directly when using client-side (browser) STT
    language_code: str = "hi"


class RiskDriver(BaseModel):
    observation: str
    protocol_reference: str
    reason: str


class VoiceVisitResponse(BaseModel):
    visit_id: str
    transcript: str
    structured_json: dict
    risk_level: str
    risk_score: float
    risk_drivers: list[RiskDriver]
    actions_generated: list[dict]
    latency_ms: int


class SyncRecord(BaseModel):
    record_type: str
    record_json: dict


class SyncBatchRequest(BaseModel):
    worker_id: str
    records: list[SyncRecord]


class SyncBatchResponse(BaseModel):
    synced: int
    failed: int
    errors: list[str]


class EscalationOut(BaseModel):
    flag_id: str
    patient_name: str
    worker_name: str
    risk_level: str
    flagged_at: datetime
    hours_elapsed: float


class HeatmapPoint(BaseModel):
    lat: float
    lng: float
    village: str
    risk_level: str
    patient_count: int


class DashboardMetrics(BaseModel):
    visits_today: int
    high_risk_cases: int
    pending_followups: int
    hmis_completion_rate: float
