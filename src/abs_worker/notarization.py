"""
Core notarization logic for processing blockchain operations

This module contains the business logic for:
- Hash-only blockchain notarization
- NFT minting with Arweave storage
- Document status transitions
"""

import time
from abs_orm import get_session, DocumentRepository, DocStatus
from abs_blockchain import BlockchainClient
from abs_utils.logger import get_logger
from .monitoring import monitor_transaction
from .certificates import generate_signed_json, generate_signed_pdf
from .error_handler import handle_failed_transaction, retry_with_backoff

logger = get_logger(__name__)


async def process_hash_notarization(client: BlockchainClient, doc_id: int) -> None:
    """
    Process document for hash-only blockchain notarization

    Args:
        client: Blockchain client instance to use
        doc_id: Document ID to process

    Flow:
        1. Fetch Document from database
        2. Update status to PROCESSING
        3. Call blockchain to record hash
        4. Monitor transaction until confirmed
        5. Generate signed certificates (JSON + PDF)
        6. Update Document with transaction details and certificate paths
        7. Handle errors with retry logic

    Args:
        doc_id: Document ID to process

    Raises:
        Exception: If transaction permanently fails after all retries
    """
    logger.info(f"Starting hash notarization for document {doc_id}", extra={"doc_id": doc_id})

    async with get_session() as session:
        doc_repo = DocumentRepository(session)
        doc = await doc_repo.get(doc_id)

        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Validate document is in PENDING status
        if doc.status == DocStatus.PROCESSING:
            logger.warning(
                f"Document {doc_id} is already being processed, skipping",
                extra={"doc_id": doc_id},
            )
            return  # Exit gracefully for idempotency
        elif doc.status != DocStatus.PENDING:
            raise ValueError(
                f"Document {doc_id} is not in PENDING status (current: {doc.status.value})"
            )

        # Update status to PROCESSING (will be committed with final update)
        await doc_repo.update(doc_id, status=DocStatus.PROCESSING)
        logger.info(f"Document {doc_id} status updated to PROCESSING", extra={"doc_id": doc_id})

        try:
            # Record hash on blockchain with retry logic
            result = await retry_with_backoff(
                client.notarize_hash,
                file_hash=doc.file_hash,
                metadata={"file_name": doc.file_name, "timestamp": doc.created_at.isoformat()},
            )
            tx_hash = result.transaction_hash
            logger.info(
                f"Hash recorded on blockchain for document {doc_id}",
                extra={"doc_id": doc_id, "tx_hash": tx_hash},
            )

            # Monitor transaction with retry logic
            await retry_with_backoff(monitor_transaction, client, doc_id, tx_hash)
            logger.info(
                f"Transaction confirmed for document {doc_id}",
                extra={"doc_id": doc_id, "tx_hash": tx_hash},
            )

            # Generate certificates
            json_path = await generate_signed_json(doc)
            pdf_path = await generate_signed_pdf(doc)
            logger.info(
                f"Certificates generated for document {doc_id}",
                extra={"doc_id": doc_id, "json_path": json_path, "pdf_path": pdf_path},
            )

            # Mark as on-chain
            await doc_repo.update(
                doc_id,
                status=DocStatus.ON_CHAIN,
                transaction_hash=tx_hash,
                signed_json_path=json_path,
                signed_pdf_path=pdf_path,
            )
            await session.commit()

            logger.info(
                f"Hash notarization completed for document {doc_id}", extra={"doc_id": doc_id}
            )

        except Exception as e:
            logger.error(
                f"Hash notarization failed for document {doc_id}: {e}",
                extra={"doc_id": doc_id, "error": str(e)},
            )
            # Mark document as ERROR - this is called after retries are exhausted
            await handle_failed_transaction(doc_id, e)
            raise


