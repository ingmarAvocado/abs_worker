"""
Pytest configuration and shared fixtures for abs_worker tests with real database
"""

import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator, Dict

import asyncpg
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from unittest.mock import AsyncMock

from abs_orm import Base
from abs_worker.config import Settings

# Import mock implementations for blockchain and external services
from tests.mocks import MockBlockchain

# Load environment variables
load_dotenv()

# Safety check: prevent accidental production database access
def _validate_test_environment():
    """Validate that we're in a test environment and not accidentally using production database."""
    # Check if we're running in a test context
    import sys
    is_pytest = "pytest" in sys.modules or (sys.argv and "pytest" in sys.argv[0])

    # If we're running tests, allow the environment but add warnings
    if is_pytest:
        production_db_names = {"abs_notary", "production", "prod"}
        current_db = os.getenv("DB_NAME", "").lower()

        if current_db in production_db_names:
            print(f"⚠️  WARNING: DB_NAME is set to '{current_db}' but tests will use isolated test databases.")
            print("   This is safe - each test creates its own database like 'test_module_worker'")
        return  # Allow tests to proceed

    # Non-test context: strict validation
    production_db_names = {"abs_notary", "production", "prod"}
    current_db = os.getenv("DB_NAME", "").lower()

    if current_db in production_db_names:
        raise RuntimeError(
            f"SAFETY CHECK FAILED: Cannot run against production database '{current_db}' outside of tests. "
            f"Please set DB_NAME to a development database name."
        )

    # Also check that we don't use suspicious host patterns
    host = os.getenv("DB_HOST", "localhost").lower()
    if any(prod_pattern in host for prod_pattern in ["prod", "production", "live"]):
        raise RuntimeError(
            f"SAFETY CHECK FAILED: Database host '{host}' appears to be a production host. "
            f"Use localhost or development hosts only."
        )

# Run safety check on import
_validate_test_environment()


async def _check_database_availability():
    """Check if the database is available for integration tests."""
    try:
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", "5432"))
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "password")

        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres",
            timeout=5  # 5 second timeout
        )
        await conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
async def database_available():
    """Check if database is available and skip integration tests if not."""
    return await _check_database_availability()

# Cache for engines per module to reuse across tests
_engine_cache: Dict[str, AsyncEngine] = {}
_db_created: Dict[str, bool] = {}


def create_database_url(database: str) -> str:
    """Create database URL from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


async def create_test_database(db_name: str) -> None:
    """Create a test database."""
    # Safety check: ensure database name looks like a test database
    if not db_name.startswith("test_"):
        raise RuntimeError(
            f"SAFETY CHECK FAILED: Database name '{db_name}' does not start with 'test_'. "
            f"Only test databases should be created/dropped during testing."
        )

    if db_name in _db_created:
        return

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password")

    conn = await asyncpg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="postgres"
    )

    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await conn.execute(f'CREATE DATABASE "{db_name}"')
        _db_created[db_name] = True
    finally:
        await conn.close()


async def drop_test_database(db_name: str) -> None:
    """Drop a test database."""
    # Safety check: ensure database name looks like a test database
    if not db_name.startswith("test_"):
        raise RuntimeError(
            f"SAFETY CHECK FAILED: Refusing to drop database '{db_name}' that doesn't start with 'test_'. "
            f"This safety check prevents accidental deletion of production databases."
        )

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password")

    conn = await asyncpg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database="postgres"
    )

    try:
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = $1
            AND pid <> pg_backend_pid()
        """, db_name)
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        _db_created.pop(db_name, None)
    finally:
        await conn.close()


def get_test_db_name(request) -> str:
    """Generate database name for the test module."""
    module_name = request.module.__name__.split('.')[-1]

    # Add worker id if running in parallel
    worker_id = getattr(request.config, 'workerinput', {}).get('workerid', '')
    if worker_id:
        return f"test_{module_name}_{worker_id}"
    else:
        return f"test_{module_name}"


