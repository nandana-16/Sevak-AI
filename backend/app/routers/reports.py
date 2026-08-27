import json
from datetime import datetime, timezone
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_roles, CurrentUser
from app.models.db_models import Visit, Patient, Worker, HmisReport
from app.agents.agent4_reporting import build_hmis_fields
from app.services.pdf_report import generate_hmis_pdf

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/hmis/{worker_id}/{month}/{year}")
def get_hmis_report(worker_id: str, month: int, year: int, db: Session = Depends(get_db),
                     user: CurrentUser = Depends(require_roles("asha", "anm", "admin"))):
    worker = db.get(Worker, worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    _, last_day = monthrange(year, month)
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    visits = (
        db.query(Visit)
        .filter(Visit.worker_id == worker_id, Visit.created_at >= start, Visit.created_at <= end,
                Visit.pipeline_status == "complete")
        .all()
    )

    rows = []
    for v in visits:
        structured = json.loads(v.structured_json) if v.structured_json else {}
        patient = db.get(Patient, v.patient_id)
        fields = build_hmis_fields(structured, {"risk_level": v.risk_level})
        rows.append({"patient_name": patient.name if patient else "Unknown", **fields})

    pdf_path = generate_hmis_pdf(worker.name, month, year, rows)

    report = HmisReport(worker_id=worker_id, month=month, year=year,
                         data_json=json.dumps(rows), pdf_path=pdf_path)
    db.add(report)
    db.commit()

    return {"report_data_json": rows, "pdf_url": f"/api/v1/reports/download/{report.report_id}"}


@router.get("/download/{report_id}")
def download_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(HmisReport, report_id)
    if not report or not report.pdf_path:
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report.pdf_path, filename=report.pdf_path.split("/")[-1], media_type="application/pdf")
