"""
Example 4: Complete API integration patterns with mocks

This example demonstrates:
- API endpoint patterns for document notarization
- Status polling workflows
- Error handling patterns
- Using mock dependencies for testing
"""

import asyncio
from tests.mocks.mock_orm import (
    MockDocumentRepository,
    DocStatus,
    DocType,
    create_document,
    get_session
)
from tests.mocks.mock_blockchain import MockBlockchain
from tests.mocks.mock_utils import get_logger, ValidationError


class MockAPI:
    """Mock API class demonstrating endpoint patterns"""

    def __init__(self):
        self.repo = MockDocumentRepository()
        self.blockchain = MockBlockchain()
        self.logger = get_logger("mock_api")

    async def upload_document(self, file_name: str, file_path: str, doc_type: str = "hash") -> dict:
        """Mock document upload endpoint"""
        self.logger.info("Document upload requested", extra={"file_name": file_name})

        # Create document record
        doc = await self.repo.create({
            'file_name': file_name,
            'file_path': file_path,
            'type': DocType(doc_type),
        })

        self.logger.info("Document created", extra={"doc_id": doc.id})
        return {
            "doc_id": doc.id,
            "file_name": doc.file_name,
            "status": doc.status.value,
            "type": doc.type.value,
            "message": "Document uploaded successfully"
        }

    async def notarize_document(self, doc_id: int) -> dict:
        """Mock document notarization endpoint"""
        self.logger.info("Notarization requested", extra={"doc_id": doc_id})

        # Get document
        doc = await self.repo.get(doc_id)
        if not doc:
            raise ValidationError(f"Document {doc_id} not found")

        if doc.status != DocStatus.PENDING:
            raise ValidationError(f"Document already {doc.status.value}")

        # Update to processing
        await self.repo.update(doc_id, status=DocStatus.PROCESSING)

        # Simulate blockchain operation
        if doc.type == DocType.HASH:
            tx_hash = await self.blockchain.record_hash(doc.file_hash, {"doc_id": doc_id})
        else:
            # Simulate NFT workflow
            file_url = await self.blockchain.upload_to_arweave(b"mock file data", "application/pdf")
            metadata_url = await self.blockchain.upload_to_arweave(b"mock metadata", "application/json")
            tx_hash = await self.blockchain.mint_nft("0xowner", 1, metadata_url)

        # Wait for confirmation
        await self.blockchain.wait_for_confirmations(tx_hash, required_confirmations=3)

        # Update document as complete
        await self.repo.update(doc_id,
            status=DocStatus.ON_CHAIN,
            transaction_hash=tx_hash
        )

        self.logger.info("Document notarized", extra={"doc_id": doc_id, "tx_hash": tx_hash})
        return {
            "doc_id": doc_id,
            "status": "processing",
            "message": "Notarization started"
        }

    async def get_document_status(self, doc_id: int) -> dict:
        """Mock document status endpoint"""
        doc = await self.repo.get(doc_id)
        if not doc:
            raise ValidationError(f"Document {doc_id} not found")

        return {
            "doc_id": doc.id,
            "file_name": doc.file_name,
            "status": doc.status.value,
            "type": doc.type.value,
            "transaction_hash": doc.transaction_hash,
            "error_message": doc.error_message,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        }


async def api_workflow_demo():
    """Demonstrate complete API workflow"""
    print("=== Complete API Integration Example ===\n")

    api = MockAPI()

    # Step 1: Upload document
    print("1. Uploading document...")
    upload_result = await api.upload_document("contract.pdf", "/tmp/contract.pdf", "hash")
    doc_id = upload_result["doc_id"]
    print(f"✓ Document uploaded with ID: {doc_id}")

    # Step 2: Start notarization
    print("\n2. Starting notarization...")
    notarize_result = await api.notarize_document(doc_id)
    print(f"✓ Notarization started: {notarize_result['message']}")

    # Step 3: Check status
    print("\n3. Checking status...")
    status_result = await api.get_document_status(doc_id)
    print(f"✓ Final status: {status_result['status']}")
    print(f"✓ Transaction: {status_result['transaction_hash']}")

    return status_result


async def error_handling_demo():
    """Demonstrate error handling"""
    print("\n=== Error Handling Demo ===\n")

    api = MockAPI()

    try:
        # Try to notarize non-existent document
        await api.notarize_document(999)
    except ValidationError as e:
        print(f"✓ Caught expected error: {e}")
        print(f"Error details: {e.to_dict()}")


async def main():
    """Run API integration examples"""
    print("API Integration Patterns with Mock Dependencies")
    print("=" * 50)

    await api_workflow_demo()
    await error_handling_demo()

    print("\n✓ API integration examples completed!")
    print("\nNote: In production, replace mock imports with real dependencies:")
    print("- MockAPI → FastAPI app")
    print("- MockDocumentRepository → abs_orm.DocumentRepository")
    print("- MockBlockchain → abs_blockchain")


if __name__ == "__main__":
    asyncio.run(main())