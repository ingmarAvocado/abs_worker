"""
Tests for configuration module
"""

import pytest
from abs_worker.config import WorkerSettings, get_settings


def test_worker_settings_defaults():
    """Test default settings values"""
    settings = WorkerSettings()

    assert settings.required_confirmations == 3
    assert settings.max_confirmation_wait == 600
    assert settings.max_retries == 3
    assert settings.retry_delay == 5
    assert settings.retry_backoff_multiplier == 2.0
    assert settings.poll_interval == 2
    assert settings.max_poll_attempts == 100
    assert settings.cert_storage_path == "/var/abs_notary/certificates"
    assert settings.cert_json_enabled is True
    assert settings.cert_pdf_enabled is True
    assert settings.worker_name == "abs_worker"
    assert settings.enable_structured_logging is True


def test_worker_settings_custom_values():
    """Test custom settings values"""
    settings = WorkerSettings(
        required_confirmations=5,
        max_confirmation_wait=120,
        max_retries=5,
        cert_storage_path="/custom/path",
    )

    assert settings.required_confirmations == 5
    assert settings.max_confirmation_wait == 120
    assert settings.max_retries == 5
    assert settings.cert_storage_path == "/custom/path"


def test_get_settings_singleton():
    """Test get_settings returns singleton instance"""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2


def test_settings_field_descriptions():
    """Test that all fields have descriptions"""
    settings = WorkerSettings()
    schema = WorkerSettings.model_json_schema()

    for field_name, field_info in schema.get("properties", {}).items():
        assert "description" in field_info, f"Field {field_name} missing description"
