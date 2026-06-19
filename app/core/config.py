from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, field_validator
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Developer Landing API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # CORS — comma-separated string in .env, e.g. ALLOWED_ORIGINS=*
    # or ALLOWED_ORIGINS=https://example.com,https://api.example.com
    ALLOWED_ORIGINS: str = "*"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v  # kept as str; split at usage time

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    # Email
    SMTP_HOST: str = "smtp.mail.ru"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    OWNER_EMAIL: str = ""

    # OpenRouter AI (Mistral Nemo)
    OPENROUTER_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "MISTRAL_API_KEY"),
    )
    OPENROUTER_MODEL: str = Field(
        default="mistralai/mistral-nemo",
        validation_alias=AliasChoices("OPENROUTER_MODEL", "MISTRAL_MODEL"),
    )
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    AI_TIMEOUT: int = 15

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 900  # 15 min

    # Paths
    DATA_DIR: Path = Path("data")
    LOGS_DIR: Path = Path("data/logs")
    METRICS_FILE: Path = Path("data/metrics.json")
    RATE_LIMITS_FILE: Path = Path("data/rate_limits.json")
    CONTACTS_LOG_FILE: Path = Path("data/logs/contacts.json")


settings = Settings()

# Ensure data directories exist on startup
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
