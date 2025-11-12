"""
Example 1: Basic usage with mock dependencies

This example demonstrates:
- Using mock dependencies for testing and development
- Basic document operations with MockDocumentRepository
- Mock blockchain interactions
- Structured logging with mock logger

Note: This example uses mocks instead of real dependencies to demonstrate
the interface contracts defined in tests/mocks/README.md
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, Optional, Any


# Inline mock implementations for standalone execution
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
    signed_json_path: Optional[str] = None
    signed_pdf_path: Optional[str] = None
    owner_id: int = 1
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)


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
        doc_data.setdefault("status", DocStatus.PENDING)
        doc_data.setdefault("type", DocType.HASH)
        doc_data.setdefault("owner_id", 1)

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


class NotarizationResult:
    """Mock result object returned by notarize_hash"""

    def __init__(self, transaction_hash: str):
        self.transaction_hash = transaction_hash


class MockBlockchain:
    """Mock blockchain interface matching abs_blockchain interface"""

    def __init__(self):
        self.transactions: Dict[str, Dict[str, Any]] = {}
        self.next_tx_id = 1000
        self.current_block = 12345678

    async def notarize_hash(self, file_hash: str, metadata: dict) -> NotarizationResult:
        """Mock notarize_hash - returns NotarizationResult object"""
        tx_hash = f"0x{self.next_tx_id:064x}"
        self.next_tx_id += 1

        self.transactions[tx_hash] = {
            "type": "record_hash",
            "file_hash": file_hash,
            "metadata": metadata,
            "block_number": self.current_block,
            "status": 1,  # Success
        }

        return NotarizationResult(tx_hash)

    async def record_hash(self, file_hash: str, metadata: dict) -> str:
        """Mock record_hash - returns fake transaction hash"""
        result = await self.notarize_hash(file_hash, metadata)
        return result.transaction_hash

    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Mock get_transaction_receipt"""
        if tx_hash not in self.transactions:
            return {
                "transactionHash": tx_hash,
                "blockNumber": None,
                "status": 0,  # Not found
                "confirmations": 0,
            }

        tx = self.transactions[tx_hash]
        confirmations = min(3, self.current_block - tx["block_number"])

        return {
            "transactionHash": tx_hash,
            "blockNumber": tx["block_number"],
            "blockHash": f"0xblock{tx['block_number']:064x}",
            "status": tx["status"],
            "confirmations": confirmations,
            "gasUsed": 50000,
            "from": "0xmock_sender",
            "to": "0xmock_contract",
        }

    async def upload_to_arweave(self, file_data: bytes, content_type: str) -> str:
        """Mock upload_to_arweave"""
        import random

        arweave_id = f"{random.randint(100000, 999999)}"
        return f"https://arweave.net/{arweave_id}"

    async def mint_nft(self, owner_address: str, token_id: int, metadata_url: str) -> str:
        """Mock mint_nft"""
        tx_hash = f"0x{self.next_tx_id:064x}"
        self.next_tx_id += 1

        self.transactions[tx_hash] = {
            "type": "mint_nft",
            "owner_address": owner_address,
            "token_id": token_id,
            "metadata_url": metadata_url,
            "block_number": self.current_block,
            "status": 1,  # Success
        }

        return tx_hash


class MockLogger:
    """Mock logger for standalone execution"""

    def __init__(self, name: str):
        self.name = name

    def info(self, message: str, extra: Optional[Dict] = None):
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        extra_str = f" | {extra}" if extra else ""
        print(f"{timestamp} - {self.name} - INFO - {message}{extra_str}")

    def error(self, message: str, extra: Optional[Dict] = None):
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        extra_str = f" | {extra}" if extra else ""
        print(f"{timestamp} - {self.name} - ERROR - {message}{extra_str}")

    def warning(self, message: str, extra: Optional[Dict] = None):
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        extra_str = f" | {extra}" if extra else ""
        print(f"{timestamp} - {self.name} - WARNING - {message}{extra_str}")


def get_logger(name: str) -> MockLogger:
    """Get a mock logger instance"""
    return MockLogger(name)


