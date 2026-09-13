from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "development"
    database_url: str = "sqlite:///./data/sevakai.db"

    jwt_secret: str = "dev-only-insecure-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 20160

    llm_provider: str = "mock"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    stt_provider: str = "mock"
    whisper_model: str = "small"

    # Bhashini (ULCA) - the Government of India language platform.
    bhashini_user_id: str = ""
    bhashini_api_key: str = ""
    bhashini_pipeline_id: str = "64392f96daac500b55c543cd"

    aadhaar_hash_salt: str = "dev-only-salt"

    chroma_persist_dir: str = "./data/chroma"
    guidelines_dir: str = "./data/guidelines"
    audio_dir: str = "./data/audio"

    def _abs(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else (BACKEND_ROOT / path).resolve()

    @property
    def chroma_path(self) -> Path:
        return self._abs(self.chroma_persist_dir)

    @property
    def guidelines_path(self) -> Path:
        return self._abs(self.guidelines_dir)

    @property
    def audio_path(self) -> Path:
        return self._abs(self.audio_dir)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    for directory in (settings.chroma_path, settings.guidelines_path, settings.audio_path):
        directory.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
