from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "DevOpsAI"
    environment: str = "development"

    openai_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None

    max_incident_description_chars: int = 5_000
    max_log_sample_chars: int = 20_000

    database_path: Path = PROJECT_ROOT / "data" / "devops_ai.db"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()