async def process_nft_notarization(client: BlockchainClient, doc_id: int) -> None:
    """
    Process document for NFT minting with Arweave storage

    Args:
        client: Blockchain client instance to use
        doc_id: Document ID to process

    Flow:
        1. Fetch Document from database
        2. Update status to PROCESSING
        3. Call blockchain to mint NFT with automatic Arweave upload
        4. Monitor transaction until confirmed
        5. Generate signed certificates (JSON + PDF)
        6. Update Document with NFT details and certificate paths
        7. Handle errors with retry logic

    Raises:
        Exception: If transaction permanently fails after all retries
    """
    start_time = time.time()
    logger.info(f"Starting NFT notarization for document {doc_id}", extra={"doc_id": doc_id})

    async with get_session() as session:
        doc_repo = DocumentRepository(session)
        doc = await doc_repo.get(doc_id)

        if not doc:
            raise ValueError(f"Document {doc_id} not found")

        # Validate document is in PENDING status
        if doc.status == DocStatus.PROCESSING:
            logger.warning(
                f"Document {doc_id} is already being processed, skipping",
                extra={"doc_id": doc_id},
            )
            return  # Exit gracefully for idempotency
        elif doc.status != DocStatus.PENDING:
            raise ValueError(
                f"Document {doc_id} is not in PENDING status (current: {doc.status.value})"
            )

        # Update status to PROCESSING (will be committed with final update)
        await doc_repo.update(doc_id, status=DocStatus.PROCESSING)
        logger.info(f"Document {doc_id} status updated to PROCESSING", extra={"doc_id": doc_id})

        try:
            # Prepare NFT metadata (OpenSea compatible)
            metadata = {
                "name": f"Notarized {doc.file_name}",
                "description": f"Official blockchain notarization certificate for {doc.file_name}",
                "image": f"https://abs-notary.com/preview/{doc_id}.png",  # Optional
                "external_url": f"https://abs-notary.com/verify/{doc.file_hash}",
                "attributes": [
                    {
                        "trait_type": "Document Type",
                        "value": doc.type.value if doc.type else "Unknown",
                    },
                    {"trait_type": "File Hash", "value": doc.file_hash},
                    {"trait_type": "Notarization Date", "value": str(doc.created_at.date())},
                    {"trait_type": "Blockchain", "value": "Polygon"},
                ],
            }

            # Mint NFT with automatic Arweave upload (ONE CALL!)
            result = await retry_with_backoff(
                client.mint_nft_from_file,
                file_path=doc.file_path,
                file_hash=doc.file_hash,
                metadata=metadata,
            )

            tx_hash = result.transaction_hash
            token_id = result.token_id  # Returned by blockchain
            arweave_file_url = result.arweave_file_url  # Automatically uploaded!
            arweave_metadata_url = result.arweave_metadata_url  # Automatically uploaded!

            logger.info(
                f"NFT minted for document {doc_id}",
                extra={
                    "doc_id": doc_id,
                    "tx_hash": tx_hash,
                    "token_id": token_id,
                    "arweave_file_url": arweave_file_url,
                    "arweave_metadata_url": arweave_metadata_url,
                },
            )

            # Monitor transaction with retry logic
            await retry_with_backoff(monitor_transaction, client, doc_id, tx_hash)
            logger.info(
                f"Transaction confirmed for document {doc_id}",
                extra={"doc_id": doc_id, "tx_hash": tx_hash},
            )

            # Generate certificates
            json_path = await generate_signed_json(doc)
            pdf_path = await generate_signed_pdf(doc)
            logger.info(
                f"Certificates generated for document {doc_id}",
                extra={"doc_id": doc_id, "json_path": json_path, "pdf_path": pdf_path},
            )

            # Mark as on-chain with NFT details
            await doc_repo.update(
                doc_id,
                status=DocStatus.ON_CHAIN,
                transaction_hash=tx_hash,
                nft_token_id=token_id,
                arweave_file_url=arweave_file_url,
                arweave_metadata_url=arweave_metadata_url,
                signed_json_path=json_path,
                signed_pdf_path=pdf_path,
            )
            await session.commit()

            duration = time.time() - start_time
            logger.info(
                f"NFT notarization completed for document {doc_id}",
                extra={
                    "doc_id": doc_id,
                    "tx_hash": tx_hash,
                    "token_id": token_id,
                    "arweave_file_url": arweave_file_url,
                    "arweave_metadata_url": arweave_metadata_url,
                    "duration_seconds": round(duration, 2),
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"NFT notarization failed for document {doc_id}: {e}",
                extra={"doc_id": doc_id, "error": str(e), "duration_seconds": round(duration, 2)},
            )
            # Mark document as ERROR - this is called after retries are exhausted
            await handle_failed_transaction(doc_id, e)
            raise
