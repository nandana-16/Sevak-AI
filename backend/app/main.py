"""SevakAI backend.

Run:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.models.db import Patient
from app.models.schemas import GuidelineSourceOut, HealthResponse
from app.rag import store
from app.routers import auth, dashboard, escalations, patients, schedule, visits

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("sevakai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    chunks = store.count()
    log.info("LLM provider: %s (%s)", settings.llm_provider, settings.groq_model)
    log.info("STT provider: %s", settings.stt_provider)
    log.info("Guideline chunks indexed: %d", chunks)
    if chunks == 0:
        log.warning(
            "No guideline corpus indexed. Risk classification will fall back to "
            "rules only. Run: python -m scripts.fetch_guidelines && "
            "python -m app.rag.ingest --reset"
        )
    yield


app = FastAPI(
    title="SevakAI",
    description=(
        "Agentic assistant for ASHA community health workers: voice and typed "
        "visit capture, extraction, NHM-guideline-grounded risk classification, "
        "and follow-up scheduling."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# The Android client sends an Authorization header, not cookies, so a
# permissive origin list costs nothing here and keeps emulator, device and a
# future dashboard all working.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(schedule.router)
app.include_router(escalations.router)
app.include_router(dashboard.router)


# The supervisor dashboard is a single static page served from the same origin
# as the API, so it needs no build step, no separate host, and no CORS
# exemption - and it reaches the backend at whatever address the browser used.
DASHBOARD = Path(__file__).parent / "static" / "dashboard.html"


@app.get("/", include_in_schema=False)
@app.get("/dashboard", include_in_schema=False)
def dashboard_page() -> FileResponse:
    return FileResponse(DASHBOARD, media_type="text/html")


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    from app.agents.llm import get_llm

    db = SessionLocal()
    try:
        patient_count = db.scalar(select(func.count()).select_from(Patient)) or 0
    finally:
        db.close()

    return HealthResponse(
        status="ok",
        llm_provider=settings.llm_provider,
        llm_ready=get_llm().available,
        stt_provider=settings.stt_provider,
        guideline_chunks=store.count(),
        patients=patient_count,
    )


@app.get("/api/guidelines", response_model=list[GuidelineSourceOut], tags=["meta"])
def guidelines() -> list[GuidelineSourceOut]:
    """What the risk classifier is actually grounded in. Exposed so the app
    can show a worker which document a recommendation came from."""
    return [GuidelineSourceOut(**row) for row in store.source_summary()]
