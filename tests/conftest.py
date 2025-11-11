"""
Pytest configuration and shared fixtures for abs_worker tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from abs_worker.config import WorkerSettings


@pytest.fixture
def worker_settings():
    """Provide test configuration settings"""
    return WorkerSettings(
        required_confirmations=2,
        max_confirmation_wait=60,
        max_retries=2,
        retry_delay=1,
        retry_backoff_multiplier=1.5,
        poll_interval=1,
        max_poll_attempts=10,
        cert_storage_path="/tmp/test_certs",
        cert_json_enabled=True,
        cert_pdf_enabled=True,
        worker_name="test_worker",
        enable_structured_logging=False,
    )


@pytest.fixture
def mock_document():
    """Provide a mock Document object"""
    doc = MagicMock()
    doc.id = 123
    doc.file_name = "test.pdf"
    doc.file_hash = "0xabc123def456"
    doc.file_path = "/tmp/test.pdf"
    doc.type = MagicMock(value="hash")
    doc.status = MagicMock(value="pending")
    doc.transaction_hash = None
    doc.owner_id = 1
    doc.created_at = MagicMock()
    doc.created_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00Z")
    return doc


@pytest.fixture
def mock_nft_document():
    """Provide a mock NFT Document object"""
    doc = MagicMock()
    doc.id = 456
    doc.file_name = "nft.png"
    doc.file_hash = "0xdef456abc789"
    doc.file_path = "/tmp/nft.png"
    doc.type = MagicMock(value="nft")
    doc.status = MagicMock(value="pending")
    doc.transaction_hash = None
    doc.arweave_file_url = None
    doc.arweave_metadata_url = None
    doc.nft_token_id = None
    doc.owner_id = 1
    doc.owner = MagicMock()
    doc.owner.eth_address = "0x1234567890abcdef"
    doc.created_at = MagicMock()
    doc.created_at.isoformat = MagicMock(return_value="2024-01-01T00:00:00Z")
    return doc


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
    repo = AsyncMock()
    repo.get = AsyncMock()
    repo.update_status = AsyncMock()
    repo.mark_as_on_chain = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
async def mock_blockchain():
    """Provide mock blockchain functions"""
    class MockBlockchain:
        async def record_hash(self, file_hash, metadata):
            return "0xabc123"

        async def mint_nft(self, to_address, token_id, metadata_uri):
            return "0xdef456"

        async def upload_to_arweave(self, data, content_type):
            return "https://arweave.net/mock123"

        async def get_transaction_receipt(self, tx_hash):
            return {
                "transactionHash": tx_hash,
                "blockNumber": 12345,
                "status": 1,
            }

        async def get_latest_block_number(self):
            return 12350

    return MockBlockchain()


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings between tests"""
    from abs_worker.config import _settings
    # Reset global settings
    yield
    # Cleanup after test
