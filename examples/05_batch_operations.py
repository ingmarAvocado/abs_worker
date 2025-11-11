"""
Example 5: Batch Processing Operations

This shows patterns for processing multiple documents:
- Parallel processing with concurrency limits
- Progress tracking and reporting
- Rate limiting to avoid blockchain congestion
- Batch retry for failed documents
- Scheduled batch jobs (cron patterns)

Use cases:
- Nightly batch processing of pending documents
- Migration scripts
- Admin bulk operations
- Retry all failed documents
"""

import asyncio
from typing import List, Dict, AsyncIterator
from datetime import datetime, timedelta
from dataclasses import dataclass

# These will be real imports when integrated
# from abs_orm import get_session, DocumentRepository, DocStatus
# from abs_utils.logger import get_logger
from abs_worker import process_hash_notarization, process_nft_notarization

# logger = get_logger(__name__)


# =============================================================================
# Helper Classes
# =============================================================================

@dataclass
class BatchResult:
    """Result of batch processing"""
    total: int
    successful: int
    failed: int
    skipped: int
    duration_seconds: float
    errors: List[Dict[str, str]]


@dataclass
class DocumentJob:
    """Document processing job"""
    doc_id: int
    type: str  # "hash" or "nft"
    retry_count: int = 0


# =============================================================================
# Batch Processing Utilities
# =============================================================================

async def chunked(items: List, size: int) -> AsyncIterator[List]:
    """
    Split items into chunks for batch processing

    Example:
        async for batch in chunked(doc_ids, size=10):
            await process_batch(batch)
    """
    for i in range(0, len(items), size):
        yield items[i:i + size]


async def process_with_concurrency_limit(
    doc_ids: List[int],
    max_concurrent: int = 5
) -> BatchResult:
    """
    Process documents with concurrency limit

    Args:
        doc_ids: List of document IDs to process
        max_concurrent: Maximum parallel operations

    Returns:
        Batch processing results
    """
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  Batch Processing with Concurrency Limit: {max_concurrent}        ║")
    print(f"╚══════════════════════════════════════════════════════╝\n")

    start_time = datetime.utcnow()
    successful = 0
    failed = 0
    errors = []

    # Use semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_one(doc_id: int) -> bool:
        """Process single document with semaphore"""
        async with semaphore:
            try:
                print(f"Processing document {doc_id}...")
                await process_hash_notarization(doc_id)
                print(f"✓ Document {doc_id} completed")
                return True
            except Exception as e:
                print(f"✗ Document {doc_id} failed: {e}")
                errors.append({"doc_id": doc_id, "error": str(e)})
                return False

    # Process all documents with concurrency limit
    results = await asyncio.gather(
        *[process_one(doc_id) for doc_id in doc_ids],
        return_exceptions=True
    )

    for result in results:
        if isinstance(result, Exception):
            failed += 1
        elif result is True:
            successful += 1
        else:
            failed += 1

    duration = (datetime.utcnow() - start_time).total_seconds()

    return BatchResult(
        total=len(doc_ids),
        successful=successful,
        failed=failed,
        skipped=0,
        duration_seconds=duration,
        errors=errors
    )


async def process_with_rate_limit(
    doc_ids: List[int],
    rate_limit: int = 10,  # documents per minute
) -> BatchResult:
    """
    Process documents with rate limiting

    Args:
        doc_ids: Documents to process
        rate_limit: Max documents per minute

    Returns:
        Batch processing results
    """
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  Batch Processing with Rate Limit: {rate_limit}/min       ║")
    print(f"╚══════════════════════════════════════════════════════╝\n")

    delay_between_docs = 60.0 / rate_limit
    start_time = datetime.utcnow()
    successful = 0
    failed = 0
    errors = []

    for i, doc_id in enumerate(doc_ids):
        try:
            print(f"[{i+1}/{len(doc_ids)}] Processing document {doc_id}...")
            await process_hash_notarization(doc_id)
            successful += 1
            print(f"✓ Document {doc_id} completed")
        except Exception as e:
            failed += 1
            print(f"✗ Document {doc_id} failed: {e}")
            errors.append({"doc_id": doc_id, "error": str(e)})

        # Rate limiting delay
        if i < len(doc_ids) - 1:  # Don't wait after last one
            await asyncio.sleep(delay_between_docs)

    duration = (datetime.utcnow() - start_time).total_seconds()

    return BatchResult(
        total=len(doc_ids),
        successful=successful,
        failed=failed,
        skipped=0,
        duration_seconds=duration,
        errors=errors
    )


