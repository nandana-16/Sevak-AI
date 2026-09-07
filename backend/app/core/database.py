from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKEND_ROOT, settings
from app.models.db import Base

url = settings.database_url
if url.startswith("sqlite:///./"):
    # Resolve relative to the backend root, not the process working directory,
    # so scripts and uvicorn agree on which file the database lives in.
    url = "sqlite:///" + str(BACKEND_ROOT / url.removeprefix("sqlite:///./"))

engine = create_engine(
    url,
    # SQLite only: the pipeline touches the session from worker threads.
    connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    (BACKEND_ROOT / "data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