async def get_or_create_engine(db_name: str) -> AsyncEngine:
    """Get or create an engine for the database."""
    if db_name not in _engine_cache:
        # Create database if needed
        await create_test_database(db_name)

        # Create engine with NullPool to avoid connection pool issues
        database_url = create_database_url(database=db_name)
        engine = create_async_engine(
            database_url,
            echo=False,
            poolclass=NullPool,  # Use NullPool to avoid event loop issues
        )

        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        _engine_cache[db_name] = engine

    return _engine_cache[db_name]


@pytest_asyncio.fixture
async def db_context(request):
    """Create a DatabaseContext-like wrapper for testing with proper isolation."""
    from abs_orm.repositories import (
        UserRepository, DocumentRepository, ApiKeyRepository
    )

    # Get database name for this module
    db_name = get_test_db_name(request)

    # Get or create engine
    engine = await get_or_create_engine(db_name)

    # Create session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create a session and use savepoint
    async with async_session_maker() as session:
        # Start a transaction
        trans = await session.begin()

        # Start a savepoint
        nested = await session.begin_nested()

        # Create a test database context wrapper
        class TestDatabaseContext:
            def __init__(self, session):
                self.session = session
                self._user_repo = None
                self._document_repo = None
                self._api_key_repo = None

            @property
            def users(self):
                if self._user_repo is None:
                    self._user_repo = UserRepository(self.session)
                return self._user_repo

            @property
            def documents(self):
                if self._document_repo is None:
                    self._document_repo = DocumentRepository(self.session)
                return self._document_repo

            @property
            def api_keys(self):
                if self._api_key_repo is None:
                    self._api_key_repo = ApiKeyRepository(self.session)
                return self._api_key_repo

            async def commit(self):
                await self.session.commit()

            async def rollback(self):
                await self.session.rollback()

            async def flush(self):
                await self.session.flush()

        db = TestDatabaseContext(session)

        yield db
        await session.flush()


@pytest_asyncio.fixture
async def session(db_context):
    """Expose the session from db_context for backward compatibility."""
    return db_context.session


@pytest.fixture(scope="session", autouse=True)
def cleanup(request):
    """Clean up after all tests."""
    def finalizer():
        # Use asyncio to run async cleanup
        import asyncio

        async def async_cleanup():
            """Properly dispose engines and drop databases."""
            try:
                # Cleanup all created databases and engines
                for db_name in list(_db_created.keys()):
                    try:
                        # Dispose engine if it exists
                        if db_name in _engine_cache:
                            engine = _engine_cache[db_name]
                            await engine.dispose()
                            print(f"Disposed engine for {db_name}")

                        # Drop the test database
                        await drop_test_database(db_name)
                        print(f"Dropped test database: {db_name}")

                    except Exception as e:
                        print(f"Warning: Failed to cleanup {db_name}: {e}")

                # Clear caches
                _engine_cache.clear()
                _db_created.clear()
                print("Test cleanup completed")

            except Exception as e:
                print(f"Error during test cleanup: {e}")

        # Run the async cleanup
        try:
            asyncio.run(async_cleanup())
        except Exception as e:
            print(f"Failed to run async cleanup: {e}")

    request.addfinalizer(finalizer)


# ============================================================================
# abs_worker specific fixtures
# ============================================================================

