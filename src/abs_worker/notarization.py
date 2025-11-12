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
from .config import get_settings
from .monitoring import monitor_transaction
from .certificates import generate_signed_json, generate_signed_pdf
from .error_handler import handle_failed_transaction

logger = get_logger(__name__)


async def process_hash_notarization(doc_id: int) -> None:
    """
    Process document for hash-only blockchain notarization

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
    settings = get_settings()
    logger.info(f"Starting hash notarization for document {doc_id}", extra={"doc_id": doc_id})

    try:
        async with get_session() as session:
            doc_repo = DocumentRepository(session)
            doc = await doc_repo.get(doc_id)

            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            # Update status to PROCESSING
            await doc_repo.update(doc_id, status=DocStatus.PROCESSING)
            await session.commit()
            logger.info(f"Document {doc_id} status updated to PROCESSING", extra={"doc_id": doc_id})

            # Record hash on blockchain
            client = BlockchainClient()
            result = await client.notarize_hash(
                file_hash=doc.file_hash,
                metadata={
                    "file_name": doc.file_name,
                    "timestamp": doc.created_at.isoformat()
                }
            )
            tx_hash = result.transaction_hash
            logger.info(f"Hash recorded on blockchain for document {doc_id}", extra={"doc_id": doc_id, "tx_hash": tx_hash})

            # Monitor transaction
            await monitor_transaction(doc_id, tx_hash)
            logger.info(f"Transaction confirmed for document {doc_id}", extra={"doc_id": doc_id, "tx_hash": tx_hash})

            # Generate certificates
            json_path = await generate_signed_json(doc)
            pdf_path = await generate_signed_pdf(doc)
            logger.info(f"Certificates generated for document {doc_id}", extra={"doc_id": doc_id, "json_path": json_path, "pdf_path": pdf_path})

            # Mark as on-chain
            await doc_repo.update(
                doc_id,
                status=DocStatus.ON_CHAIN,
                transaction_hash=tx_hash,
                signed_json_path=json_path,
                signed_pdf_path=pdf_path
            )
            await session.commit()

            logger.info(f"Hash notarization completed for document {doc_id}", extra={"doc_id": doc_id})

    except Exception as e:
        logger.error(f"Hash notarization failed for document {doc_id}: {e}", extra={"doc_id": doc_id, "error": str(e)})
        await handle_failed_transaction(doc_id, e)
        raise


async def process_nft_notarization(doc_id: int) -> None:
    """
    Process document for NFT minting with Arweave storage

    Flow:
        1. Fetch Document from database
        2. Update status to PROCESSING
        3. Upload file to Arweave → get file URL
        4. Upload metadata to Arweave → get metadata URL
        5. Mint NFT on blockchain
        6. Monitor transaction until confirmed
        7. Generate signed certificates
        8. Update Document with all details (tx hash, Arweave URLs, token ID)
        9. Handle errors with retry logic

    Args:
        doc_id: Document ID to process

    Raises:
        Exception: If transaction permanently fails after all retries
    """
    # TODO: Implement when abs_orm and abs_blockchain are available
    # settings = get_settings()
    # logger.info(f"Starting NFT minting for document {doc_id}")

    # try:
    #     async with get_session() as session:
    #         doc_repo = DocumentRepository(session)
    #         doc = await doc_repo.get(doc_id)

    #         if not doc:
    #             raise ValueError(f"Document {doc_id} not found")

    #         # Update status to PROCESSING
    #         await doc_repo.update_status(doc_id, DocStatus.PROCESSING)
    #         await session.commit()

    #         # Upload file to Arweave
    #         with open(doc.file_path, 'rb') as f:
    #             file_url = await upload_to_arweave(f.read(), content_type='application/pdf')

    #         # Upload metadata to Arweave
    #         metadata = {
    #             "name": doc.file_name,
    #             "description": f"Notarized document: {doc.file_name}",
    #             "file_hash": doc.file_hash,
    #             "file_url": file_url,
    #             "timestamp": doc.created_at.isoformat()
    #         }
    #         metadata_url = await upload_to_arweave(
    #             json.dumps(metadata).encode(),
    #             content_type='application/json'
    #         )

    #         # Mint NFT
    #         owner_address = doc.owner.eth_address  # Assuming user has eth_address
    #         token_id = doc.id  # Simple token ID strategy
    #         tx_hash = await mint_nft(
    #             to_address=owner_address,
    #             token_id=token_id,
    #             metadata_uri=metadata_url
    #         )

    #         # Monitor transaction
    #         await monitor_transaction(doc_id, tx_hash)

    #         # Generate certificates
    #         json_path = await generate_signed_json(doc) if settings.cert_json_enabled else None
    #         pdf_path = await generate_signed_pdf(doc) if settings.cert_pdf_enabled else None

    #         # Mark as on-chain with NFT details
    #         await doc_repo.mark_as_on_chain(
    #             doc_id,
    #             transaction_hash=tx_hash,
    #             arweave_file_url=file_url,
    #             arweave_metadata_url=metadata_url,
    #             nft_token_id=token_id,
    #             signed_json_path=json_path,
    #             signed_pdf_path=pdf_path
    #         )
    #         await session.commit()

    #         logger.info(f"NFT minting completed for document {doc_id}")

    # except Exception as e:
    #     logger.error(f"NFT minting failed for document {doc_id}: {e}")
    #     await handle_failed_transaction(doc_id, e)
    #     raise

    # Stub implementation
    pass