def create_hash_document(**overrides) -> MockDocument:
    """Create a mock hash document with test defaults + overrides"""
    defaults = {
        "id": 1,
        "file_name": "test.pdf",
        "file_hash": "0xabc123def456",
        "file_path": "/tmp/test.pdf",
        "status": DocStatus.PENDING,
        "type": DocType.HASH,
        "owner_id": 1,
    }
    defaults.update(overrides)
    return MockDocument(**defaults)


async def basic_document_operations():
    """
    Demonstrate basic document repository operations using mocks
    """
    print("=== Basic Document Operations Example ===\n")

    logger = get_logger("example_01")
    logger.info("Starting basic operations example")

    # Create repository and add some documents
    repo = MockDocumentRepository()

    # Create a hash document
    hash_doc = create_hash_document(id=1, file_name="contract.pdf", file_hash="0xabcdef123456")

    # Add to repository
    repo.documents[1] = hash_doc
    logger.info("Created hash document", extra={"doc_id": 1, "file_name": "contract.pdf"})

    # Retrieve document
    retrieved = await repo.get(1)
    if retrieved:
        print(f"Retrieved document: {retrieved.file_name}")
        print(f"Status: {retrieved.status.value}")
        print(f"Type: {retrieved.type.value}\n")
    else:
        print("Document not found\n")

    # Update document status
    updated = await repo.update(1, status=DocStatus.PROCESSING)
    print(f"Updated status to: {updated.status.value}")
    logger.info("Document status updated", extra={"doc_id": 1, "new_status": "processing"})

    # Create document via repository
    new_doc = await repo.create(
        {"file_name": "report.pdf", "file_hash": "0xfedcba654321", "file_path": "/tmp/report.pdf"}
    )
    print(f"Created new document with ID: {new_doc.id}")
    print(f"Total documents in repo: {len(repo.documents)}\n")


async def mock_blockchain_operations():
    """
    Demonstrate mock blockchain operations
    """
    print("=== Mock Blockchain Operations Example ===\n")

    logger = get_logger("blockchain_example")
    blockchain = MockBlockchain()

    # Record hash on blockchain
    file_hash = "0xabcdef123456789"
    metadata = {"doc_id": 123, "timestamp": "2024-01-01T12:00:00Z"}

    tx_hash = await blockchain.record_hash(file_hash, metadata)
    print(f"Recorded hash, transaction: {tx_hash}")
    logger.info("Hash recorded on blockchain", extra={"tx_hash": tx_hash, "file_hash": file_hash})

    # Get transaction receipt
    receipt = await blockchain.get_transaction_receipt(tx_hash)
    print(f"Transaction status: {receipt['status']}")
    print(f"Block number: {receipt['blockNumber']}")
    print(f"Confirmations: {receipt['confirmations']}\n")

    # Upload to Arweave
    file_data = b"Sample PDF content"
    arweave_url = await blockchain.upload_to_arweave(file_data, "application/pdf")
    print(f"Uploaded to Arweave: {arweave_url}\n")

    # Mint NFT
    nft_tx = await blockchain.mint_nft(
        owner_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        token_id=1,
        metadata_url=arweave_url,
    )
    print(f"NFT minted, transaction: {nft_tx}")
    logger.info("NFT minted", extra={"tx_hash": nft_tx, "token_id": 1})


async def error_handling_example():
    """
    Demonstrate error handling with mock exceptions
    """
    print("=== Error Handling Example ===\n")

    from tests.mocks.mock_utils import ValidationError, ConfigurationError

    logger = get_logger("error_example")

    try:
        # Simulate validation error
        raise ValidationError("Invalid email format", "email")
    except ValidationError as e:
        print(f"Validation error: {e}")
        print(f"Error dict: {e.to_dict()}")
        logger.error("Validation failed", extra=e.to_dict())

    try:
        # Simulate configuration error
        raise ConfigurationError("Database connection failed", "db_url")
    except ConfigurationError as e:
        print(f"Configuration error: {e}")
        print(f"Error dict: {e.to_dict()}")
        logger.error("Configuration error", extra=e.to_dict())


