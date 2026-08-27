"""Shared pipeline runner used by both the live /visits/voice endpoint and the
offline /sync/batch endpoint, so a voice note recorded offline gets exactly the
same 5-agent processing once it syncs."""
import json
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.graph import get_pipeline
from app.agents.stt_client import get_stt_provider
from app.models.db_models import Visit, RiskFlag, Action, RchRegisterEntry, Patient, Worker
from app.services.whatsapp import send_whatsapp_message
from app.services.audit import log_action

RISK_SCORE_MAP = {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.2}


def process_voice_visit(
    db: Session,
    worker_id: str,
    patient_id: str,
    language_code: str = "hi",
    transcript: str | None = None,
    audio_base64: str | None = None,
) -> dict:
    start = time.monotonic()

    if not transcript:
        if not audio_base64:
            raise ValueError("Either transcript or audio_base64 must be provided")
        transcript = get_stt_provider().transcribe(audio_base64, language_code)

    visit = Visit(
        patient_id=patient_id, worker_id=worker_id, transcript=transcript,
        language_code=language_code, pipeline_status="processing",
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)

    pipeline = get_pipeline()
    result = pipeline.invoke({"transcript": transcript, "language_code": language_code})

    structured = result["structured"]
    risk_result = result["risk_result"]
    actions_result = result["actions_result"]
    hmis_fields = result["hmis_fields"]
    risk_level = risk_result.get("risk_level", "LOW")

    visit.structured_json = json.dumps(structured)
    visit.risk_level = risk_level
    visit.risk_score = RISK_SCORE_MAP.get(risk_level, 0.2)
    visit.pipeline_status = "complete"
    db.commit()

    flag = RiskFlag(
        visit_id=visit.visit_id, risk_level=risk_level,
        drivers_json=json.dumps(risk_result.get("drivers", [])),
    )
    db.add(flag)

    patient = db.get(Patient, patient_id)
    generated_actions = []
    for a in actions_result.get("actions", []):
        due_at = None
        if a.get("type") == "followup" and a.get("due_days") is not None:
            from datetime import timedelta
            due_at = datetime.now(timezone.utc) + timedelta(days=a["due_days"])

        action = Action(visit_id=visit.visit_id, type=a["type"], content=a["content"], due_at=due_at)

        if a["type"] == "whatsapp" and patient and patient.phone:
            send_result = send_whatsapp_message(patient.phone, a["content"])
            action.status = send_result["status"]
            if send_result["status"] == "sent":
                action.sent_at = datetime.now(timezone.utc)

        db.add(action)
        generated_actions.append({"type": a["type"], "content": a["content"]})

    if risk_level == "HIGH":
        worker = db.get(Worker, worker_id)
        supervisor_note = (
            f"HIGH RISK ALERT: {patient.name if patient else 'Patient'} flagged HIGH risk "
            f"by ASHA worker {worker.name if worker else worker_id}. "
            f"Drivers: {'; '.join(d['observation'] for d in risk_result.get('drivers', []))}"
        )
        send_whatsapp_message("supervisor", supervisor_note)
        flag.escalated_at = None  # cleared until the 48h monitor actually escalates
        log_action(db, worker_id, "high_risk_alert_sent", visit.visit_id, "visit", supervisor_note)

    if structured.get("pregnancy_stage_months") is not None:
        rch_entry = RchRegisterEntry(
            patient_id=patient_id, visit_id=visit.visit_id,
            data_json=json.dumps({**hmis_fields, "pregnancy_stage_months": structured["pregnancy_stage_months"]}),
        )
        db.add(rch_entry)

    db.commit()
    log_action(db, worker_id, "visit_processed", visit.visit_id, "visit", f"risk_level={risk_level}")

    latency_ms = int((time.monotonic() - start) * 1000)

    return {
        "visit_id": visit.visit_id,
        "transcript": transcript,
        "structured_json": structured,
        "risk_level": risk_level,
        "risk_score": visit.risk_score,
        "risk_drivers": risk_result.get("drivers", []),
        "actions_generated": generated_actions,
        "latency_ms": latency_ms,
    }
