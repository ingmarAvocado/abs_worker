"""
Mock implementations of abs_orm interfaces for testing and examples.

This module provides drop-in replacements for abs_orm components that can be used
in tests and examples without requiring a real database.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import AsyncContextManager, Dict, Optional
from unittest.mock import AsyncMock


class DocStatus(str, Enum):
    """Document status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    ON_CHAIN = "on_chain"
    ERROR = "error"


class DocType(str, Enum):
    """Document type enumeration"""
    HASH = "hash"
    NFT = "nft"


@dataclass
class MockDocument:
    """Mock Document model matching abs_orm.Document interface"""
    id: int
    file_name: str
    file_hash: str
    file_path: str
    status: DocStatus
    type: DocType
    transaction_hash: Optional[str] = None
    arweave_file_url: Optional[str] = None
    arweave_metadata_url: Optional[str] = None
    nft_token_id: Optional[int] = None
    error_message: Optional[str] = None
    owner_id: int = 1
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class MockDocumentRepository:
    """Mock DocumentRepository matching abs_orm.DocumentRepository interface"""

    def __init__(self):
        self.documents: Dict[int, MockDocument] = {}
        self.next_id = 1

    async def get(self, doc_id: int) -> Optional[MockDocument]:
        """Get document by ID"""
        return self.documents.get(doc_id)

    async def update(self, doc_id: int, **kwargs) -> MockDocument:
        """Update document fields and return updated document"""
        if doc_id not in self.documents:
            raise ValueError(f"Document {doc_id} not found")

        doc = self.documents[doc_id]
        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
            else:
                raise AttributeError(f"Document has no attribute '{key}'")

        return doc

    async def create(self, doc_data: dict) -> MockDocument:
        """Create new document and return it"""
        doc_id = self.next_id
        self.next_id += 1

        # Set defaults for required fields
        doc_data.setdefault('status', DocStatus.PENDING)
        doc_data.setdefault('type', DocType.HASH)
        doc_data.setdefault('owner_id', 1)

        doc = MockDocument(id=doc_id, **doc_data)
        self.documents[doc_id] = doc
        return doc


class MockAsyncSession:
    """Mock async database session"""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        """Commit transaction"""
        self.committed = True

    async def rollback(self):
        """Rollback transaction"""
        self.rolled_back = True

    async def close(self):
        """Close session"""
        pass


@asynccontextmanager
async def get_session():
    """Mock async context manager for database sessions"""
    session = MockAsyncSession()
    try:
        yield session
    finally:
        await session.close()


# Convenience functions for creating test data
def create_mock_document(**overrides) -> MockDocument:
    """Create a mock document with test defaults + overrides"""
    defaults = {
        'id': 1,
        'file_name': 'test.pdf',
        'file_hash': '0xabc123def456',
        'file_path': '/tmp/test.pdf',
        'status': DocStatus.PENDING,
        'type': DocType.HASH,
        'owner_id': 1,
    }
    defaults.update(overrides)
    return MockDocument(**defaults)


def create_mock_nft_document(**overrides) -> MockDocument:
    """Create a mock NFT document with test defaults + overrides"""
    defaults = {
        'id': 2,
        'file_name': 'nft.png',
        'file_hash': '0xdef456abc789',
        'file_path': '/tmp/nft.png',
        'status': DocStatus.PENDING,
        'type': DocType.NFT,
        'owner_id': 1,
    }
    defaults.update(overrides)
    return MockDocument(**defaults)