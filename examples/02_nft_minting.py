"""
Example 2: NFT Minting with Automatic Arweave Storage

This example demonstrates:
- Complete NFT minting workflow using abs_worker
- ONE-CALL NFT minting with mint_nft_from_file() API ⭐
- Automatic file upload to Arweave (permanent storage)
- NFT minting on blockchain
- Certificate generation
- Error handling and status transitions
- High-level API vs. under-the-hood workflow

Key Insight: The new mint_nft_from_file() API handles Arweave upload
automatically, making NFT minting as simple as hash notarization!

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
    """Mock result object returned by notarize_hash and mint_nft_from_file"""

    def __init__(self, transaction_hash: str):
        self.transaction_hash = transaction_hash
        self.token_id: Optional[int] = None
        self.arweave_url: Optional[str] = None
        self.notarization_type: Optional[str] = None


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

    async def mint_nft_from_file(
        self, file_path: str, file_hash: str, metadata: dict
    ) -> NotarizationResult:
        """
        Mock mint_nft_from_file - ONE-CALL NFT minting with automatic Arweave upload

        This method simulates the simplified abs_blockchain API that:
        1. Uploads file to Arweave automatically
        2. Mints NFT with the Arweave URL as metadata
        3. Returns all details in one result object
        """
        import random

        tx_hash = f"0x{self.next_tx_id:064x}"
        self.next_tx_id += 1

        # Simulate automatic Arweave upload
        arweave_id = f"{random.randint(100000, 999999)}"
        arweave_url = f"https://arweave.net/{arweave_id}"

        # Simulate NFT minting
        token_id = random.randint(1, 10000)

        self.transactions[tx_hash] = {
            "type": "mint_nft_from_file",
            "file_hash": file_hash,
            "metadata": metadata,
            "block_number": self.current_block,
            "status": 1,  # Success
            "token_id": token_id,
            "arweave_url": arweave_url,
        }

        # Return comprehensive result
        result = NotarizationResult(tx_hash)
        result.token_id = token_id
        result.arweave_url = arweave_url
        result.notarization_type = "nft"

        return result

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

    Shows TWO perspectives:
    1. High-level: Just call process_nft_notarization(client, doc_id)
    2. Under-the-hood: What happens inside (for educational value)
    """
    print("=== NFT Minting Workflow Example ===\n")

    from abs_worker.notarization import process_nft_notarization

    logger = get_logger("nft_example")
    repo = MockDocumentRepository()
    blockchain = MockBlockchain()

    # Create test document
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
        print(f"Initial status: {doc.status.value}\n")

        # ═══════════════════════════════════════════════════════════
        # PERSPECTIVE 1: High-Level API (What Users See)
        # ═══════════════════════════════════════════════════════════
        print("🎯 HIGH-LEVEL API (Production Usage):")
        print("-" * 50)
        print("In production, just call process_nft_notarization():\n")
        print("```python")
        print("from abs_worker import process_nft_notarization")
        print("from abs_blockchain import BlockchainClient")
        print("")
        print("client = BlockchainClient()")
        print("await process_nft_notarization(client, doc_id)")
        print("```\n")
        print("That's it! One function call handles everything.\n")

        # ═══════════════════════════════════════════════════════════
        # PERSPECTIVE 2: Under-the-Hood (Educational - What Happens Inside)
        # ═══════════════════════════════════════════════════════════
        print("🔍 UNDER-THE-HOOD (Educational - What Happens Inside):")
        print("-" * 50)
        print("The process_nft_notarization() function does this:\n")

        try:
            # Step 1: Fetch and validate
            print("1. ✓ Fetch document and validate status")

            # Step 2: Update status
            updated_doc = await repo.update(doc.id, status=DocStatus.PROCESSING)
            print(f"2. ✓ Update status to: {updated_doc.status.value}")

            # Step 3: Prepare metadata
            metadata = {
                "name": doc.file_name,
                "description": f"Notarized digital artwork: {doc.file_name}",
                "file_hash": doc.file_hash,
                "timestamp": doc.created_at.isoformat()
                if doc.created_at
                else datetime.now(UTC).isoformat(),
                "attributes": [
                    {"trait_type": "Document Type", "value": "Artwork"},
                    {"trait_type": "File Hash", "value": doc.file_hash},
                    {"trait_type": "Blockchain", "value": "Polygon"},
                ],
            }
            print(f"3. ✓ Prepare NFT metadata (OpenSea compatible)")

            # Step 4: ONE-CALL NFT minting with automatic Arweave upload! ⭐
            print("\n4. ✓ Call mint_nft_from_file() - ONE CALL!")
            print("   (Automatically uploads file to Arweave + mints NFT)")

            # Simulate the simplified API call
            result = await blockchain.mint_nft_from_file(
                file_path=doc.file_path, file_hash=doc.file_hash, metadata=metadata
            )

            tx_hash = result.transaction_hash
            token_id = result.token_id
            arweave_url = result.arweave_url  # Automatically uploaded!

            print(f"   Transaction hash: {tx_hash}")
            print(f"   NFT Token ID: {token_id}")
            print(f"   Arweave URL: {arweave_url}")
            print("   ✨ File automatically stored on Arweave (permanent!)✨")

            # Step 5: Monitor transaction
            print("\n5. ✓ Monitor transaction until confirmed")
            print("   Waiting for 3 block confirmations...")
            print("   Transaction confirmed!")

            # Step 6: Generate certificates
            json_path = f"/certs/{doc.id}.json"
            pdf_path = f"/certs/{doc.id}.pdf"
            print(f"\n6. ✓ Generate signed certificates")
            print(f"   JSON: {json_path}")
            print(f"   PDF: {pdf_path}")

            # Step 7: Update document with all NFT details
            final_doc = await repo.mark_as_on_chain(
                doc.id,
                transaction_hash=tx_hash,
                signed_json_path=json_path,
                signed_pdf_path=pdf_path,
                arweave_file_url=arweave_url,
                nft_token_id=token_id,
            )
            print(f"\n7. ✓ Update document status to: {final_doc.status.value}")

            print("\n" + "=" * 50)
            print("✅ NFT MINTING COMPLETED SUCCESSFULLY!")
            print("=" * 50)
            print(f"Transaction Hash:     {final_doc.transaction_hash}")
            print(f"NFT Token ID:         {final_doc.nft_token_id}")
            print(f"Arweave File URL:     {final_doc.arweave_file_url}")
            print(f"JSON Certificate:     {final_doc.signed_json_path}")
            print(f"PDF Certificate:      {final_doc.signed_pdf_path}")
            print()

            print("🎯 KEY TAKEAWAY:")
            print("The magic is in mint_nft_from_file() - it handles:")
            print("  • File upload to Arweave (permanent storage)")
            print("  • NFT minting on blockchain")
            print("  • All in ONE asynchronous call!")
            print()

        except Exception as e:
            print(f"✗ Error during NFT minting: {e}")
            logger.error("NFT minting failed", extra={"doc_id": doc.id, "error": str(e)})

    finally:
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
from abs_blockchain import BlockchainClient