async def retry_failed_documents() -> BatchResult:
    """
    Retry all documents that previously failed

    Flow:
        1. Query database for status=ERROR
        2. Filter out non-retryable errors
        3. Process with rate limiting
        4. Report results
    """
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  Retrying Failed Documents                           ║")
    print(f"╚══════════════════════════════════════════════════════╝\n")

    # TODO: Query real database
    # async with get_session() as session:
    #     doc_repo = DocumentRepository(session)
    #     failed_docs = await doc_repo.get_error_documents()
    #
    #     # Filter retryable errors
    #     retryable = []
    #     for doc in failed_docs:
    #         if is_retryable_error_message(doc.error_message):
    #             retryable.append(doc.id)
    #
    #     if not retryable:
    #         print("No retryable documents found")
    #         return BatchResult(0, 0, 0, 0, 0.0, [])
    #
    #     print(f"Found {len(retryable)} retryable documents")
    #
    #     # Retry with rate limiting
    #     return await process_with_rate_limit(retryable, rate_limit=5)

    # Stub implementation
    failed_doc_ids = [100, 101, 102]  # Mock failed documents
    print(f"Found {len(failed_doc_ids)} failed documents to retry")

    return await process_with_rate_limit(failed_doc_ids, rate_limit=5)


async def process_pending_batch(batch_size: int = 50) -> BatchResult:
    """
    Process batch of pending documents

    Typical use: Scheduled cron job every hour

    Flow:
        1. Query pending documents (limit=batch_size)
        2. Process with concurrency control
        3. Report results
        4. Can be run repeatedly
    """
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  Processing Pending Documents Batch                  ║")
    print(f"╚══════════════════════════════════════════════════════╝\n")

    # TODO: Query real database
    # async with get_session() as session:
    #     doc_repo = DocumentRepository(session)
    #     pending_docs = await doc_repo.get_pending_documents(limit=batch_size)
    #
    #     if not pending_docs:
    #         print("No pending documents")
    #         return BatchResult(0, 0, 0, 0, 0.0, [])
    #
    #     doc_ids = [doc.id for doc in pending_docs]
    #     print(f"Found {len(doc_ids)} pending documents")
    #
    #     return await process_with_concurrency_limit(doc_ids, max_concurrent=10)

    # Stub implementation
    pending_doc_ids = list(range(1, 11))  # Mock 10 pending documents
    print(f"Found {len(pending_doc_ids)} pending documents")

    return await process_with_concurrency_limit(pending_doc_ids, max_concurrent=5)


async def smart_batch_processor(
    doc_jobs: List[DocumentJob],
    max_concurrent: int = 10
) -> BatchResult:
    """
    Smart batch processor that handles both hash and NFT types

    Args:
        doc_jobs: List of DocumentJob with type info
        max_concurrent: Max parallel operations

    Returns:
        Batch processing results
    """
    print(f"\n╔══════════════════════════════════════════════════════╗")
    print(f"║  Smart Batch Processor (Hash + NFT)                  ║")
    print(f"╚══════════════════════════════════════════════════════╝\n")

    start_time = datetime.utcnow()
    successful = 0
    failed = 0
    skipped = 0
    errors = []

    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_job(job: DocumentJob) -> bool:
        """Process job based on type"""
        async with semaphore:
            try:
                print(f"Processing {job.type} document {job.doc_id}...")

                if job.type == "hash":
                    await process_hash_notarization(job.doc_id)
                elif job.type == "nft":
                    await process_nft_notarization(job.doc_id)
                else:
                    raise ValueError(f"Unknown type: {job.type}")

                print(f"✓ Document {job.doc_id} ({job.type}) completed")
                return True

            except Exception as e:
                print(f"✗ Document {job.doc_id} failed: {e}")
                errors.append({
                    "doc_id": job.doc_id,
                    "type": job.type,
                    "error": str(e)
                })
                return False

    # Process all jobs
    results = await asyncio.gather(
        *[process_job(job) for job in doc_jobs],
        return_exceptions=True
    )

    for result in results:
        if isinstance(result, Exception):
            failed += 1
        elif result is True:
            successful += 1
        else:
            failed += 1

    duration = (datetime.utcnow() - start_time).total_seconds()

    return BatchResult(
        total=len(doc_jobs),
        successful=successful,
        failed=failed,
        skipped=skipped,
        duration_seconds=duration,
        errors=errors
    )


