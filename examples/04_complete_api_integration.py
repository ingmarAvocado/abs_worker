"""
Example 4: Complete FastAPI API Integration

This shows a production-ready FastAPI application with:
- Document upload and notarization workflows
- User authentication (JWT placeholder)
- Status polling endpoints
- Certificate downloads
- Error handling middleware
- Health checks
- CORS configuration

This is how abs_api_server will use abs_worker.
"""

import asyncio
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# These will be real imports when integrated
# from abs_orm import get_session, DocumentRepository, UserRepository, DocType, DocStatus
# from abs_utils.logger import setup_logging, get_logger
from abs_worker import (
    process_hash_notarization,
    process_nft_notarization,
    get_settings
)

# logger = get_logger(__name__)
# setup_logging(level="INFO", log_format="json", service_name="abs_api_server")


# =============================================================================
# App Setup
# =============================================================================

app = FastAPI(
    title="ABS Notary API",
    description="Gasless blockchain notarization service",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Pydantic Models
# =============================================================================

class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    doc_id: int
    file_name: str
    file_hash: str
    status: str  # "pending"
    message: str


class DocumentStatusResponse(BaseModel):
    """Document status information"""
    doc_id: int
    file_name: str
    file_hash: str
    status: str  # pending, processing, on_chain, error
    type: str  # hash or nft
    transaction_hash: Optional[str] = None
    arweave_file_url: Optional[str] = None
    arweave_metadata_url: Optional[str] = None
    nft_token_id: Optional[int] = None
    signed_json_path: Optional[str] = None
    signed_pdf_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class NotarizeRequest(BaseModel):
    """Request to notarize a document"""
    doc_id: int
    type: str = "hash"  # "hash" or "nft"


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    worker_config: dict


# =============================================================================
# Dependency Injection (Auth, DB Session, etc.)
# =============================================================================

async def get_current_user(request: Request):
    """
    Extract and validate JWT token

    In real implementation:
    - Parse Authorization header
    - Validate JWT token
    - Return user object
    """
    # TODO: Implement real JWT auth
    # token = request.headers.get("Authorization", "").replace("Bearer ", "")
    # user = await validate_jwt_token(token)
    # return user

    # Stub for now
    class MockUser:
        id = 1
        email = "user@example.com"
        role = "user"

    return MockUser()


async def get_db_session():
    """
    Provide database session

    In real implementation:
    - Use abs_orm.get_session()
    - Yield session
    - Close on completion
    """
    # TODO: Use real abs_orm session
    # async with get_session() as session:
    #     yield session

    # Stub for now
    class MockSession:
        async def commit(self):
            pass
        async def rollback(self):
            pass

    yield MockSession()


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns service status and configuration info
    """
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        worker_config={
            "required_confirmations": settings.required_confirmations,
            "max_retries": settings.max_retries,
            "poll_interval": settings.poll_interval,
        }
    )


@app.post("/api/v1/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "hash",
    user = Depends(get_current_user),
    # session = Depends(get_db_session)
):
    """
    Upload a document for notarization

    Flow:
        1. Validate file (size, type)
        2. Calculate file hash (SHA-256)
        3. Check if hash already exists
        4. Save file to storage
        5. Create Document record in database (status=PENDING)
        6. Return document ID

    User will then call /documents/{doc_id}/sign to trigger notarization
    """
    # TODO: Implement real file upload
    # # Validate file
    # if file.size > 50 * 1024 * 1024:  # 50MB limit
    #     raise HTTPException(400, "File too large")

    # # Read file and calculate hash
    # file_content = await file.read()
    # file_hash = hashlib.sha256(file_content).hexdigest()

    # # Check if already exists
    # doc_repo = DocumentRepository(session)
    # if await doc_repo.file_hash_exists(file_hash):
    #     raise HTTPException(409, "File already notarized")

    # # Save file to storage
    # file_path = f"/var/abs_notary/files/{user.id}/{file_hash[:16]}_{file.filename}"
    # os.makedirs(os.path.dirname(file_path), exist_ok=True)
    # with open(file_path, 'wb') as f:
    #     f.write(file_content)

    # # Create document record
    # doc = await doc_repo.create(
    #     owner_id=user.id,
    #     file_name=file.filename,
    #     file_hash=f"0x{file_hash}",
    #     file_path=file_path,
    #     type=DocType.HASH if doc_type == "hash" else DocType.NFT,
    #     status=DocStatus.PENDING
    # )
    # await session.commit()

    # Stub response
    return DocumentUploadResponse(
        doc_id=123,
        file_name=file.filename,
        file_hash="0xabc123def456...",
        status="pending",
        message="Document uploaded successfully. Call /sign to notarize."
    )


@app.post("/api/v1/documents/{doc_id}/sign")
async def sign_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user),
    # session = Depends(get_db_session)
):
    """
    Trigger blockchain notarization for uploaded document

    Flow:
        1. Verify document exists and user owns it
        2. Verify document status is PENDING
        3. Enqueue background task based on document type
        4. Return 202 Accepted
        5. User polls /documents/{doc_id} for status updates
    """
    # TODO: Implement real validation
    # doc_repo = DocumentRepository(session)
    # doc = await doc_repo.get(doc_id)

    # if not doc:
    #     raise HTTPException(404, "Document not found")

    # if doc.owner_id != user.id:
    #     raise HTTPException(403, "Not authorized to sign this document")

    # if doc.status != DocStatus.PENDING:
    #     raise HTTPException(400, f"Document already {doc.status.value}")

    # # Enqueue appropriate background task
    # if doc.type == DocType.HASH:
    #     background_tasks.add_task(process_hash_notarization, doc_id)
    # else:
    #     background_tasks.add_task(process_nft_notarization, doc_id)

    # Stub implementation
    background_tasks.add_task(process_hash_notarization, doc_id)

    return {
        "message": "Notarization started",
        "doc_id": doc_id,
        "status": "processing"
    }


@app.get("/api/v1/documents/{doc_id}", response_model=DocumentStatusResponse)
async def get_document_status(
    doc_id: int,
    user = Depends(get_current_user),
    # session = Depends(get_db_session)
):
    """
    Get document status and details

    Frontend polls this endpoint every 2-3 seconds while status is "processing"

    Status transitions:
        pending → processing → on_chain
                           → error
    """
    # TODO: Implement real status check
    # doc_repo = DocumentRepository(session)
    # doc = await doc_repo.get(doc_id)

    # if not doc:
    #     raise HTTPException(404, "Document not found")

    # if doc.owner_id != user.id and user.role != "admin":
    #     raise HTTPException(403, "Not authorized")

    # return DocumentStatusResponse(
    #     doc_id=doc.id,
    #     file_name=doc.file_name,
    #     file_hash=doc.file_hash,
    #     status=doc.status.value,
    #     type=doc.type.value,
    #     transaction_hash=doc.transaction_hash,
    #     arweave_file_url=doc.arweave_file_url,
    #     arweave_metadata_url=doc.arweave_metadata_url,
    #     nft_token_id=doc.nft_token_id,
    #     signed_json_path=doc.signed_json_path,
    #     signed_pdf_path=doc.signed_pdf_path,
    #     error_message=doc.error_message,
    #     created_at=doc.created_at,
    #     updated_at=doc.updated_at
    # )

    # Stub response
    return DocumentStatusResponse(
        doc_id=doc_id,
        file_name="example.pdf",
        file_hash="0xabc123def456...",
        status="on_chain",
        type="hash",
        transaction_hash="0xtx123...",
        signed_json_path="/certs/cert_123.json",
        signed_pdf_path="/certs/cert_123.pdf",
        created_at=datetime.utcnow(),
    )


@app.get("/api/v1/documents/{doc_id}/certificate")
async def download_certificate(
    doc_id: int,
    format: str = "json",  # "json" or "pdf"
    user = Depends(get_current_user),
    # session = Depends(get_db_session)
):
    """
    Download notarization certificate

    Supports:
    - JSON format (machine-readable)
    - PDF format (human-readable with QR code)
    """
    # TODO: Implement real certificate download
    # doc_repo = DocumentRepository(session)
    # doc = await doc_repo.get(doc_id)

    # if not doc:
    #     raise HTTPException(404, "Document not found")

    # if doc.owner_id != user.id and user.role != "admin":
    #     raise HTTPException(403, "Not authorized")

    # if doc.status != DocStatus.ON_CHAIN:
    #     raise HTTPException(400, "Document not yet notarized")

    # if format == "json":
    #     if not doc.signed_json_path:
    #         raise HTTPException(404, "JSON certificate not found")
    #     return FileResponse(
    #         doc.signed_json_path,
    #         media_type="application/json",
    #         filename=f"certificate_{doc_id}.json"
    #     )
    # elif format == "pdf":
    #     if not doc.signed_pdf_path:
    #         raise HTTPException(404, "PDF certificate not found")
    #     return FileResponse(
    #         doc.signed_pdf_path,
    #         media_type="application/pdf",
    #         filename=f"certificate_{doc_id}.pdf"
    #     )
    # else:
    #     raise HTTPException(400, "Invalid format. Use 'json' or 'pdf'")

    # Stub response
    return {
        "message": "Certificate download would happen here",
        "doc_id": doc_id,
        "format": format
    }


@app.get("/api/v1/documents")
async def list_user_documents(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    user = Depends(get_current_user),
    # session = Depends(get_db_session)
):
    """
    List user's documents with pagination

    Filters:
    - status: pending, processing, on_chain, error

    Returns paginated list of documents
    """
    # TODO: Implement real document listing
    # doc_repo = DocumentRepository(session)

    # if status:
    #     docs = await doc_repo.get_user_documents(
    #         user.id,
    #         status=DocStatus(status),
    #         limit=limit,
    #         offset=skip
    #     )
    # else:
    #     docs = await doc_repo.get_user_documents(
    #         user.id,
    #         limit=limit,
    #         offset=skip
    #     )

    # total = await doc_repo.count(owner_id=user.id)

    # return {
    #     "documents": [DocumentStatusResponse.from_orm(doc) for doc in docs],
    #     "total": total,
    #     "skip": skip,
    #     "limit": limit
    # }

    # Stub response
    return {
        "documents": [],
        "total": 0,
        "skip": skip,
        "limit": limit
    }


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with logging"""
    # logger.warning(f"HTTP {exc.status_code}: {exc.detail}", extra={
    #     "path": request.url.path,
    #     "method": request.method
    # })

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler"""
    # logger.error(f"Unhandled exception: {exc}", extra={
    #     "path": request.url.path,
    #     "method": request.method
    # })

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500
        }
    )


# =============================================================================
# Startup/Shutdown Events
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # setup_logging(level="INFO", log_format="json", service_name="abs_api_server")
    # logger.info("ABS Notary API starting up")
    print("✓ ABS Notary API started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # logger.info("ABS Notary API shutting down")
    print("✓ ABS Notary API shutdown")


# =============================================================================
# Main (for running directly)
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    print("""
╔═══════════════════════════════════════════════════════╗
║       ABS Notary API - Complete Integration          ║
╚═══════════════════════════════════════════════════════╝

Starting FastAPI server with abs_worker integration...

Available endpoints:
  GET    /api/v1/health              - Health check
  POST   /api/v1/documents/upload    - Upload file
  POST   /api/v1/documents/{id}/sign - Trigger notarization
  GET    /api/v1/documents/{id}      - Get status
  GET    /api/v1/documents/{id}/cert - Download certificate
  GET    /api/v1/documents           - List documents

Try it:
  curl http://localhost:8000/api/v1/health

Docs:
  http://localhost:8000/docs

""")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
