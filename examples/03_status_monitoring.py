"""
Example 3: Transaction status monitoring with mocks

This example demonstrates:
- Monitoring blockchain transactions using mocks
- Checking transaction confirmations
- Frontend polling patterns
"""

import asyncio
from tests.mocks.mock_blockchain import MockBlockchain
from tests.mocks.mock_utils import get_logger


async def monitor_transaction_example():
    """
    Example of monitoring a transaction until confirmed using mocks

    This demonstrates the monitoring pattern used internally during notarization.
    """
    print("=== Transaction Monitoring Example ===\n")

    logger = get_logger("monitor_example")
    blockchain = MockBlockchain()

    # Simulate a transaction that was just submitted
    tx_hash = "0x0000000000000000000000000000000000000000000000000000000000001000"
    print(f"Monitoring transaction {tx_hash}")
    print("Waiting for confirmations...\n")

    # Check initial status
    receipt = await blockchain.get_transaction_receipt(tx_hash)
    print(f"Initial status: {receipt['status']}")
    print(f"Initial confirmations: {receipt['confirmations']}\n")

    # Wait for confirmations
    required_confirmations = 3
    max_attempts = 10
    poll_interval = 1  # seconds

    for attempt in range(max_attempts):
        receipt = await blockchain.get_transaction_receipt(tx_hash)
        confirmations = receipt['confirmations']

        print(f"Attempt {attempt + 1}: {confirmations} confirmations")

        if confirmations >= required_confirmations:
            print(f"✓ Transaction confirmed with {confirmations} blocks!")
            logger.info("Transaction confirmed", extra={
                "tx_hash": tx_hash,
                "confirmations": confirmations,
                "block_number": receipt['blockNumber']
            })
            break

        # Simulate time passing by advancing block number
        blockchain.current_block += 1
        await asyncio.sleep(poll_interval)

    else:
        print("✗ Transaction monitoring timed out")
        logger.warning("Transaction monitoring timed out", extra={"tx_hash": tx_hash})


async def polling_pattern_example():
    """
    Demonstrate frontend polling pattern for status updates
    """
    print("\n=== Frontend Polling Pattern Example ===\n")

    from tests.mocks.mock_orm import MockDocumentRepository, create_mock_document as create_document, DocStatus

    logger = get_logger("polling_example")
    repo = MockDocumentRepository()

    # Create a document in processing state
    doc = create_document(id=123, status=DocStatus.PROCESSING)
    repo.documents[123] = doc

    print("Simulating frontend polling for document status...")
    print("(In real app, this would be HTTP requests every 2-3 seconds)\n")

    # Simulate polling loop
    max_polls = 5
    for poll_count in range(max_polls):
        retrieved = await repo.get(123)
        status = retrieved.status.value

        print(f"Poll {poll_count + 1}: Status = {status}")

        if status == "on_chain":
            print("✓ Document processing complete!")
            logger.info("Document processing complete", extra={"doc_id": 123})
            break
        elif status == "error":
            print("✗ Document processing failed!")
            logger.error("Document processing failed", extra={"doc_id": 123})
            break

        # Simulate processing time
        await asyncio.sleep(1)

        # Update status to simulate completion
        if poll_count == 2:  # Complete on 3rd poll
            await repo.update(123, status=DocStatus.ON_CHAIN, transaction_hash="0xabc123")

    else:
        print("Still processing... (would continue polling in real app)")


async def main():
    """
    Run monitoring examples
    """
    print("Transaction Status Monitoring Examples")
    print("=" * 50)

    await monitor_transaction_example()
    await polling_pattern_example()

    print("\n✓ Monitoring examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
