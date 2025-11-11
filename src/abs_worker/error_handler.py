"""
Error handling and retry logic for failed transactions

This module handles:
- Determining if errors are retryable
- Implementing exponential backoff retry logic
- Marking documents as ERROR when permanently failed
"""

import asyncio
# from abs_orm import get_session, DocumentRepository, DocStatus
# from abs_utils.logger import get_logger
from .config import get_settings

# logger = get_logger(__name__)


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable

    Retryable errors:
        - Network timeouts
        - Connection errors
        - Gas estimation failures
        - Nonce errors

    Non-retryable errors:
        - Contract execution reverted
        - Insufficient funds
        - Invalid signatures
        - Duplicate file hash

    Args:
        error: Exception to check

    Returns:
        True if error should trigger a retry, False otherwise
    """
    error_str = str(error).lower()

    # Retryable errors
    retryable_keywords = [
        "timeout",
        "connection",
        "network",
        "gas estimation",
        "nonce too low",
        "replacement transaction underpriced",
        "transaction underpriced",
    ]

    for keyword in retryable_keywords:
        if keyword in error_str:
            return True

    # Non-retryable errors
    non_retryable_keywords = [
        "reverted",
        "insufficient funds",
        "invalid signature",
        "already exists",
        "unauthorized",
        "access denied",
    ]

    for keyword in non_retryable_keywords:
        if keyword in error_str:
            return False

    # Default to retryable for unknown errors (be conservative)
    return True


async def handle_failed_transaction(doc_id: int, error: Exception) -> None:
    """
    Handle failed transaction with retry logic

    Flow:
        1. Log error with context
        2. Check if error is retryable
        3. If retryable: implement retry with exponential backoff
        4. If not retryable: mark document as ERROR
        5. Update error_message in document

    Args:
        doc_id: Document ID that failed
        error: Exception that caused failure
    """
    # TODO: Implement when abs_orm is available
    # settings = get_settings()
    # logger.error(f"Transaction failed for document {doc_id}: {error}")

    # async with get_session() as session:
    #     doc_repo = DocumentRepository(session)
    #     doc = await doc_repo.get(doc_id)

    #     if not doc:
    #         logger.error(f"Document {doc_id} not found during error handling")
    #         return

    #     # Check if retryable
    #     if is_retryable_error(error):
    #         logger.warning(
    #             f"Retryable error for document {doc_id}, will retry: {error}"
    #         )
    #         # In FastAPI BackgroundTasks, we can't easily retry
    #         # Just mark as error for now, user can re-trigger
    #         # In Celery, this would use task.retry()
    #     else:
    #         logger.error(
    #             f"Non-retryable error for document {doc_id}: {error}"
    #         )

    #     # Mark as error
    #     await doc_repo.update(
    #         doc_id,
    #         status=DocStatus.ERROR,
    #         error_message=str(error)[:500]  # Truncate long errors
    #     )
    #     await session.commit()
    #     logger.info(f"Document {doc_id} marked as ERROR")

    # Stub implementation
    pass


async def retry_with_backoff(
    func,
    *args,
    max_retries: int = None,
    initial_delay: int = None,
    backoff_multiplier: float = None,
    **kwargs
):
    """
    Retry a function with exponential backoff

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_retries: Maximum retry attempts (uses config default if None)
        initial_delay: Initial delay between retries (uses config default if None)
        backoff_multiplier: Multiplier for exponential backoff (uses config default if None)
        **kwargs: Keyword arguments for func

    Returns:
        Result of successful function call

    Raises:
        Exception: Last exception if all retries exhausted
    """
    settings = get_settings()
    max_retries = max_retries or settings.max_retries
    delay = initial_delay or settings.retry_delay
    multiplier = backoff_multiplier or settings.retry_backoff_multiplier

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if attempt == max_retries:
                # logger.error(f"All retry attempts exhausted: {e}")
                raise

            if not is_retryable_error(e):
                # logger.error(f"Non-retryable error, not retrying: {e}")
                raise

            wait_time = delay * (multiplier ** attempt)
            # logger.warning(
            #     f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
            #     f"Retrying in {wait_time:.1f}s..."
            # )
            await asyncio.sleep(wait_time)

    raise last_exception