async def hash_notarization_workflow():
    """
    Demonstrate complete hash notarization workflow using abs_worker
    """
    print("=== Hash Notarization Workflow Example ===\n")

    from abs_worker.notarization import process_hash_notarization
    from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, DocType, get_session
    from tests.mocks.mock_blockchain import MockBlockchain
    from tests.mocks.mock_utils import get_logger

    logger = get_logger("notarization_example")

    # Create a document repository and add a test document
    repo = MockDocumentRepository()
    doc = await repo.create(
        {
            "file_name": "contract.pdf",
            "file_hash": "0xabcdef123456789",
            "file_path": "/tmp/contract.pdf",
        }
    )
    print(f"Created document: {doc.file_name} (ID: {doc.id})")
    print(f"Initial status: {doc.status.value}\n")

    # Mock the blockchain and other dependencies for demonstration
    # In real usage, these would be the actual abs_* libraries
    blockchain = MockBlockchain()

    # Simulate the workflow (in real usage, this would be called from FastAPI background task)
    print("Starting hash notarization process...")
    logger.info("Beginning hash notarization workflow", extra={"doc_id": doc.id})

    try:
        # This would normally be called as: await process_hash_notarization(doc.id)
        # But for demo purposes, we'll simulate the steps

        # Step 1: Update status to PROCESSING
        updated_doc = await repo.update(doc.id, status=DocStatus.PROCESSING)
        print(f"✓ Status updated to: {updated_doc.status.value}")

        # Step 2: Record hash on blockchain
        timestamp = doc.created_at.isoformat() if doc.created_at else datetime.now(UTC).isoformat()
        result = await blockchain.notarize_hash(
            file_hash=doc.file_hash,
            metadata={"file_name": doc.file_name, "timestamp": timestamp},
        )
        tx_hash = result.transaction_hash
        print(f"✓ Hash recorded on blockchain: {tx_hash}")

        # Step 3: Monitor transaction (simulated)
        print("✓ Transaction confirmed")

        # Step 4: Generate certificates (simulated)
        json_path = f"/certs/{doc.id}.json"
        pdf_path = f"/certs/{doc.id}.pdf"
        print(f"✓ Certificates generated: {json_path}, {pdf_path}")

        # Step 5: Mark as on-chain
        final_doc = await repo.update(
            doc.id,
            status=DocStatus.ON_CHAIN,
            transaction_hash=tx_hash,
            signed_json_path=json_path,
            signed_pdf_path=pdf_path,
        )

        print(f"✓ Final status: {final_doc.status.value}")
        print(f"✓ Transaction hash: {final_doc.transaction_hash}")
        print(f"✓ JSON certificate: {final_doc.signed_json_path}")
        print(f"✓ PDF certificate: {final_doc.signed_pdf_path}")

        logger.info("Hash notarization completed successfully", extra={"doc_id": doc.id})

    except Exception as e:
        print(f"✗ Error during notarization: {e}")
        logger.error("Notarization failed", extra={"doc_id": doc.id, "error": str(e)})


async def session_context_example():
    """
    Demonstrate database session usage
    """
    print("=== Database Session Example ===\n")

    logger = get_logger("session_example")

    async with get_session() as session:
        print("Session opened")
        logger.info("Database session started")

        # Simulate some database operations
        await session.commit()
        print("Session committed")

        # Session will be closed automatically
        logger.info("Database operations completed")


async def main():
    """
    Run all examples
    """
    print("Mock Dependencies Examples")
    print("=" * 50)

    await basic_document_operations()
    await mock_blockchain_operations()
    await hash_notarization_workflow()
    await error_handling_example()
    await session_context_example()

    print("\n✓ All examples completed successfully!")
    print("\nNote: These examples use mock implementations.")
    print("In production, replace 'tests.mocks.*' imports with real dependencies:")
    print("- tests.mocks.mock_orm → abs_orm")
    print("- tests.mocks.mock_blockchain → abs_blockchain")
    print("- tests.mocks.mock_utils → abs_utils")


if __name__ == "__main__":
    asyncio.run(main())
