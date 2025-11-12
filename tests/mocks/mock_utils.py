"""
Mock implementations of abs_utils interfaces for testing and examples.

This module provides drop-in replacements for abs_utils components that can be used
in tests and examples without requiring the real abs_utils library.
"""

import json
import logging
from typing import Any, Dict, Optional


class MockLogger:
    """Mock logger that prints structured logs to console"""

    def __init__(self, name: str):
        self.name = name
        self._console_logger = logging.getLogger(name)
        if not self._console_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self._console_logger.addHandler(handler)
            self._console_logger.setLevel(logging.INFO)

    def _log(self, level: str, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log a message with optional extra data"""
        if extra:
            # Format as JSON-like structure for readability
            extra_str = json.dumps(extra, default=str)
            full_message = f"{message} | {extra_str}"
        else:
            full_message = message

        if level == 'debug':
            self._console_logger.debug(full_message)
        elif level == 'info':
            self._console_logger.info(full_message)
        elif level == 'warning':
            self._console_logger.warning(full_message)
        elif level == 'error':
            self._console_logger.error(full_message)
        elif level == 'critical':
            self._console_logger.critical(full_message)

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self._log('debug', message, extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self._log('info', message, extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self._log('warning', message, extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log error message"""
        self._log('error', message, extra)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log critical message"""
        self._log('critical', message, extra)


# Global logger registry
_loggers: Dict[str, MockLogger] = {}


def get_logger(name: str) -> MockLogger:
    """Get or create a logger with the given name"""
    if name not in _loggers:
        _loggers[name] = MockLogger(name)
    return _loggers[name]


class MockException(Exception):
    """Mock exception that can be serialized to dict"""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "exception_type": self.__class__.__name__,
        }


class ValidationError(MockException):
    """Mock validation error"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field} if field else {})


class ConfigurationError(MockException):
    """Mock configuration error"""
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, "CONFIGURATION_ERROR", {"config_key": config_key} if config_key else {})


# Convenience functions for testing
def create_test_logger(name: str = "test") -> MockLogger:
    """Create a test logger"""
    return get_logger(name)


def create_test_exception(message: str = "Test error") -> MockException:
    """Create a test exception"""
    return MockException(message)