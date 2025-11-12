"""
Configuration settings for abs_worker using Pydantic Settings
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Blockchain settings
    required_confirmations: int = Field(default=6, gt=0)
    poll_interval: int = Field(default=2, gt=0)  # Seconds between blockchain polls
    max_poll_attempts: int = Field(default=100, gt=0)  # Maximum polling attempts
    max_confirmation_wait: int = Field(default=600, gt=0)  # Max seconds to wait for confirmation

    # Retry settings
    max_retries: int = Field(default=3, ge=1)
    retry_delay: int = Field(default=5, ge=1)
    retry_backoff_multiplier: float = Field(default=2.0, gt=1.0)

    # Worker settings
    worker_timeout: int = Field(default=300, gt=0)
    max_concurrent_tasks: int = Field(default=10, gt=0)

    # Optional settings
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern).

    Returns:
        Settings: Application settings instance
    """
    return Settings()
