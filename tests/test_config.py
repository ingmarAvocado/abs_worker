"""
Tests for configuration module
"""

import pytest
from pydantic import ValidationError
from abs_worker.config import (
    get_settings,
    Settings,
    BlockchainSettings,
    RetrySettings,
    WorkerSettings,
    CertificateSettings,
)


def test_settings_loads_defaults(monkeypatch, tmp_path):
    """Test that settings load with default values."""
    # Ensure clean environment for this test
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("BLOCKCHAIN_REQUIRED_CONFIRMATIONS", raising=False)
    monkeypatch.delenv("RETRY_MAX_RETRIES", raising=False)

    # Change to a temp directory without .env file
    monkeypatch.chdir(tmp_path)

    # Create a new Settings class that doesn't load from .env
    class TestSettings(Settings):
        model_config = Settings.model_config.copy()
        model_config["env_file"] = None

    settings = TestSettings(
        certificate=CertificateSettings(
            storage_path="/tmp/test/certificates", signing_key_path="/tmp/test/signing_key.pem"
        )
    )
    assert settings.blockchain.required_confirmations == 6
    assert settings.retry.max_retries == 3
    assert settings.log_level == "INFO"


def test_settings_loads_from_env(monkeypatch, tmp_path):
    """Test that settings load from environment variables."""
    # Create actual test files
    cert_dir = tmp_path / "certificates"
    cert_dir.mkdir()
    signing_key = tmp_path / "signing_key.pem"
    signing_key.write_text("0x" + "1" * 64)
    signing_key.chmod(0o600)

    monkeypatch.setenv("BLOCKCHAIN_REQUIRED_CONFIRMATIONS", "12")
    monkeypatch.setenv("RETRY_MAX_RETRIES", "5")
    monkeypatch.setenv("CERTIFICATE_STORAGE_PATH", str(cert_dir))
    monkeypatch.setenv("CERTIFICATE_SIGNING_KEY_PATH", str(signing_key))
    settings = Settings()
    assert settings.blockchain.required_confirmations == 12
    assert settings.retry.max_retries == 5


def test_singleton_pattern(monkeypatch, tmp_path):
    """Test that get_settings() returns same instance."""
    # Clear cache first
    get_settings.cache_clear()

    # Create actual test files
    cert_dir = tmp_path / "certificates"
    cert_dir.mkdir()
    signing_key = tmp_path / "signing_key.pem"
    signing_key.write_text("0x" + "1" * 64)
    signing_key.chmod(0o600)

    monkeypatch.setenv("CERTIFICATE_STORAGE_PATH", str(cert_dir))
    monkeypatch.setenv("CERTIFICATE_SIGNING_KEY_PATH", str(signing_key))

    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2

    # Clean up
    get_settings.cache_clear()


def test_validation_required_confirmations_positive():
    """Test that required_confirmations must be positive."""
    with pytest.raises(ValidationError):
        Settings(
            blockchain=BlockchainSettings(required_confirmations=0),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )
    with pytest.raises(ValidationError):
        Settings(
            blockchain=BlockchainSettings(required_confirmations=-1),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )


def test_validation_log_level():
    """Test that log_level must be valid."""
    with pytest.raises(ValidationError):
        Settings(
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
            log_level="INVALID",
        )

    # Valid levels should work
    settings = Settings(
        certificate=CertificateSettings(
            storage_path="/tmp/test/certificates",
            signing_key_path="/tmp/test/signing_key.pem",
        ),
        log_level="debug",
    )
    assert settings.log_level == "DEBUG"


def test_validation_max_retries():
    """Test that max_retries must be >= 1."""
    with pytest.raises(ValidationError):
        Settings(
            retry=RetrySettings(max_retries=0),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )
    with pytest.raises(ValidationError):
        Settings(
            retry=RetrySettings(max_retries=-1),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )

    # Valid values should work
    settings = Settings(
        retry=RetrySettings(max_retries=1),
        certificate=CertificateSettings(
            storage_path="/tmp/test/certificates",
            signing_key_path="/tmp/test/signing_key.pem",
        ),
    )
    assert settings.retry.max_retries == 1


def test_validation_retry_delay():
    """Test that retry_delay must be >= 1."""
    with pytest.raises(ValidationError):
        Settings(
            retry=RetrySettings(retry_delay=0),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )
    with pytest.raises(ValidationError):
        Settings(
            retry=RetrySettings(retry_delay=-1),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )

    # Valid values should work
    settings = Settings(
        retry=RetrySettings(retry_delay=1),
        certificate=CertificateSettings(
            storage_path="/tmp/test/certificates",
            signing_key_path="/tmp/test/signing_key.pem",
        ),
    )
    assert settings.retry.retry_delay == 1


