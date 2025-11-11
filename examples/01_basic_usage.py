"""
Example 1: Basic hash notarization with FastAPI BackgroundTasks

This example demonstrates:
- Setting up abs_worker configuration
- Processing hash notarization in background
- Using with FastAPI BackgroundTasks
"""

import asyncio
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

# abs_notary imports
from abs_worker import process_hash_notarization, get_settings
from abs_orm import get_session, DocumentRepository, DocStatus, DocType
from abs_utils.logger import setup_logging, get_logger, LoggingMiddleware
from abs_utils.exceptions import DocumentNotFoundException

# Setup logging
setup_logging(level="INFO", log_format="json", service_name="abs_worker_example")
logger = get_logger(__name__)

app = FastAPI()
app.add_middleware(LoggingMiddleware)  # Auto-log all requests


@app.post("/documents/{doc_id}/notarize")
async def notarize_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Endpoint to trigger hash notarization for a document

    Flow:
        1. User uploads file via /documents/upload (creates doc record)
        2. User calls this endpoint to notarize
        3. Background task processes blockchain transaction
        4. User polls /documents/{doc_id} to check status
    """
    logger.info(f"Notarization requested for document {doc_id}")

    # Validate document exists
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get(doc_id)

    if not doc:
        logger.warning(f"Document {doc_id} not found")
        raise DocumentNotFoundException(doc_id=doc_id)

    # Validate status is pending
    if doc.status != DocStatus.PENDING:
        raise HTTPException(
            400,
            f"Document already {doc.status.value}, cannot re-notarize"
        )

    # Enqueue background task
    background_tasks.add_task(process_hash_notarization, doc_id)
    logger.info(f"Background task enqueued for document {doc_id}")

    return {
        "message": "Document notarization started",
        "doc_id": doc_id,
        "status": "processing"
    }


@app.get("/documents/{doc_id}")
async def get_document_status(
    doc_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Poll endpoint for frontend to check document status

    Frontend should poll this every 2-3 seconds while status is "processing"
    """
    logger.debug(f"Status check for document {doc_id}")

    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get(doc_id)

    if not doc:
        raise DocumentNotFoundException(doc_id=doc_id)

    return {
        "doc_id": doc.id,
        "file_name": doc.file_name,
        "file_hash": doc.file_hash,
        "status": doc.status.value,
        "type": doc.type.value,
        "transaction_hash": doc.transaction_hash,
        "signed_json_path": doc.signed_json_path,
        "signed_pdf_path": doc.signed_pdf_path,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat() if doc.created_at else None
    }


# Exception handler
@app.exception_handler(DocumentNotFoundException)
async def handle_document_not_found(request, exc: DocumentNotFoundException):
    """Handle DocumentNotFoundException gracefully"""
    return JSONResponse(
        status_code=404,
        content=exc.to_dict()
    )


# Standalone usage example
async def standalone_example():
    """
    Example of calling notarization directly without FastAPI

    This is useful for:
    - Testing
    - CLI tools
    - Background workers separate from API server
    """
    print("=== Standalone Hash Notarization Example ===\n")

    logger.info("Starting standalone example")

    # Load settings
    settings = get_settings()
    print(f"Required confirmations: {settings.required_confirmations}")
    print(f"Max retries: {settings.max_retries}\n")

    # Simulate processing a document
    doc_id = 123
    print(f"Processing document {doc_id}...")

    try:
        # In real usage, this would process the actual document
        await process_hash_notarization(doc_id)
        print(f"✓ Document {doc_id} notarized successfully!")
        logger.info(f"Document {doc_id} notarized", extra={"doc_id": doc_id})

    except DocumentNotFoundException as e:
        print(f"✗ Document not found: {e}")
        logger.error(f"Document not found: {e}", extra=e.to_dict())

    except Exception as e:
        print(f"✗ Error notarizing document {doc_id}: {e}")
        logger.error(f"Notarization failed", extra={"doc_id": doc_id, "error": str(e)})


if __name__ == "__main__":
    # Run standalone example
    asyncio.run(standalone_example())

    # To run FastAPI server:
    # uvicorn examples.01_basic_usage:app --reload