app = FastAPI()

# Initialize blockchain client (reuse across requests)
blockchain_client = BlockchainClient()

@app.post("/documents/{doc_id}/mint-nft")
async def mint_nft(doc_id: int, background_tasks: BackgroundTasks):
    '''
    Mint an NFT for the specified document.

    This endpoint:
    1. Validates document ownership and status
    2. Enqueues background NFT minting task (ONE CALL!)
    3. Returns immediate response to user

    The background task automatically:
    - Uploads file to Arweave (permanent storage)
    - Mints NFT on blockchain
    - Generates certificates
    - Updates document status
    '''
    # Validate document exists and user owns it
    # ... validation logic ...

    # Enqueue background task - ONE CALL! ⭐
    background_tasks.add_task(
        process_nft_notarization,
        blockchain_client,  # Dependency injection
        doc_id
    )

    return {
        "status": "processing",
        "message": "NFT minting started. File will be permanently stored on Arweave.",
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
    - Arweave file URL (permanent storage link)
    - Error message (if failed)
    '''
    # Get document from database
    # ... database query ...

    return {
        "doc_id": doc_id,
        "status": "on_chain",
        "transaction_hash": "0x123...",
        "nft_token_id": 456,
        "arweave_file_url": "https://arweave.net/abc123"  # Permanent link!
    }
"""
    )

    print("\nKey integration points:")
    print("• BackgroundTasks.add_task() for async processing")
    print("• Dependency injection: pass BlockchainClient to worker")
    print("• ONE function call: process_nft_notarization(client, doc_id)")
    print("• Automatic Arweave upload (no manual file handling!)")
    print("• Immediate response prevents API timeouts")
    print("• Status endpoint for progress tracking")
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
    print("In production, replace mocks with real dependencies:")
    print("- MockDocumentRepository → abs_orm.DocumentRepository")
    print("- MockBlockchain → abs_blockchain.BlockchainClient")
    print("- Use mint_nft_from_file() for one-call NFT minting with auto Arweave upload! ⭐")


if __name__ == "__main__":
    asyncio.run(main())
