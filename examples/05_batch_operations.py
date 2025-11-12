"""
Example 5: Batch operations with mock dependencies

This example demonstrates:
- Processing multiple documents in parallel
- Batch notarization workflows
- Performance monitoring
- Error handling in batch operations
"""

import asyncio
import time
from typing import List, Dict, Any
from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, create_document
from tests.mocks.mock_blockchain import MockBlockchain, ContractRevertedException
from tests.mocks.mock_utils import get_logger


async def process_single_document(repo: MockDocumentRepository, blockchain: MockBlockchain,
                                doc_id: int, logger) -> Dict[str, Any]:
    """Process a single document"""
    try:
        # Get document
        doc = await repo.get(doc_id)
        if not doc:
            return {"doc_id": doc_id, "status": "error", "error": "Document not found"}

        if doc.status != DocStatus.PENDING:
            return {"doc_id": doc_id, "status": "skipped", "reason": f"Already {doc.status.value}"}

        # Update to processing
        await repo.update(doc_id, status=DocStatus.PROCESSING)

        # Simulate blockchain operation
        if doc.type.value == "hash":
            tx_hash = await blockchain.record_hash(doc.file_hash, {"doc_id": doc_id})
        else:
            # NFT workflow
            file_url = await blockchain.upload_to_arweave(b"mock data", "application/pdf")
            metadata_url = await blockchain.upload_to_arweave(b"mock metadata", "application/json")
            tx_hash = await blockchain.mint_nft("0xowner", doc_id, metadata_url)

        # Wait for confirmations
        await blockchain.wait_for_confirmations(tx_hash, required_confirmations=3)

        # Mark as complete
        await repo.update(doc_id, status=DocStatus.ON_CHAIN, transaction_hash=tx_hash)

        logger.info("Document processed successfully", extra={"doc_id": doc_id, "tx_hash": tx_hash})
        return {"doc_id": doc_id, "status": "success", "tx_hash": tx_hash}

    except Exception as e:
        # Mark as failed
        try:
            await repo.update(doc_id, status=DocStatus.ERROR, error_message=str(e))
        except:
            pass  # Repository might not exist

        logger.error("Document processing failed", extra={"doc_id": doc_id, "error": str(e)})
        return {"doc_id": doc_id, "status": "error", "error": str(e)}


async def batch_process_documents(doc_ids: List[int], max_concurrent: int = 3) -> Dict[str, Any]:
    """Process multiple documents in parallel with concurrency control"""
    print(f"=== Batch Processing {len(doc_ids)} Documents ===\n")

    logger = get_logger("batch_processor")
    repo = MockDocumentRepository()
    blockchain = MockBlockchain()

    # Create test documents
    for doc_id in doc_ids:
        doc = create_document(id=doc_id, file_name=f"document_{doc_id}.pdf")
        repo.documents[doc_id] = doc

    start_time = time.time()
    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def process_with_semaphore(doc_id: int):
        async with semaphore:
            return await process_single_document(repo, blockchain, doc_id, logger)

    # Process in parallel with concurrency limit
    tasks = [process_with_semaphore(doc_id) for doc_id in doc_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle results
    successful = 0
    failed = 0
    skipped = 0
    errors = []

    for i, result in enumerate(results):
        doc_id = doc_ids[i]
        if isinstance(result, Exception):
            failed += 1
            errors.append({"doc_id": doc_id, "error": str(result)})
            print(f"✗ Document {doc_id}: Exception - {result}")
        else:
            status = result.get("status")
            if status == "success":
                successful += 1
                tx_hash = result.get("tx_hash", "")
                print(f"✓ Document {doc_id}: Success - {tx_hash[:10]}...")
            elif status == "error":
                failed += 1
                error_msg = result.get("error", "Unknown error")
                errors.append({"doc_id": doc_id, "error": error_msg})
                print(f"✗ Document {doc_id}: {error_msg}")
            elif status == "skipped":
                skipped += 1
                reason = result.get("reason", "Unknown reason")
                print(f"⚠ Document {doc_id}: Skipped - {reason}")

    duration = time.time() - start_time

    batch_result = {
        "total": len(doc_ids),
        "successful": successful,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": round(duration, 2),
        "errors": errors
    }

    print(f"\nBatch completed in {batch_result['duration_seconds']}s")
    print(f"Results: {successful} success, {failed} failed, {skipped} skipped")

    return batch_result


async def simulate_failures_and_retries():
    """Demonstrate handling failures and retries"""
    print("\n=== Failure Handling and Retries ===\n")

    logger = get_logger("retry_demo")
    repo = MockDocumentRepository()
    blockchain = MockBlockchain()

    # Create documents
    doc_ids = [100, 101, 102]
    for doc_id in doc_ids:
        doc = create_document(id=doc_id)
        repo.documents[doc_id] = doc

    # Make some operations fail
    blockchain.set_next_transaction_failure(ContractRevertedException("Gas too low"))
    blockchain.set_next_transaction_failure(ContractRevertedException("Network timeout"))

    # Process batch
    results = await asyncio.gather(*[
        process_single_document(repo, blockchain, doc_id, logger)
        for doc_id in doc_ids
    ], return_exceptions=True)

    # Report results
    for i, result in enumerate(results):
        doc_id = doc_ids[i]
        if isinstance(result, Exception):
            print(f"✗ Document {doc_id}: Unhandled exception - {result}")
        else:
            status = result["status"]
            if status == "error":
                print(f"✗ Document {doc_id}: {result['error']}")
            else:
                print(f"✓ Document {doc_id}: {status}")


async def main():
    """Run batch processing examples"""
    print("Batch Operations with Mock Dependencies")
    print("=" * 50)

    # Example 1: Basic batch processing
    doc_ids = [1, 2, 3, 4, 5]
    result = await batch_process_documents(doc_ids, max_concurrent=2)

    # Example 2: Failure handling
    await simulate_failures_and_retries()

    print("\n✓ Batch operations examples completed!")
    print("\nNote: In production, replace mock calls with real:")
    print("- MockDocumentRepository → abs_orm.DocumentRepository")
    print("- MockBlockchain → abs_blockchain operations")
    print("- asyncio.gather → proper batch processing with error handling")


if __name__ == "__main__":
    asyncio.run(main())