@pytest.fixture
def worker_settings():
    """Provide test configuration settings"""
    return Settings(
        required_confirmations=2,
        max_retries=2,
        retry_delay=1,
        worker_timeout=60,
        max_concurrent_tasks=5,
        log_level="DEBUG",
        environment="test",
    )


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings cache between tests"""
    from abs_worker.config import get_settings

    # Clear the LRU cache before each test
    get_settings.cache_clear()
    yield
    # Clear the LRU cache after each test
    get_settings.cache_clear()


# ============================================================================
# Real data fixtures using factories
# ============================================================================

from tests.factories import UserFactory, DocumentFactory, ApiKeyFactory


@pytest_asyncio.fixture
async def test_user(db_context):
    """Create a real test user in the database."""
    user = await UserFactory.create(db_context.session)
    await db_context.commit()
    return user


@pytest_asyncio.fixture
async def test_admin(db_context):
    """Create a real admin user in the database."""
    admin = await UserFactory.create_admin(db_context.session)
    await db_context.commit()
    return admin


@pytest_asyncio.fixture
async def test_document(db_context, test_user):
    """Create a real pending document in the database."""
    doc = await DocumentFactory.create_pending(db_context.session, owner=test_user)
    await db_context.commit()
    return doc


@pytest_asyncio.fixture
async def test_nft_document(db_context, test_user):
    """Create a real pending NFT document in the database."""
    doc = await DocumentFactory.create_nft_pending(db_context.session, owner=test_user)
    await db_context.commit()
    return doc


@pytest_asyncio.fixture
async def test_processing_document(db_context, test_user):
    """Create a real processing document in the database."""
    doc = await DocumentFactory.create_processing(db_context.session, owner=test_user)
    await db_context.commit()
    return doc


@pytest_asyncio.fixture
async def test_on_chain_document(db_context, test_user):
    """Create a real on-chain document in the database."""
    doc = await DocumentFactory.create_on_chain(db_context.session, owner=test_user)
    await db_context.commit()
    return doc


@pytest_asyncio.fixture
async def test_error_document(db_context, test_user):
    """Create a real error document in the database."""
    doc = await DocumentFactory.create_error(db_context.session, owner=test_user)
    await db_context.commit()
    return doc


@pytest_asyncio.fixture
async def test_api_key(db_context, test_user):
    """Create a real API key in the database."""
    api_key = await ApiKeyFactory.create(db_context.session, owner=test_user)
    await db_context.commit()
    return api_key


@pytest_asyncio.fixture
async def test_workflow_documents(db_context):
    """Create a complete set of documents representing a workflow."""
    workflow = await DocumentFactory.create_workflow_batch(db_context.session)
    await db_context.commit()
    return workflow


# ============================================================================
# Mock fixtures for external services (blockchain, etc.)
# ============================================================================

@pytest.fixture
async def mock_blockchain():
    """Provide mock blockchain interface for testing"""
    return MockBlockchain()


@pytest.fixture
def mock_transaction_receipt():
    """Provide a mock blockchain transaction receipt"""
    return {
        "transactionHash": "0xabc123",
        "blockNumber": 12345,
        "blockHash": "0xblock123",
        "status": 1,  # Success
        "gasUsed": 50000,
        "from": "0xsender",
        "to": "0xcontract",
    }


# ============================================================================
# Backward compatibility aliases (deprecated - use test_* fixtures instead)
# ============================================================================

@pytest_asyncio.fixture
async def mock_document(test_document):
    """Backward compatibility - use test_document instead."""
    return test_document


@pytest_asyncio.fixture
async def mock_nft_document(test_nft_document):
    """Backward compatibility - use test_nft_document instead."""
    return test_nft_document


@pytest_asyncio.fixture
async def mock_processing_document(test_processing_document):
    """Backward compatibility - use test_processing_document instead."""
    return test_processing_document


@pytest_asyncio.fixture
async def mock_completed_document(test_on_chain_document):
    """Backward compatibility - use test_on_chain_document instead."""
    return test_on_chain_document


# ============================================================================
# Factory class fixtures for direct use in tests
# ============================================================================

@pytest.fixture
def user_factory():
    """Provide UserFactory class for creating users in tests."""
    return UserFactory


@pytest.fixture
def document_factory():
    """Provide DocumentFactory class for creating documents in tests."""
    return DocumentFactory


@pytest.fixture
def api_key_factory():
    """Provide ApiKeyFactory class for creating API keys in tests."""
    return ApiKeyFactory
