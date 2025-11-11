"""
Example 1: Basic hash notarization with FastAPI BackgroundTasks

This example demonstrates:
- Setting up abs_worker configuration
- Processing hash notarization in background
- Using with FastAPI BackgroundTasks
"""

import asyncio
from fastapi import FastAPI, BackgroundTasks
from abs_worker import process_hash_notarization, get_settings

app = FastAPI()


@app.post("/documents/{doc_id}/notarize")
async def notarize_document(doc_id: int, background_tasks: BackgroundTasks):
    """
    Endpoint to trigger hash notarization for a document

    Flow:
        1. User uploads file via /documents/upload (creates doc record)
        2. User calls this endpoint to notarize
        3. Background task processes blockchain transaction
        4. User polls /documents/{doc_id} to check status
    """
    # Validate document exists and user owns it
    # (validation code omitted for brevity)

    # Enqueue background task
    background_tasks.add_task(process_hash_notarization, doc_id)

    return {
        "message": "Document notarization started",
        "doc_id": doc_id,
        "status": "processing"
    }


@app.get("/documents/{doc_id}")
async def get_document_status(doc_id: int):
    """
    Poll endpoint for frontend to check document status

    Frontend should poll this every 2-3 seconds while status is "processing"
    """
    # TODO: Implement when abs_orm is available
    # async with get_session() as session:
    #     doc_repo = DocumentRepository(session)
    #     doc = await doc_repo.get(doc_id)
    #
    #     return {
    #         "doc_id": doc.id,
    #         "file_name": doc.file_name,
    #         "status": doc.status.value,
    #         "transaction_hash": doc.transaction_hash,
    #         "signed_json_path": doc.signed_json_path,
    #         "signed_pdf_path": doc.signed_pdf_path,
    #         "error_message": doc.error_message
    #     }

    # Stub response
    return {
        "doc_id": doc_id,
        "file_name": "example.pdf",
        "status": "on_chain",
        "transaction_hash": "0xabc123...",
        "signed_json_path": "/certs/cert_1.json",
        "signed_pdf_path": "/certs/cert_1.pdf"
    }


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

    # Load settings
    settings = get_settings()
    print(f"Required confirmations: {settings.required_confirmations}")
    print(f"Max retries: {settings.max_retries}\n")

    # Simulate processing a document
    doc_id = 123
    print(f"Processing document {doc_id}...")

    try:
        await process_hash_notarization(doc_id)
        print(f"✓ Document {doc_id} notarized successfully!")

    except Exception as e:
        print(f"✗ Error notarizing document {doc_id}: {e}")


if __name__ == "__main__":
    # Run standalone example
    asyncio.run(standalone_example())

    # To run FastAPI server:
    # uvicorn examples.01_basic_usage:app --reload