def print_batch_results(result: BatchResult):
    """Pretty print batch results"""
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING RESULTS")
    print(f"{'='*60}")
    print(f"Total documents:    {result.total}")
    print(f"✓ Successful:       {result.successful}")
    print(f"✗ Failed:           {result.failed}")
    print(f"⊘ Skipped:          {result.skipped}")
    print(f"⏱  Duration:         {result.duration_seconds:.2f}s")

    if result.errors:
        print(f"\n{'='*60}")
        print(f"ERRORS ({len(result.errors)}):")
        print(f"{'='*60}")
        for error in result.errors[:5]:  # Show first 5
            print(f"  Document {error['doc_id']}: {error['error']}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more errors")

    print(f"{'='*60}\n")


# =============================================================================
# Scheduled Job Examples
# =============================================================================

async def hourly_batch_job():
    """
    Hourly cron job to process pending documents

    Crontab entry:
        0 * * * * /path/to/python /path/to/05_batch_operations.py hourly
    """
    print("Running hourly batch job...")
    result = await process_pending_batch(batch_size=100)
    print_batch_results(result)

    # TODO: Send notification if many failures
    # if result.failed > result.successful * 0.2:  # > 20% failure rate
    #     await send_alert(f"High failure rate: {result.failed}/{result.total}")


async def nightly_retry_job():
    """
    Nightly cron job to retry failed documents

    Crontab entry:
        0 2 * * * /path/to/python /path/to/05_batch_operations.py nightly
    """
    print("Running nightly retry job...")
    result = await retry_failed_documents()
    print_batch_results(result)


# =============================================================================
# Main Examples
# =============================================================================

async def example_basic_batch():
    """Example: Basic batch with concurrency limit"""
    doc_ids = list(range(1, 21))  # 20 documents
    result = await process_with_concurrency_limit(doc_ids, max_concurrent=5)
    print_batch_results(result)


async def example_rate_limited_batch():
    """Example: Batch with rate limiting"""
    doc_ids = list(range(1, 11))  # 10 documents
    result = await process_with_rate_limit(doc_ids, rate_limit=20)  # 20/min
    print_batch_results(result)


async def example_mixed_types_batch():
    """Example: Batch with mixed document types"""
    jobs = [
        DocumentJob(doc_id=1, type="hash"),
        DocumentJob(doc_id=2, type="hash"),
        DocumentJob(doc_id=3, type="nft"),
        DocumentJob(doc_id=4, type="hash"),
        DocumentJob(doc_id=5, type="nft"),
    ]

    result = await smart_batch_processor(jobs, max_concurrent=3)
    print_batch_results(result)


async def example_retry_failed():
    """Example: Retry failed documents"""
    result = await retry_failed_documents()
    print_batch_results(result)


async def example_pending_batch():
    """Example: Process pending documents"""
    result = await process_pending_batch(batch_size=20)
    print_batch_results(result)


# =============================================================================
# CLI Interface
# =============================================================================

async def main():
    """Run all examples"""
    print("""
╔═════════════════════════════════════════════════════════╗
║         Batch Operations Examples                       ║
╚═════════════════════════════════════════════════════════╝

This demonstrates various batch processing patterns.
""")

    # Run examples
    await example_basic_batch()
    await example_rate_limited_batch()
    await example_mixed_types_batch()
    await example_retry_failed()
    await example_pending_batch()

    print("\n✓ All batch examples completed\n")


if __name__ == "__main__":
    import sys

    # Support CLI arguments for cron jobs
    if len(sys.argv) > 1:
        if sys.argv[1] == "hourly":
            asyncio.run(hourly_batch_job())
        elif sys.argv[1] == "nightly":
            asyncio.run(nightly_retry_job())
        elif sys.argv[1] == "pending":
            asyncio.run(example_pending_batch())
        elif sys.argv[1] == "retry":
            asyncio.run(example_retry_failed())
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python 05_batch_operations.py [hourly|nightly|pending|retry]")
    else:
        # Run all examples
        asyncio.run(main())
