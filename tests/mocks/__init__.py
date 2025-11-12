"""
Mock implementations for abs_worker external dependencies.

This package provides mock versions of abs_orm, abs_blockchain, and abs_utils
for testing and running examples without real dependencies.
"""

from .mock_orm import (
    MockDocument,
    MockDocumentRepository,
    DocStatus,
    DocType,
    get_session,
    create_mock_document,
    create_mock_nft_document,
)
from .mock_blockchain import (
    MockBlockchain,
    BlockchainException,
    InsufficientFundsException,
    ContractRevertedException,
    GasEstimationException,
    NetworkTimeoutException,
    create_successful_blockchain,
    create_failing_blockchain,
    create_timeout_blockchain,
)
from .mock_utils import (
    get_logger,
    MockLogger,
    MockException,
    ValidationError,
    ConfigurationError,
    create_test_logger,
    create_test_exception,
)
from .factories import (
    create_document,
    create_hash_document,
    create_nft_document,
    create_processing_document,
    create_completed_document,
    create_failed_document,
    create_document_repository,
    create_populated_repository,
    create_blockchain_with_transactions,
    get_standard_test_documents,
    get_test_document_sets,
)

__all__ = [
    # ORM mocks
    "MockDocument",
    "MockDocumentRepository",
    "DocStatus",
    "DocType",
    "get_session",
    "create_mock_document",
    "create_mock_nft_document",
    # Blockchain mocks
    "MockBlockchain",
    "BlockchainException",
    "InsufficientFundsException",
    "ContractRevertedException",
    "GasEstimationException",
    "NetworkTimeoutException",
    "create_successful_blockchain",
    "create_failing_blockchain",
    "create_timeout_blockchain",
    # Utils mocks
    "get_logger",
    "MockLogger",
    "MockException",
    "ValidationError",
    "ConfigurationError",
    "create_test_logger",
    "create_test_exception",
    # Factories
    "create_document",
    "create_hash_document",
    "create_nft_document",
    "create_processing_document",
    "create_completed_document",
    "create_failed_document",
    "create_document_repository",
    "create_populated_repository",
    "create_blockchain_with_transactions",
    "get_standard_test_documents",
    "get_test_document_sets",
]
