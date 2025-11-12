"""
Tests for configuration module
"""

import pytest
from pydantic import ValidationError
from abs_worker.config import get_settings, Settings


def test_settings_loads_defaults():
    """Test that settings load with default values."""
    settings = Settings()
    assert settings.required_confirmations == 6
    assert settings.max_retries == 3
    assert settings.log_level == "INFO"


def test_settings_loads_from_env(monkeypatch):
    """Test that settings load from environment variables."""
    monkeypatch.setenv("REQUIRED_CONFIRMATIONS", "12")
    monkeypatch.setenv("MAX_RETRIES", "5")
    settings = Settings()
    assert settings.required_confirmations == 12
    assert settings.max_retries == 5


def test_singleton_pattern():
    """Test that get_settings() returns same instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


def test_validation_required_confirmations_positive():
    """Test that required_confirmations must be positive."""
    with pytest.raises(ValidationError):
        Settings(required_confirmations=0)
    with pytest.raises(ValidationError):
        Settings(required_confirmations=-1)


def test_validation_log_level():
    """Test that log_level must be valid."""
    with pytest.raises(ValidationError):
        Settings(log_level="INVALID")

    # Valid levels should work
    settings = Settings(log_level="debug")
    assert settings.log_level == "DEBUG"


def test_validation_max_retries():
    """Test that max_retries must be >= 1."""
    with pytest.raises(ValidationError):
        Settings(max_retries=0)
    with pytest.raises(ValidationError):
        Settings(max_retries=-1)

    # Valid values should work
    settings = Settings(max_retries=1)
    assert settings.max_retries == 1


def test_validation_retry_delay():
    """Test that retry_delay must be >= 1."""
    with pytest.raises(ValidationError):
        Settings(retry_delay=0)
    with pytest.raises(ValidationError):
        Settings(retry_delay=-1)

    # Valid values should work
    settings = Settings(retry_delay=1)
    assert settings.retry_delay == 1


def test_validation_worker_timeout():
    """Test that worker_timeout must be > 0."""
    with pytest.raises(ValidationError):
        Settings(worker_timeout=0)
    with pytest.raises(ValidationError):
        Settings(worker_timeout=-1)

    # Valid values should work
    settings = Settings(worker_timeout=1)
    assert settings.worker_timeout == 1


def test_validation_max_concurrent_tasks():
    """Test that max_concurrent_tasks must be > 0."""
    with pytest.raises(ValidationError):
        Settings(max_concurrent_tasks=0)
    with pytest.raises(ValidationError):
        Settings(max_concurrent_tasks=-1)

    # Valid values should work
    settings = Settings(max_concurrent_tasks=1)
    assert settings.max_concurrent_tasks == 1


def test_case_insensitive_env_vars(monkeypatch):
    """Test that environment variables are case insensitive."""
    monkeypatch.setenv("required_confirmations", "10")
    monkeypatch.setenv("MAX_RETRIES", "7")
    monkeypatch.setenv("Log_Level", "warning")

    settings = Settings()
    assert settings.required_confirmations == 10
    assert settings.max_retries == 7
    assert settings.log_level == "WARNING"


def test_env_file_loading(tmp_path, monkeypatch):
    """Test loading settings from .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        """
REQUIRED_CONFIRMATIONS=15
MAX_RETRIES=8
LOG_LEVEL=ERROR
"""
    )

    # Change to the temp directory so .env is found
    monkeypatch.chdir(tmp_path)

    settings = Settings()
    assert settings.required_confirmations == 15
    assert settings.max_retries == 8
    assert settings.log_level == "ERROR"
