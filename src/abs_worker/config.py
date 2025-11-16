"""
Configuration settings for abs_worker using Pydantic Settings

Settings are organized into logical groups for better maintainability:
- BlockchainSettings: Transaction confirmation and polling configuration
- RetrySettings: Error handling and retry behavior
- WorkerSettings: Worker execution and concurrency limits
- CertificateSettings: Certificate storage and signing key paths
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, Union


class BlockchainSettings(BaseSettings):
    """Blockchain transaction and polling configuration."""

    model_config = SettingsConfigDict(
        env_prefix="BLOCKCHAIN_",
        case_sensitive=False,
    )

    required_confirmations: int = Field(
        default=6,
        gt=0,
        description="Number of block confirmations required for finality",
    )
    poll_interval: int = Field(
        default=2,
        gt=0,
        description="Seconds between blockchain polls",
    )
    max_poll_attempts: int = Field(
        default=100,
        gt=0,
        description="Maximum number of polling attempts",
    )
    max_confirmation_wait: int = Field(
        default=600,
        gt=0,
        description="Maximum seconds to wait for transaction confirmation",
    )


class RetrySettings(BaseSettings):
    """Error handling and retry behavior configuration."""

    model_config = SettingsConfigDict(
        env_prefix="RETRY_",
        case_sensitive=False,
    )

    max_retries: int = Field(
        default=3,
        ge=1,
        description="Maximum number of retry attempts for failed operations",
    )
    retry_delay: int = Field(
        default=5,
        ge=1,
        description="Initial delay in seconds before first retry",
    )
    backoff_multiplier: float = Field(
        default=2.0,
        gt=1.0,
        description="Multiplier for exponential backoff between retries",
    )


class WorkerSettings(BaseSettings):
    """Worker execution and concurrency configuration."""

    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        case_sensitive=False,
    )

    timeout: int = Field(
        default=300,
        gt=0,
        description="Maximum seconds for a single worker task",
    )
    max_concurrent_tasks: int = Field(
        default=10,
        gt=0,
        description="Maximum number of concurrent worker tasks",
    )


class CertificateSettings(BaseSettings):
    """Certificate storage and signing configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CERTIFICATE_",
        case_sensitive=False,
    )

    storage_path: str = Field(
        default="/tmp/certificates",  # Default for development
        description="Directory path for storing generated certificates (auto-created if missing)",
    )
    signing_key_path: Union[str, None] = Field(
        default=None,
        description="File path to ECDSA signing key (must exist with secure permissions)",
    )
    signing_key_hex: Union[str, None] = Field(
        default=None,
        description="Hex-encoded ECDSA private key (alternative to signing_key_path)",
    )
    certificate_version: str = Field(
        default="1.0",
        description="Version string for generated certificates",
    )

    @field_validator("signing_key_path")
    @classmethod
    def validate_signing_key_path(cls, v: Union[str, None]) -> Union[str, None]:
        """
        Validate signing key file exists and is readable.

        Raises:
            ValueError: If file doesn't exist or isn't readable
        """
        if v is None or v == "":
            return v  # Allow None/empty for optional configuration
        if not os.path.exists(v):
            raise ValueError(f"Signing key path does not exist: {v}")
        if not os.access(v, os.R_OK):
            raise ValueError(f"Signing key path is not readable: {v}")
        return v

    @field_validator("signing_key_hex")
    @classmethod
    def validate_signing_key_hex(cls, v: Union[str, None]) -> Union[str, None]:
        """
        Validate hex-encoded signing key format and length.

        Must be a valid hex string representing a 32-byte (256-bit) ECDSA private key.

        Raises:
            ValueError: If key format or length is invalid
        """
        if v is None or v == "":  # Empty is allowed (will use file path instead)
            return v

        # Remove 0x prefix if present
        key_hex = v[2:] if v.startswith("0x") else v

        # Check if valid hex
        try:
            bytes.fromhex(key_hex)
        except ValueError:
            raise ValueError("Signing key must be valid hexadecimal")

        # Check length (32 bytes = 64 hex chars)
        if len(key_hex) != 64:
            raise ValueError(
                f"Signing key must be 32 bytes (64 hex characters), got {len(key_hex)}"
            )

        return key_hex  # Return normalized version without 0x prefix

    @field_validator("certificate_version")
    @classmethod
    def validate_certificate_version(cls, v: str) -> str:
        """
        Validate certificate version format.

        Should be a semantic version string (e.g., "1.0", "2.1.0").

        Raises:
            ValueError: If version format is invalid
        """
        import re

        if not re.match(r"^\d+\.\d+(\.\d+)?$", v):
            raise ValueError(
                f"Certificate version must be semantic version (e.g., '1.0'), got '{v}'"
            )
        return v

    @field_validator("storage_path")
    @classmethod
    def validate_storage_path(cls, v: str) -> str:
        """
        Validate or create certificate storage directory.

        Auto-creates the directory if it doesn't exist. Validates write permissions.

        Raises:
            ValueError: If directory cannot be created or isn't writable
        """
        # Try to create directory if it doesn't exist
        if not os.path.exists(v):
            try:
                os.makedirs(v, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Cannot create certificate storage path: {v} - {e}") from e

        # Verify write permissions
        if not os.access(v, os.W_OK):
            raise ValueError(f"Certificate storage path is not writable: {v}")

        return v


class Settings(BaseSettings):
    """
    Main application settings loaded from environment variables and .env file.

    Settings are organized into logical groups:
    - blockchain: Transaction confirmation and polling
    - retry: Error handling and retry behavior
    - worker: Worker execution and concurrency
    - certificate: Certificate storage and signing

    Environment variables can use either:
    - Grouped: BLOCKCHAIN_REQUIRED_CONFIRMATIONS=6
    - Direct: LOG_LEVEL=INFO
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Grouped settings
    blockchain: BlockchainSettings = Field(default_factory=BlockchainSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    worker: WorkerSettings = Field(default_factory=WorkerSettings)
    certificate: CertificateSettings = Field(default_factory=CertificateSettings)

    # Top-level settings
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    environment: str = Field(
        default="development",
        description="Application environment (development, staging, production)",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate log level is a standard Python logging level.

        Raises:
            ValueError: If log level is not recognized
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern).

    Settings are loaded from environment variables and .env file.
    The instance is cached to avoid repeated parsing.

    Returns:
        Settings: Application settings instance

    Raises:
        ValidationError: If required settings are missing or invalid
    """
    return Settings()
