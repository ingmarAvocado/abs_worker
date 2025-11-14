"""
Example 2: NFT Minting with Arweave Storage

This example demonstrates:
- Complete NFT minting workflow using abs_worker
- File upload to Arweave
- Metadata creation and upload
- NFT minting on blockchain
- Certificate generation
- Error handling and status transitions

Note: This example uses mocks instead of real dependencies to demonstrate
the interface contracts defined in tests/mocks/README.md
"""

import asyncio
import json
import tempfile
import os
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

    async def mark_as_on_chain(
        self,
        doc_id: int,
        transaction_hash: str,
        signed_json_path: str,
        signed_pdf_path: str,
        arweave_file_url: Optional[str] = None,
        arweave_metadata_url: Optional[str] = None,
        nft_token_id: Optional[int] = None,
    ) -> MockDocument:
        """Mark document as on-chain with all details"""
        return await self.update(
            doc_id,
            status=DocStatus.ON_CHAIN,
            transaction_hash=transaction_hash,
            signed_json_path=signed_json_path,
            signed_pdf_path=signed_pdf_path,
            arweave_file_url=arweave_file_url,
            arweave_metadata_url=arweave_metadata_url,
            nft_token_id=nft_token_id,
        )

    async def create(self, doc_data: dict) -> MockDocument:
        """Create new document and return it"""
        doc_id = self.next_id
        self.next_id += 1

        # Set defaults for required fields
        doc_data.setdefault("status", DocStatus.PENDING)
        doc_data.setdefault("type", DocType.NFT)
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


class ArweaveUploadResult:
    """Mock result object returned by upload_to_arweave"""

    def __init__(self, url: str):
        self.url = url


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

    async def upload_to_arweave(self, file_data: bytes, content_type: str) -> ArweaveUploadResult:
        """Mock upload_to_arweave - returns ArweaveUploadResult object"""
        import random

        arweave_id = f"{random.randint(100000, 999999)}"
        url = f"https://arweave.net/{arweave_id}"
        return ArweaveUploadResult(url)

    async def mint_nft(
        self, owner_address: str, token_id: int, metadata_url: str
    ) -> NotarizationResult:
        """Mock mint_nft - returns NotarizationResult object"""
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

        return NotarizationResult(tx_hash)

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


def create_nft_document(**overrides) -> MockDocument:
    """Create a mock NFT document with test defaults + overrides"""
    defaults = {
        "id": 1,
        "file_name": "digital_artwork.png",
        "file_hash": "0xdef456abc789",
        "file_path": "/tmp/artwork.png",
        "status": DocStatus.PENDING,
        "type": DocType.NFT,
        "owner_id": 1,
    }
    defaults.update(overrides)
    return MockDocument(**defaults)