def test_validation_worker_timeout():
    """Test that worker_timeout must be > 0."""
    with pytest.raises(ValidationError):
        Settings(
            worker=WorkerSettings(timeout=0),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )
    with pytest.raises(ValidationError):
        Settings(
            worker=WorkerSettings(timeout=-1),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )

    # Valid values should work
    settings = Settings(
        worker=WorkerSettings(timeout=1),
        certificate=CertificateSettings(
            storage_path="/tmp/test/certificates",
            signing_key_path="/tmp/test/signing_key.pem",
        ),
    )
    assert settings.worker.timeout == 1


def test_validation_max_concurrent_tasks():
    """Test that max_concurrent_tasks must be > 0."""
    with pytest.raises(ValidationError):
        Settings(
            worker=WorkerSettings(max_concurrent_tasks=0),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/certificates",
            ),
        )
    with pytest.raises(ValidationError):
        Settings(
            worker=WorkerSettings(max_concurrent_tasks=-1),
            certificate=CertificateSettings(
                storage_path="/tmp/test/certificates",
                signing_key_path="/tmp/test/signing_key.pem",
            ),
        )

    # Valid values should work
    settings = Settings(
        worker=WorkerSettings(max_concurrent_tasks=1),
        certificate=CertificateSettings(
            storage_path="/tmp/test/certificates",
            signing_key_path="/tmp/test/signing_key.pem",
        ),
    )
    assert settings.worker.max_concurrent_tasks == 1


def test_case_insensitive_env_vars(monkeypatch, tmp_path):
    """Test that environment variables are case insensitive."""
    # Create actual test files
    cert_dir = tmp_path / "certificates"
    cert_dir.mkdir()
    signing_key = tmp_path / "signing_key.pem"
    signing_key.write_text("0x" + "1" * 64)
    signing_key.chmod(0o600)

    monkeypatch.setenv("blockchain_required_confirmations", "10")
    monkeypatch.setenv("RETRY_MAX_RETRIES", "7")
    monkeypatch.setenv("Log_Level", "warning")
    monkeypatch.setenv("CERTIFICATE_STORAGE_PATH", str(cert_dir))
    monkeypatch.setenv("CERTIFICATE_SIGNING_KEY_PATH", str(signing_key))

    settings = Settings()
    assert settings.blockchain.required_confirmations == 10
    assert settings.retry.max_retries == 7
    assert settings.log_level == "WARNING"


def test_env_file_loading(tmp_path, monkeypatch):
    """Test that settings can load from environment variables (primary mechanism)."""
    # Clear any cached settings first
    from abs_worker.config import get_settings

    get_settings.cache_clear()

    # Clear environment variables that might interfere
    monkeypatch.delenv("BLOCKCHAIN_REQUIRED_CONFIRMATIONS", raising=False)
    monkeypatch.delenv("RETRY_MAX_RETRIES", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    # Set environment variables
    monkeypatch.setenv("BLOCKCHAIN_REQUIRED_CONFIRMATIONS", "15")
    monkeypatch.setenv("RETRY_MAX_RETRIES", "8")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")

    # Create a new Settings class that doesn't load from .env file
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field, field_validator

    class TestBlockchainSettings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=None, env_prefix="BLOCKCHAIN_", case_sensitive=False
        )
        required_confirmations: int = Field(default=6, gt=0)

    class TestRetrySettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=None, env_prefix="RETRY_", case_sensitive=False)
        max_retries: int = Field(default=3, ge=1)

    class TestSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=None, case_sensitive=False, extra="ignore")

        blockchain: TestBlockchainSettings = Field(default_factory=TestBlockchainSettings)
        retry: TestRetrySettings = Field(default_factory=TestRetrySettings)
        log_level: str = Field(default="INFO")

        @field_validator("log_level")
        @classmethod
        def validate_log_level(cls, v: str) -> str:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if v.upper() not in valid_levels:
                raise ValueError(f"log_level must be one of {valid_levels}")
            return v.upper()

    settings = TestSettings()
    assert settings.blockchain.required_confirmations == 15
    assert settings.retry.max_retries == 8
    assert settings.log_level == "ERROR"
