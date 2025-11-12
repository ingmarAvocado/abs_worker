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
from tests.mocks.mock_orm import (
    MockDocumentRepository,
    DocStatus,
    DocType,
    get_session,
    create_mock_document as create_document,
    create_mock_nft_document as create_nft_document,
)
from tests.mocks.mock_blockchain import MockBlockchain
from tests.mocks.mock_utils import get_logger
from tests.mocks.factories import create_hash_document


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
    hash_doc = create_hash_document(
        id=1,
        file_name="contract.pdf",
        file_hash="0xabcdef123456"
    )

    # Add to repository
    repo.documents[1] = hash_doc
    logger.info("Created hash document", extra={"doc_id": 1, "file_name": "contract.pdf"})

    # Retrieve document
    retrieved = await repo.get(1)
    print(f"Retrieved document: {retrieved.file_name}")
    print(f"Status: {retrieved.status.value}")
    print(f"Type: {retrieved.type.value}\n")

    # Update document status
    updated = await repo.update(1, status=DocStatus.PROCESSING)
    print(f"Updated status to: {updated.status.value}")
    logger.info("Document status updated", extra={"doc_id": 1, "new_status": "processing"})

    # Create document via repository
    new_doc = await repo.create({
        'file_name': 'report.pdf',
        'file_hash': '0xfedcba654321',
        'file_path': '/tmp/report.pdf'
    })
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
        metadata_url=arweave_url
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
    doc = repo.create({
        'file_name': 'contract.pdf',
        'file_hash': '0xabcdef123456789',
        'file_path': '/tmp/contract.pdf'
    })
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
        result = await blockchain.notarize_hash(
            file_hash=doc.file_hash,
            metadata={
                "file_name": doc.file_name,
                "timestamp": doc.created_at.isoformat()
            }
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
            signed_pdf_path=pdf_path
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
