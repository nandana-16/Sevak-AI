import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.models import db_models  # noqa: F401 (registers models with Base)
from app.routers import auth, visits, sync, dashboard, escalations, reports, tasks
from app.services.escalation_monitor import run_escalation_sweep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sevakai")

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(visits.router)
app.include_router(sync.router)
app.include_router(dashboard.router)
app.include_router(escalations.router)
app.include_router(reports.router)
app.include_router(tasks.router)

scheduler = BackgroundScheduler()


@app.on_event("startup")
def start_scheduler():
    def sweep():
        db = SessionLocal()
        try:
            fired = run_escalation_sweep(db)
            if fired:
                logger.info(f"Escalation sweep fired {fired} alert(s)")
        finally:
            db.close()

    scheduler.add_job(sweep, "interval", minutes=5, id="escalation_sweep")
    scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown(wait=False)


@app.get("/")
def root():
    return {"service": settings.app_name, "status": "running", "environment": settings.environment}


@app.get("/health")
def health():
    return {"status": "ok"}
