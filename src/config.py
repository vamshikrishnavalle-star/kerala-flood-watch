"""Application configuration module.

Loads environment variables from .env file using pydantic-settings.
"""

from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema and defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    REGION_NAME: str = ""
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    ADVISORY_PROVIDER: Literal["template", "claude", "gemini"] = "template"
    ADVISORY_API_KEY: Optional[str] = None
    ALERT_THRESHOLD: float = 0.7
    ALERT_CONSECUTIVE_READINGS: int = 3


settings = Settings()