async def nft_minting_workflow():
    """
    Demonstrate complete NFT minting workflow using abs_worker
    """
    print("=== NFT Minting Workflow Example ===\n")

    from abs_worker.notarization import process_nft_notarization

    # Use inline mocks defined at the top of this file
    # (DocStatus, DocType, MockDocumentRepository, MockBlockchain, etc.)

    logger = get_logger("nft_example")

    # Create a document repository and add a test NFT document
    repo = MockDocumentRepository()

    # Create a temporary file to simulate the NFT artwork
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(b"Fake PNG image data for NFT")
        temp_file_path = tmp.name

    try:
        doc = await repo.create(
            {
                "file_name": "digital_artwork.png",
                "file_hash": "0xabcdef123456789",
                "file_path": temp_file_path,
                "type": DocType.NFT,
            }
        )
        print(f"Created NFT document: {doc.file_name} (ID: {doc.id})")
        print(f"Initial status: {doc.status.value}")
        print(f"Document type: {doc.type.value}\n")

        # Mock the blockchain and other dependencies for demonstration
        blockchain = MockBlockchain()

        # Simulate the workflow (in real usage, this would be called from FastAPI background task)
        print("Starting NFT minting process...")
        logger.info("Beginning NFT minting workflow", extra={"doc_id": doc.id})

        try:
            # This would normally be called as: await process_nft_notarization(doc.id)
            # But for demo purposes, we'll simulate the steps

            # Step 1: Update status to PROCESSING
            updated_doc = await repo.update(doc.id, status=DocStatus.PROCESSING)
            print(f"✓ Status updated to: {updated_doc.status.value}")

            # Step 2: Read file from storage
            with open(doc.file_path, "rb") as f:
                file_data = f.read()
            print(f"✓ Read file from storage: {len(file_data)} bytes")

            # Step 3: Upload file to Arweave
            file_result = await blockchain.upload_to_arweave(file_data, "image/png")
            file_url = file_result.url
            print(f"✓ File uploaded to Arweave: {file_url}")

            # Step 4: Create NFT metadata
            metadata = {
                "name": doc.file_name,
                "description": f"Notarized digital artwork: {doc.file_name}",
                "file_hash": doc.file_hash,
                "file_url": file_url,
                "timestamp": doc.created_at.isoformat()
                if doc.created_at
                else datetime.now(UTC).isoformat(),
                "blockchain_proof": {
                    "chain": "polygon",
                    "notarization_type": "nft",
                },
            }
            print(f"✓ Created NFT metadata: {metadata['name']}")

            # Step 5: Upload metadata to Arweave
            metadata_json = json.dumps(metadata, indent=2).encode()
            metadata_result = await blockchain.upload_to_arweave(metadata_json, "application/json")
            metadata_url = metadata_result.url
            print(f"✓ Metadata uploaded to Arweave: {metadata_url}")

            # Step 6: Mint NFT
            owner_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"  # Mock owner
            token_id = doc.id
            result = await blockchain.mint_nft(owner_address, token_id, metadata_url)
            tx_hash = result.transaction_hash
            print(f"✓ NFT minted on blockchain: {tx_hash}")

            # Step 7: Monitor transaction (simulated)
            print("✓ Transaction confirmed")

            # Step 8: Generate certificates (simulated)
            json_path = f"/certs/{doc.id}.json"
            pdf_path = f"/certs/{doc.id}.pdf"
            print(f"✓ Certificates generated: {json_path}, {pdf_path}")

            # Step 9: Mark as on-chain with NFT details
            final_doc = await repo.mark_as_on_chain(
                doc.id,
                transaction_hash=tx_hash,
                signed_json_path=json_path,
                signed_pdf_path=pdf_path,
                arweave_file_url=file_url,
                arweave_metadata_url=metadata_url,
                nft_token_id=token_id,
            )

            print(f"\n✓ NFT minting completed successfully!")
            print(f"✓ Final status: {final_doc.status.value}")
            print(f"✓ Transaction hash: {final_doc.transaction_hash}")
            print(f"✓ NFT Token ID: {final_doc.nft_token_id}")
            print(f"✓ Arweave file URL: {final_doc.arweave_file_url}")
            print(f"✓ Arweave metadata URL: {final_doc.arweave_metadata_url}")
            print(f"✓ JSON certificate: {final_doc.signed_json_path}")
            print(f"✓ PDF certificate: {final_doc.signed_pdf_path}")

            logger.info(
                "NFT minting completed successfully", extra={"doc_id": doc.id, "token_id": token_id}
            )

        except Exception as e:
            print(f"✗ Error during NFT minting: {e}")
            logger.error("NFT minting failed", extra={"doc_id": doc.id, "error": str(e)})

    finally:
        # Clean up temp file
        os.unlink(temp_file_path)


async def opensea_metadata_example():
    """
    Demonstrate OpenSea-compatible NFT metadata creation
    """
    print("=== OpenSea-Compatible NFT Metadata Example ===\n")

    # Create comprehensive NFT metadata following OpenSea standards
    opensea_metadata = {
        "name": "Digital Artwork Certificate",
        "description": "This NFT represents ownership of a digitally notarized artwork with blockchain proof of authenticity",
        "image": "https://arweave.net/123456",  # Arweave URL to the artwork
        "external_url": "https://notary.example.com/certificates/123",
        "attributes": [
            {"trait_type": "Notarization Type", "value": "NFT"},
            {"trait_type": "Blockchain", "value": "Polygon"},
            {"trait_type": "File Hash", "value": "0xabcdef123456789"},
            {"trait_type": "Timestamp", "value": "2024-01-01T12:00:00Z"},
        ],
        "file_hash": "0xabcdef123456789",
        "timestamp": "2024-01-01T12:00:00Z",
        "blockchain_proof": {
            "chain": "polygon",
            "transaction_hash": "0x123456789abcdef",
            "block_number": 12345678,
            "notarization_type": "nft",
        },
    }

    print("OpenSea-compatible NFT metadata:")
    print(json.dumps(opensea_metadata, indent=2))
    print()


