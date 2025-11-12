"""
Example 2: NFT minting with mock blockchain and Arweave

This example demonstrates:
- NFT minting workflow using mocks
- Mock Arweave file upload
- Mock NFT metadata generation
- Complete NFT creation flow
"""

import asyncio
import json
from tests.mocks.mock_orm import create_mock_nft_document as create_nft_document, DocStatus
from tests.mocks.mock_blockchain import MockBlockchain
from tests.mocks.mock_utils import get_logger


async def nft_minting_workflow():
    """
    Demonstrate complete NFT minting workflow using mocks
    """
    print("=== NFT Minting Workflow Example ===\n")

    logger = get_logger("nft_example")

    # Create an NFT document
    nft_doc = create_nft_document(
        id=100,
        file_name="artwork.png",
        file_hash="0xnft987654321fedcba",
        file_path="/tmp/artwork.png"
    )

    print(f"Created NFT document: {nft_doc.file_name}")
    print(f"Document type: {nft_doc.type.value}")
    print(f"Initial status: {nft_doc.status.value}\n")

    # Initialize mock blockchain
    blockchain = MockBlockchain()

    # Step 1: Upload file to Arweave
    print("Step 1: Uploading file to Arweave...")
    # Use mock file data instead of reading from disk
    file_data = b"Mock PNG file content for NFT artwork"

    file_url = await blockchain.upload_to_arweave(file_data, "image/png")
    print(f"✓ File uploaded to: {file_url}")
    logger.info("File uploaded to Arweave", extra={"file_url": file_url})

    # Step 2: Create and upload metadata
    print("\nStep 2: Creating NFT metadata...")
    metadata = {
        "name": f"Notarized Document: {nft_doc.file_name}",
        "description": "A legally notarized document stored on blockchain",
        "image": file_url,
        "attributes": [
            {"trait_type": "Document Type", "value": "NFT"},
            {"trait_type": "File Hash", "value": nft_doc.file_hash},
            {"trait_type": "Notarization Date", "value": "2024-01-01"}
        ]
    }

    metadata_json = json.dumps(metadata, indent=2)
    metadata_url = await blockchain.upload_to_arweave(
        metadata_json.encode('utf-8'),
        "application/json"
    )
    print(f"✓ Metadata uploaded to: {metadata_url}")
    logger.info("Metadata uploaded to Arweave", extra={"metadata_url": metadata_url})

    # Step 3: Mint NFT
    print("\nStep 3: Minting NFT...")
    owner_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    token_id = 1

    mint_tx = await blockchain.mint_nft(owner_address, token_id, metadata_url)
    print(f"✓ NFT minted! Transaction: {mint_tx}")
    logger.info("NFT minted successfully", extra={
        "tx_hash": mint_tx,
        "token_id": token_id,
        "owner": owner_address
    })

    # Step 4: Wait for confirmations
    print("\nStep 4: Waiting for transaction confirmations...")
    receipt = await blockchain.wait_for_confirmations(mint_tx, required_confirmations=3)
    print(f"✓ Transaction confirmed in block {receipt['blockNumber']}")
    print(f"Confirmations: {receipt['confirmations']}")

    # Step 5: Update document with results
    print("\nStep 5: Updating document record...")
    nft_doc.status = DocStatus.ON_CHAIN
    nft_doc.transaction_hash = mint_tx
    nft_doc.arweave_file_url = file_url
    nft_doc.arweave_metadata_url = metadata_url
    nft_doc.nft_token_id = token_id

    print("✓ Document updated with notarization details")
    print(f"Final status: {nft_doc.status.value}")
    print(f"NFT Token ID: {nft_doc.nft_token_id}")
    print(f"Transaction: {nft_doc.transaction_hash}")
    print(f"Arweave file: {nft_doc.arweave_file_url}")
    print(f"Arweave metadata: {nft_doc.arweave_metadata_url}")

    return nft_doc


async def error_scenarios():
    """
    Demonstrate error handling in NFT minting
    """
    print("\n=== Error Handling Scenarios ===\n")

    from tests.mocks.mock_blockchain import ContractRevertedException

    blockchain = MockBlockchain()
    logger = get_logger("nft_errors")

    # Simulate contract revert
    blockchain.set_next_transaction_failure(
        ContractRevertedException("Insufficient funds for NFT minting")
    )

    try:
        await blockchain.mint_nft("0x123", 1, "https://arweave.net/abc")
    except ContractRevertedException as e:
        print(f"✗ NFT minting failed: {e}")
        logger.error("NFT minting failed", extra={"error": str(e)})


async def main():
    """
    Run NFT minting examples
    """
    print("NFT Minting Examples with Mock Dependencies")
    print("=" * 50)

    await nft_minting_workflow()
    await error_scenarios()

    print("\n✓ NFT examples completed!")
    print("\nNote: In production, replace mock imports with real blockchain/Arweave clients")


if __name__ == "__main__":
    asyncio.run(main())
