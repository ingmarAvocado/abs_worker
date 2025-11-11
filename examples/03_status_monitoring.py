"""
Example 3: Transaction status monitoring

This example demonstrates:
- Monitoring blockchain transactions
- Checking transaction confirmations
- Frontend polling patterns
"""

import asyncio
from abs_worker import monitor_transaction, check_transaction_status


async def monitor_transaction_example():
    """
    Example of monitoring a transaction until confirmed

    This is what abs_worker does internally during notarization,
    but can also be used standalone for:
    - Admin tools
    - Transaction debugging
    - Manual verification
    """
    print("=== Transaction Monitoring Example ===\n")

    doc_id = 789
    tx_hash = "0xabc123def456..."

    print(f"Monitoring transaction {tx_hash}")
    print("Waiting for confirmations...\n")

    try:
        receipt = await monitor_transaction(doc_id, tx_hash)
        print(f"✓ Transaction confirmed!")
        print(f"  Block Number: {receipt['blockNumber']}")
        print(f"  Status: {'Success' if receipt['status'] == 1 else 'Reverted'}")

    except TimeoutError as e:
        print(f"✗ Transaction timeout: {e}")

    except ValueError as e:
        print(f"✗ Transaction reverted: {e}")


async def check_status_example():
    """
    Example of checking transaction status without waiting

    Useful for:
    - Quick status checks
    - Frontend status indicators
    - Debugging
    """
    print("\n=== Transaction Status Check Example ===\n")

    tx_hash = "0xdef456abc789..."

    status = await check_transaction_status(tx_hash)

    print(f"Transaction: {tx_hash}")
    print(f"Status: {status['status']}")
    print(f"Confirmations: {status['confirmations']}")

    if status['status'] == 'pending':
        print("⏳ Transaction still pending...")
    elif status['status'] == 'confirmed':
        print("✓ Transaction confirmed")
    elif status['status'] == 'reverted':
        print("✗ Transaction reverted")


async def frontend_polling_pattern():
    """
    Example of how frontend should poll for document status

    Frontend Pattern:
        1. User triggers action (sign document)
        2. API returns {"status": "processing"}
        3. Frontend starts polling every 2-3 seconds
        4. Poll /documents/{doc_id} endpoint
        5. When status changes to "on_chain", stop polling
        6. Show success message with certificate download links
    """
    print("\n=== Frontend Polling Pattern Example ===\n")

    doc_id = 123
    poll_interval = 2  # seconds
    max_polls = 30  # max 1 minute

    print(f"Simulating frontend polling for document {doc_id}...")
    print(f"Poll interval: {poll_interval}s\n")

    for attempt in range(max_polls):
        # In real implementation, this would call API endpoint
        # response = await http_client.get(f"/api/v1/documents/{doc_id}")
        # status = response.json()["status"]

        # Simulated status progression
        if attempt < 5:
            status = "processing"
        elif attempt < 10:
            status = "on_chain"
        else:
            status = "on_chain"

        print(f"Poll #{attempt + 1}: status = {status}")

        if status == "on_chain":
            print("\n✓ Document notarized successfully!")
            print("Certificates available for download")
            break

        elif status == "error":
            print("\n✗ Notarization failed")
            break

        await asyncio.sleep(poll_interval)
    else:
        print("\n⚠ Polling timeout - status still processing")


async def multiple_transaction_monitoring():
    """
    Example of monitoring multiple transactions simultaneously

    Useful for:
    - Batch operations
    - Admin dashboards
    - System monitoring
    """
    print("\n=== Multiple Transaction Monitoring Example ===\n")

    transactions = [
        (1, "0xaaa111..."),
        (2, "0xbbb222..."),
        (3, "0xccc333..."),
    ]

    print(f"Monitoring {len(transactions)} transactions in parallel...\n")

    # Monitor all transactions concurrently
    tasks = [
        monitor_transaction(doc_id, tx_hash)
        for doc_id, tx_hash in transactions
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Report results
    for (doc_id, tx_hash), result in zip(transactions, results):
        if isinstance(result, Exception):
            print(f"✗ Document {doc_id}: Failed - {result}")
        else:
            print(f"✓ Document {doc_id}: Confirmed at block {result['blockNumber']}")


if __name__ == "__main__":
    # Run examples
    asyncio.run(monitor_transaction_example())
    asyncio.run(check_status_example())
    asyncio.run(frontend_polling_pattern())
    # asyncio.run(multiple_transaction_monitoring())
