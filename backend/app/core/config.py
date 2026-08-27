from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SevakAI Backend"
    environment: str = "development"

    database_url: str = "sqlite:///./data/sevakai.db"

    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    # LLM provider: "gemini" or "mock"
    llm_provider: str = "mock"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"

    # STT provider: "bhashini" or "mock"
    stt_provider: str = "mock"
    bhashini_api_key: str = ""
    bhashini_user_id: str = ""
    bhashini_endpoint: str = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"

    # WhatsApp: "meta" or "mock"
    whatsapp_provider: str = "mock"
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""

    chroma_persist_dir: str = "./data/chroma"

    high_risk_alert_seconds: int = 60
    escalation_threshold_hours: int = 48

    cors_origins: list[str] = ["*"]


settings = Settings()