async def error_scenarios():
    """
    Demonstrate error handling in NFT minting
    """
    print("=== NFT Minting Error Scenarios ===\n")

    logger = get_logger("error_example")

    # Simulate Arweave upload failure
    print("1. Arweave Upload Failure:")
    try:
        # This would trigger error handling in real implementation
        raise Exception("Arweave upload failed: network timeout")
    except Exception as e:
        print(f"   Error: {e}")
        print("   → Document status would be set to ERROR")
        print("   → Retry logic would attempt again with backoff")
        logger.error("Arweave upload failed", extra={"error": str(e)})

    # Simulate NFT minting failure
    print("\n2. NFT Minting Failure:")
    try:
        raise Exception("NFT minting failed: insufficient funds")
    except Exception as e:
        print(f"   Error: {e}")
        print("   → Document status would be set to ERROR")
        print("   → User would be notified of permanent failure")
        logger.error("NFT minting failed", extra={"error": str(e)})

    # Simulate transaction monitoring timeout
    print("\n3. Transaction Monitoring Timeout:")
    try:
        raise Exception("Transaction monitoring timeout: no confirmations after 10 minutes")
    except Exception as e:
        print(f"   Error: {e}")
        print("   → Document status would be set to ERROR")
        print("   → Manual intervention might be required")
        logger.error("Transaction monitoring failed", extra={"error": str(e)})

    print()


async def integration_with_fastapi():
    """
    Show how NFT minting integrates with FastAPI BackgroundTasks
    """
    print("=== FastAPI Integration Example ===\n")

    print("FastAPI endpoint for NFT minting:")
    print(
        """
from fastapi import FastAPI, BackgroundTasks, HTTPException
from abs_worker import process_nft_notarization

app = FastAPI()

@app.post("/documents/{doc_id}/mint-nft")
async def mint_nft(doc_id: int, background_tasks: BackgroundTasks):
    '''
    Mint an NFT for the specified document.

    This endpoint:
    1. Validates document ownership and status
    2. Updates document type to NFT
    3. Enqueues background NFT minting task
    4. Returns immediate response to user
    '''
    # Validate document exists and user owns it
    # ... validation logic ...

    # Enqueue background task
    background_tasks.add_task(process_nft_notarization, doc_id)

    return {
        "status": "processing",
        "message": "NFT minting started. Check status endpoint for updates.",
        "doc_id": doc_id
    }

@app.get("/documents/{doc_id}/status")
async def get_document_status(doc_id: int):
    '''
    Get current document processing status.

    Returns status information including:
    - Current status (pending/processing/on_chain/error)
    - Transaction hash (when available)
    - NFT token ID (when minted)
    - Arweave URLs (when uploaded)
    - Error message (if failed)
    '''
    # Get document from database
    # ... database query ...

    return {
        "doc_id": doc_id,
        "status": "on_chain",  # Example
        "transaction_hash": "0x123...",
        "nft_token_id": 456,
        "arweave_file_url": "https://arweave.net/123",
        "arweave_metadata_url": "https://arweave.net/456"
    }
"""
    )

    print("Key integration points:")
    print("• BackgroundTasks.add_task() for async processing")
    print("• Immediate response prevents API timeouts")
    print("• Status endpoint for progress tracking")
    print("• Error handling preserves user experience")
    print()


async def main():
    """
    Run all NFT minting examples
    """
    print("NFT Minting Examples")
    print("=" * 50)

    await nft_minting_workflow()
    await opensea_metadata_example()
    await error_scenarios()
    await integration_with_fastapi()

    print("\n✓ All NFT examples completed successfully!")
    print("\nNote: These examples use mock implementations.")
    print("In production, replace 'tests.mocks.*' imports with real dependencies:")
    print("- tests.mocks.mock_orm → abs_orm")
    print("- tests.mocks.mock_blockchain → abs_blockchain")
    print("- tests.mocks.mock_utils → abs_utils")


if __name__ == "__main__":
    asyncio.run(main())
