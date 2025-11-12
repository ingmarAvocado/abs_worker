"""
Example: Configuration Management

This example demonstrates:
- Loading settings from environment variables and .env files
- Accessing configuration values throughout the application
- Singleton pattern usage
- Validation of configuration constraints
"""

from abs_worker.config import get_settings


def main():
    """Demonstrate configuration loading and usage"""
    settings = get_settings()

    print("✅ Configuration loaded successfully!")
    print(f"  Required confirmations: {settings.required_confirmations}")
    print(f"  Max retries: {settings.max_retries}")
    print(f"  Retry delay: {settings.retry_delay}")
    print(f"  Worker timeout: {settings.worker_timeout}")
    print(f"  Max concurrent tasks: {settings.max_concurrent_tasks}")
    print(f"  Log level: {settings.log_level}")
    print(f"  Environment: {settings.environment}")

    # Demonstrate singleton pattern
    settings2 = get_settings()
    print(f"\n✅ Singleton pattern working: {settings is settings2}")

    # Show that settings are validated
    print("\n✅ All settings validated:")
    print(f"  - required_confirmations > 0: {settings.required_confirmations > 0}")
    print(f"  - max_retries >= 1: {settings.max_retries >= 1}")
    print(f"  - retry_delay >= 1: {settings.retry_delay >= 1}")
    print(f"  - worker_timeout > 0: {settings.worker_timeout > 0}")
    print(f"  - max_concurrent_tasks > 0: {settings.max_concurrent_tasks > 0}")
    print(f"  - log_level in valid set: {settings.log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']}")


if __name__ == "__main__":
    main()