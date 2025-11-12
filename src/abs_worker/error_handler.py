"""
Error handling and retry logic for failed transactions

This module handles:
- Determining if errors are retryable
- Implementing exponential backoff retry logic
- Marking documents as ERROR when permanently failed
"""

import asyncio
from typing import Optional, Callable, Any

from abs_orm import get_session, DocumentRepository, DocStatus
from abs_utils.logger import get_logger
from .config import get_settings

logger = get_logger(__name__)


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
    Handle failed transaction by marking document as ERROR

    This function is called when a transaction has permanently failed.
    It updates the document status to ERROR and stores the error message.

    Args:
        doc_id: Document ID that failed
        error: Exception that caused failure
    """
    logger.error(
        f"Transaction failed for document {doc_id}: {error}",
        extra={"doc_id": doc_id, "error": str(error)},
    )

    async with get_session() as session:
        doc_repo = DocumentRepository(session)
        doc = await doc_repo.get(doc_id)

        if not doc:
            logger.error(
                f"Document {doc_id} not found during error handling", extra={"doc_id": doc_id}
            )
            return

        # Check if retryable for logging purposes
        if is_retryable_error(error):
            logger.warning(
                f"Retryable error for document {doc_id}, marking as ERROR (retry not implemented in FastAPI): {error}",
                extra={"doc_id": doc_id, "error": str(error), "retryable": True},
            )
        else:
            logger.error(
                f"Non-retryable error for document {doc_id}: {error}",
                extra={"doc_id": doc_id, "error": str(error), "retryable": False},
            )

        # Mark as error
        await doc_repo.update(
            doc_id, status=DocStatus.ERROR, error_message=str(error)[:500]  # Truncate long errors
        )

        await session.commit()
        logger.info(f"Document {doc_id} marked as ERROR", extra={"doc_id": doc_id})


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    max_retries: Optional[int] = None,
    initial_delay: Optional[int] = None,
    backoff_multiplier: Optional[float] = None,
    **kwargs,
) -> Any:
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
    max_retries = max_retries if max_retries is not None else settings.max_retries
    delay = initial_delay if initial_delay is not None else settings.retry_delay
    multiplier = (
        backoff_multiplier if backoff_multiplier is not None else settings.retry_backoff_multiplier
    )

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            if attempt == max_retries:
                # logger.error(f"All retry attempts exhausted: {e}")
                raise

            if not is_retryable_error(e):
                # logger.error(f"Non-retryable error, not retrying: {e}")
                raise

            wait_time = delay * (multiplier**attempt)
            # logger.warning(
            #     f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
            #     f"Retrying in {wait_time:.1f}s..."
            # )
            await asyncio.sleep(wait_time)

    # This should never be reached, but just in case
    raise RuntimeError("Unexpected end of retry loop")
