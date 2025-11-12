"""
Pytest configuration and shared fixtures for abs_worker tests
"""

import pytest
from unittest.mock import AsyncMock
from abs_worker.config import Settings

# Import mock implementations
from tests.mocks import (
    MockBlockchain,
    DocStatus,
    DocType,
    get_session,
    create_hash_document,
    create_nft_document,
    create_processing_document,
    create_completed_document,
    create_failed_document,
    create_document_repository,
    create_populated_repository,
    get_logger,
)


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


@pytest.fixture
def mock_document():
    """Provide a mock Document object"""
    return create_hash_document(
        id=123,
        file_name="test.pdf",
        file_hash="0xabc123def456",
        file_path="/tmp/test.pdf",
        status=DocStatus.PENDING,
        type=DocType.HASH,
    )


@pytest.fixture
def mock_nft_document():
    """Provide a mock NFT Document object"""
    return create_nft_document(
        id=456,
        file_name="nft.png",
        file_hash="0xdef456abc789",
        file_path="/tmp/nft.png",
        status=DocStatus.PENDING,
        type=DocType.NFT,
    )


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


@pytest.fixture
def mock_db_session():
    """Provide a mock database session"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_document_repository():
    """Provide a mock DocumentRepository"""
    return create_document_repository()


@pytest.fixture
async def mock_blockchain():
    """Provide mock blockchain interface"""
    return MockBlockchain()


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing"""
    return get_logger("test")


@pytest.fixture
def mock_session():
    """Provide a mock database session context manager"""
    return get_session()


@pytest.fixture
def mock_processing_document():
    """Provide a document in processing status"""
    return create_processing_document(id=789)


@pytest.fixture
def mock_completed_document():
    """Provide a document in completed status"""
    return create_completed_document(id=101)


@pytest.fixture
def mock_failed_document():
    """Provide a document in error status"""
    return create_failed_document(id=202)


@pytest.fixture
def populated_document_repository():
    """Provide a repository with some test documents"""
    return create_populated_repository(count=3)


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings cache between tests"""
    from abs_worker.config import get_settings

    # Clear the LRU cache before each test
    get_settings.cache_clear()
    yield
    # Clear the LRU cache after each test
    get_settings.cache_clear()
