"""
Core notarization logic for processing blockchain operations

This module contains the business logic for:
- Hash-only blockchain notarization
- NFT minting with Arweave storage
- Document status transitions
"""

from abs_orm import get_session, DocumentRepository, DocStatus
from abs_blockchain import BlockchainClient
from abs_utils.logger import get_logger
from .monitoring import monitor_transaction
from .certificates import generate_signed_json, generate_signed_pdf
from .error_handler import handle_failed_transaction

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

    try:
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

            # Record hash on blockchain
            result = await client.notarize_hash(
                file_hash=doc.file_hash,
                metadata={"file_name": doc.file_name, "timestamp": doc.created_at.isoformat()},
            )
            tx_hash = result.transaction_hash
            logger.info(
                f"Hash recorded on blockchain for document {doc_id}",
                extra={"doc_id": doc_id, "tx_hash": tx_hash},
            )

            # Monitor transaction
            await monitor_transaction(client, doc_id, tx_hash)
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
        # Mark document as ERROR in a separate transaction before the original session rolls back
        async with get_session() as error_session:
            error_doc_repo = DocumentRepository(error_session)
            await error_doc_repo.update(doc_id, status=DocStatus.ERROR, error_message=str(e)[:500])
            await error_session.commit()
        logger.info(
            f"Document {doc_id} marked as ERROR due to notarization failure",
            extra={"doc_id": doc_id},
        )
        raise


async def process_nft_notarization(doc_id: int) -> None:
    """
    Process document for NFT minting with Arweave storage

    TODO: Implement NFT notarization workflow (separate feature)
    """
    raise NotImplementedError("NFT notarization not yet implemented")
