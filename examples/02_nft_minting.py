"""
Example 2: NFT minting with Arweave storage

This example demonstrates:
- NFT minting workflow
- Arweave file upload
- Complete NFT metadata generation
"""

import asyncio
from fastapi import FastAPI, BackgroundTasks
from abs_worker import process_nft_notarization

app = FastAPI()


@app.post("/documents/{doc_id}/mint-nft")
async def mint_document_nft(doc_id: int, background_tasks: BackgroundTasks):
    """
    Endpoint to trigger NFT minting for a document

    Flow:
        1. User uploads file with type="nft"
        2. User calls this endpoint to mint NFT
        3. Background task:
           - Uploads file to Arweave
           - Uploads metadata to Arweave
           - Mints NFT with metadata URI
        4. User polls /documents/{doc_id} to check status
    """
    # Validate document exists, is type NFT, and user owns it
    # (validation code omitted for brevity)

    # Enqueue NFT minting background task
    background_tasks.add_task(process_nft_notarization, doc_id)

    return {
        "message": "NFT minting started",
        "doc_id": doc_id,
        "status": "processing"
    }


@app.get("/documents/{doc_id}/nft-details")
async def get_nft_details(doc_id: int):
    """
    Get NFT-specific details for a minted document

    Returns:
        - Token ID
        - Arweave file URL
        - Arweave metadata URL
        - Transaction hash
        - OpenSea link (if on supported chain)
    """
    # TODO: Implement when abs_orm is available
    # async with get_session() as session:
    #     doc_repo = DocumentRepository(session)
    #     doc = await doc_repo.get(doc_id)
    #
    #     if doc.type != DocType.NFT:
    #         raise HTTPException(400, "Document is not an NFT")
    #
    #     return {
    #         "token_id": doc.nft_token_id,
    #         "arweave_file_url": doc.arweave_file_url,
    #         "arweave_metadata_url": doc.arweave_metadata_url,
    #         "transaction_hash": doc.transaction_hash,
    #         "opensea_url": f"https://opensea.io/assets/polygon/{contract_address}/{doc.nft_token_id}"
    #     }

    # Stub response
    return {
        "token_id": 123,
        "arweave_file_url": "https://arweave.net/file123",
        "arweave_metadata_url": "https://arweave.net/metadata123",
        "transaction_hash": "0xdef456...",
        "opensea_url": "https://opensea.io/assets/polygon/0x.../123"
    }


# Standalone usage example
async def standalone_example():
    """
    Example of NFT minting directly without FastAPI

    NFT Minting Flow:
        1. Document record exists in database
        2. File is stored locally at doc.file_path
        3. process_nft_notarization:
           - Reads file from disk
           - Uploads to Arweave → file_url
           - Creates metadata JSON
           - Uploads metadata to Arweave → metadata_url
           - Calls blockchain mint_nft(owner, token_id, metadata_url)
           - Monitors transaction
           - Updates document with all URLs and token_id
    """
    print("=== Standalone NFT Minting Example ===\n")

    # Simulate processing an NFT document
    doc_id = 456
    print(f"Minting NFT for document {doc_id}...")
    print("Steps:")
    print("  1. Upload file to Arweave")
    print("  2. Upload metadata to Arweave")
    print("  3. Mint NFT on blockchain")
    print("  4. Monitor transaction")
    print("  5. Generate certificates")
    print("  6. Update document\n")

    try:
        await process_nft_notarization(doc_id)
        print(f"✓ NFT minted successfully for document {doc_id}!")

    except Exception as e:
        print(f"✗ Error minting NFT for document {doc_id}: {e}")


async def batch_nft_minting_example():
    """
    Example of minting multiple NFTs in batch

    Useful for:
    - Admin tools
    - Migration scripts
    - Bulk operations
    """
    print("\n=== Batch NFT Minting Example ===\n")

    doc_ids = [1, 2, 3, 4, 5]
    print(f"Minting {len(doc_ids)} NFTs in parallel...")

    # Process all in parallel
    tasks = [process_nft_notarization(doc_id) for doc_id in doc_ids]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Report results
    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = len(results) - successful

    print(f"\n✓ Successfully minted: {successful}")
    print(f"✗ Failed: {failed}")

    # Show errors
    for doc_id, result in zip(doc_ids, results):
        if isinstance(result, Exception):
            print(f"  Document {doc_id}: {result}")


if __name__ == "__main__":
    # Run standalone examples
    asyncio.run(standalone_example())
    # asyncio.run(batch_nft_minting_example())

    # To run FastAPI server:
    # uvicorn examples.02_nft_minting:app --reload
