"""
Factory functions for creating test data and mock objects.

This module provides convenient factory functions for creating mock documents,
blockchain objects, and other test data with sensible defaults.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from .mock_orm import MockDocument, MockDocumentRepository, DocStatus, DocType
from .mock_blockchain import MockBlockchain


def create_document(
    id: int = 1,
    file_name: str = "test.pdf",
    file_hash: str = "0xabc123def456789",
    file_path: str = "/tmp/test.pdf",
    status: DocStatus = DocStatus.PENDING,
    type: DocType = DocType.HASH,
    transaction_hash: Optional[str] = None,
    arweave_file_url: Optional[str] = None,
    arweave_metadata_url: Optional[str] = None,
    nft_token_id: Optional[int] = None,
    error_message: Optional[str] = None,
    owner_id: int = 1,
    created_at: Optional[datetime] = None,
    **overrides: Any
) -> MockDocument:
    """Create a mock document with customizable defaults"""

    data = {
        'id': id,
        'file_name': file_name,
        'file_hash': file_hash,
        'file_path': file_path,
        'status': status,
        'type': type,
        'transaction_hash': transaction_hash,
        'arweave_file_url': arweave_file_url,
        'arweave_metadata_url': arweave_metadata_url,
        'nft_token_id': nft_token_id,
        'error_message': error_message,
        'owner_id': owner_id,
        'created_at': created_at,
    }

    # Apply any overrides
    data.update(overrides)

    return MockDocument(**data)


def create_hash_document(**overrides: Any) -> MockDocument:
    """Create a mock hash-type document"""
    defaults = {
        'file_name': 'contract.pdf',
        'file_hash': '0xhash123456789abcdef',
        'file_path': '/tmp/contract.pdf',
        'type': DocType.HASH,
    }
    defaults.update(overrides)
    return create_document(**defaults)


def create_nft_document(**overrides: Any) -> MockDocument:
    """Create a mock NFT-type document"""
    defaults = {
        'file_name': 'artwork.png',
        'file_hash': '0xnft987654321fedcba',
        'file_path': '/tmp/artwork.png',
        'type': DocType.NFT,
    }
    defaults.update(overrides)
    return create_document(**defaults)


def create_processing_document(**overrides: Any) -> MockDocument:
    """Create a mock document in processing status"""
    return create_document(status=DocStatus.PROCESSING, **overrides)


def create_completed_document(**overrides: Any) -> MockDocument:
    """Create a mock document in on_chain status"""
    return create_document(status=DocStatus.ON_CHAIN, transaction_hash='0xcompleted_tx_123', **overrides)


def create_failed_document(**overrides: Any) -> MockDocument:
    """Create a mock document in error status"""
    return create_document(status=DocStatus.ERROR, error_message='Mock processing error', **overrides)


def create_document_repository(documents: Optional[Dict[int, MockDocument]] = None) -> MockDocumentRepository:
    """Create a mock document repository with optional initial documents"""
    repo = MockDocumentRepository()
    if documents:
        repo.documents = documents.copy()
        # Update next_id to avoid conflicts
        if documents:
            repo.next_id = max(documents.keys()) + 1
    return repo


def create_populated_repository(count: int = 5) -> MockDocumentRepository:
    """Create a repository with some test documents"""
    repo = MockDocumentRepository()
    for i in range(1, count + 1):
        doc = create_document(id=i, file_name=f'document_{i}.pdf')
        repo.documents[i] = doc
        repo.next_id = i + 1
    return repo


def create_blockchain_with_transactions() -> MockBlockchain:
    """Create a blockchain mock with some existing transactions"""
    blockchain = MockBlockchain()

    # Simulate some existing transactions
    blockchain.transactions = {
        '0x0000000000000000000000000000000000000000000000000000000000001000': {
            'type': 'record_hash',
            'file_hash': '0xhash1',
            'metadata': {'doc_id': 1},
            'block_number': 12345670,
            'status': 1,
        },
        '0x0000000000000000000000000000000000000000000000000000000000001001': {
            'type': 'mint_nft',
            'owner_address': '0xowner1',
            'token_id': 1,
            'metadata_url': 'https://arweave.net/123',
            'block_number': 12345675,
            'status': 1,
        }
    }

    blockchain.next_tx_id = 0x1002
    return blockchain


# Convenience collections for testing
def get_standard_test_documents() -> Dict[str, MockDocument]:
    """Get a dict of standard test documents for different scenarios"""
    return {
        'pending_hash': create_hash_document(id=1, status=DocStatus.PENDING),
        'processing_nft': create_nft_document(id=2, status=DocStatus.PROCESSING),
        'completed_hash': create_completed_document(id=3),
        'failed_nft': create_failed_document(id=4, type=DocType.NFT),
    }


def get_test_document_sets() -> Dict[str, Dict[int, MockDocument]]:
    """Get different sets of test documents for various test scenarios"""
    return {
        'empty': {},
        'single_pending': {1: create_document(id=1)},
        'mixed_statuses': {i: doc for i, doc in enumerate(get_standard_test_documents().values(), 1)},
        'all_completed': {
            1: create_completed_document(id=1),
            2: create_completed_document(id=2, type=DocType.NFT),
        },
        'all_failed': {
            1: create_failed_document(id=1, type=DocType.HASH),
            2: create_failed_document(id=2, type=DocType.NFT),
        }
    }