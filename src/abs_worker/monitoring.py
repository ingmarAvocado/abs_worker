"""
Transaction monitoring and confirmation polling

This module handles:
- Polling blockchain for transaction status
- Waiting for required confirmations
- Handling timeout and reverted transactions
"""

import asyncio
from typing import Optional, Dict, Any

from abs_blockchain import BlockchainClient
from abs_utils.logger import get_logger
from .config import get_settings

logger = get_logger(__name__)


async def monitor_transaction(
    client: BlockchainClient, doc_id: Optional[int], tx_hash: str
) -> Dict[str, Any]:
    """
    Monitor blockchain transaction until confirmed

    Polls blockchain at regular intervals until the transaction receives
    the required number of confirmations.

    Args:
        client: Blockchain client instance to use
        doc_id: Document ID being processed (for logging), can be None for generic monitoring
        tx_hash: Transaction hash to monitor

    Returns:
        Transaction receipt dict with confirmation details

    Raises:
        TimeoutError: If max_confirmation_wait exceeded
        ValueError: If transaction reverted
    """
    settings = get_settings()
    logger.info(
        f"Monitoring transaction {tx_hash}"
        + (f" for document {doc_id}" if doc_id is not None else ""),
        extra={"doc_id": doc_id, "tx_hash": tx_hash}
        if doc_id is not None
        else {"tx_hash": tx_hash},
    )
    attempts = 0
    start_time = asyncio.get_event_loop().time()

    while attempts < settings.blockchain.max_poll_attempts:
        try:
            # Get transaction receipt
            receipt = await client.get_transaction_receipt(tx_hash)

            if receipt is None:
                # Transaction not yet mined
                logger.debug(
                    f"Transaction {tx_hash} not yet mined, waiting...",
                    extra={"tx_hash": tx_hash, "attempt": attempts},
                )
                await asyncio.sleep(settings.blockchain.poll_interval)
                attempts += 1
                continue

            # Check if transaction reverted
            if receipt.get("status") == 0:
                logger.error(
                    f"Transaction {tx_hash} reverted",
                    extra={"tx_hash": tx_hash, "receipt": receipt},
                )
                raise ValueError(f"Transaction {tx_hash} reverted")

            # Check confirmations - only fetch latest block when we have a receipt
            tx_block = receipt.get("blockNumber")
            current_block = await client.get_latest_block_number()
            confirmations = current_block - tx_block

            if confirmations >= settings.blockchain.required_confirmations:
                logger.info(
                    f"Transaction {tx_hash} confirmed with {confirmations} confirmations",
                    extra={
                        "tx_hash": tx_hash,
                        "confirmations": confirmations,
                        "block_number": tx_block,
                    },
                )
                return receipt

            logger.debug(
                f"Transaction {tx_hash} has {confirmations}/{settings.blockchain.required_confirmations} confirmations",
                extra={"tx_hash": tx_hash, "confirmations": confirmations},
            )

        except ValueError:
            # Re-raise ValueError (reverted transaction)
            raise
        except (ConnectionError, TimeoutError, OSError) as e:
            # These are recoverable network/transient errors
            logger.warning(
                f"Recoverable error checking transaction {tx_hash}: {e}",
                extra={"tx_hash": tx_hash, "error": str(e), "attempt": attempts},
            )

        # Check timeout
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > settings.blockchain.max_confirmation_wait:
            raise TimeoutError(f"Transaction {tx_hash} confirmation timeout after {elapsed:.0f}s")

        await asyncio.sleep(settings.blockchain.poll_interval)
        attempts += 1

    raise TimeoutError(f"Transaction {tx_hash} exceeded max poll attempts")


async def check_transaction_status(client: BlockchainClient, tx_hash: str) -> Dict[str, Any]:
    """
    Check current status of a blockchain transaction

    Args:
        client: Blockchain client instance to use
        tx_hash: Transaction hash to check

    Returns:
        Dict with status information:
        {
            "status": "pending" | "confirmed" | "reverted",
            "confirmations": int,
            "receipt": dict | None
        }
    """

    try:
        receipt = await client.get_transaction_receipt(tx_hash)

        if receipt is None:
            return {"status": "pending", "confirmations": 0, "receipt": None}

        if receipt.get("status") == 0:
            return {"status": "reverted", "confirmations": 0, "receipt": receipt}

        tx_block = receipt.get("blockNumber")
        current_block = await client.get_latest_block_number()
        confirmations = current_block - tx_block

        return {
            "status": "confirmed",
            "confirmations": confirmations,
            "receipt": receipt,
        }

    except Exception as e:
        logger.error(
            f"Failed to check transaction status for {tx_hash}: {e}",
            extra={"tx_hash": tx_hash, "error": str(e)},
        )
        raise


async def wait_for_confirmation(
    client: BlockchainClient, tx_hash: str, required_confirmations: Optional[int] = None
) -> Dict[str, Any]:
    """
    Wait for transaction to receive required confirmations

    Args:
        client: Blockchain client instance to use
        tx_hash: Transaction hash to wait for
        required_confirmations: Number of confirmations required (uses config default if None)

    Returns:
        Transaction receipt

    Raises:
        ValueError: If transaction reverted
        TimeoutError: If confirmation timeout exceeded
    """
    settings = get_settings()
    confirmations_needed = required_confirmations or settings.blockchain.required_confirmations

    logger.info(
        f"Waiting for {confirmations_needed} confirmations for transaction {tx_hash}",
        extra={"tx_hash": tx_hash, "required_confirmations": confirmations_needed},
    )

    # Use monitor_transaction with doc_id=None for generic monitoring
    return await monitor_transaction(client, None, tx_hash)
