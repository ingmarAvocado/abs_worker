"""
Configuration settings for abs_worker using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class WorkerSettings(BaseSettings):
    """Worker configuration settings"""

    # Blockchain confirmation settings
    required_confirmations: int = Field(
        default=3,
        description="Number of block confirmations required before marking transaction as complete"
    )
    max_confirmation_wait: int = Field(
        default=600,
        description="Maximum time to wait for transaction confirmation (seconds)"
    )

    # Retry settings
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed operations"
    )
    retry_delay: int = Field(
        default=5,
        description="Initial delay between retry attempts (seconds)"
    )
    retry_backoff_multiplier: float = Field(
        default=2.0,
        description="Multiplier for exponential backoff between retries"
    )

    # Transaction monitoring
    poll_interval: int = Field(
        default=2,
        description="Interval between transaction status polls (seconds)"
    )
    max_poll_attempts: int = Field(
        default=100,
        description="Maximum number of polling attempts before timeout"
    )

    # Certificate settings
    cert_storage_path: str = Field(
        default="/var/abs_notary/certificates",
        description="Base path for storing generated certificates"
    )
    cert_json_enabled: bool = Field(
        default=True,
        description="Generate signed JSON certificates"
    )
    cert_pdf_enabled: bool = Field(
        default=True,
        description="Generate signed PDF certificates"
    )

    # Worker settings
    worker_name: str = Field(
        default="abs_worker",
        description="Worker service name for logging"
    )
    enable_structured_logging: bool = Field(
        default=True,
        description="Enable structured JSON logging via abs_utils"
    )

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
_settings: WorkerSettings | None = None


def get_settings() -> WorkerSettings:
    """Get or create global settings instance"""
    global _settings
    if _settings is None:
        _settings = WorkerSettings()
    return _settings
