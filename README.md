# abs_worker

**Background task processor for blockchain operations in abs_notary**

## Overview

`abs_worker` is the asynchronous task processing layer for the abs_notary file notarization service. It handles blockchain operations that are too slow to run synchronously in API requests, including:

- File hash notarization on blockchain
- NFT minting with Arweave storage
- Transaction monitoring and confirmation polling
- Certificate generation (signed JSON and PDF)
- Error handling with automatic retry logic

## Why This Exists

Blockchain transactions can take seconds to minutes to confirm. Instead of blocking API requests, `abs_worker` processes these operations in the background while providing immediate responses to users.

## Architecture

**Phase 1 (MVP):** Business logic library used with FastAPI `BackgroundTasks`
- No message broker required
- Simple, lightweight implementation
- Perfect for development and small-scale production

**Phase 2 (Scale):** Same logic wrapped as Celery tasks
- Redis broker for task queue
- Task persistence and retry
- Distributed workers
- Production-scale throughput

The design allows you to start simple and scale when needed without rewriting business logic.

## Installation

**This project uses Poetry for dependency management.**

```bash
# Install poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Or just production dependencies
poetry install --only main

# Install with Celery support (Phase 2)
poetry install -E celery
```

## Quick Start

### Configuration

Create a `.env` file:

```env
# Blockchain settings
REQUIRED_CONFIRMATIONS=3
MAX_CONFIRMATION_WAIT=600

# Retry settings
MAX_RETRIES=3
RETRY_DELAY=5
RETRY_BACKOFF_MULTIPLIER=2.0

# Monitoring
POLL_INTERVAL=2
MAX_POLL_ATTEMPTS=100

# Storage
CERT_STORAGE_PATH=/var/abs_notary/certificates
```

### Phase 1: Using with FastAPI BackgroundTasks

```python
from fastapi import FastAPI, BackgroundTasks
from abs_worker import process_hash_notarization, process_nft_notarization

app = FastAPI()

@app.post("/documents/sign/{doc_id}")
async def sign_document(doc_id: int, background_tasks: BackgroundTasks):
    """Trigger blockchain notarization in background"""
    # Enqueue background task
    background_tasks.add_task(process_hash_notarization, doc_id)

    return {"status": "processing", "doc_id": doc_id}

@app.post("/documents/mint/{doc_id}")
async def mint_nft(doc_id: int, background_tasks: BackgroundTasks):
    """Mint NFT with Arweave storage in background"""
    background_tasks.add_task(process_nft_notarization, doc_id)

    return {"status": "processing", "doc_id": doc_id}
```

### Phase 2: Using with Celery (Future)

```python
from abs_worker.tasks import process_hash_notarization, process_nft_notarization

@app.post("/documents/sign/{doc_id}")
async def sign_document(doc_id: int):
    """Trigger blockchain notarization via Celery"""
    process_hash_notarization.delay(doc_id)
    return {"status": "processing"}
```

## Core Functions

### `process_hash_notarization(doc_id: int)`

Processes document for hash-only blockchain notarization.

**Flow:**
1. Fetch document from database
2. Update status to `PROCESSING`
3. Record hash on blockchain via `abs_blockchain.record_hash()`
4. Monitor transaction until confirmed
5. Generate signed certificates (JSON + PDF)
6. Update document: status=`ON_CHAIN`, transaction_hash, certificate paths
7. On error: retry or mark as `ERROR`

**Example:**
```python
from abs_worker import process_hash_notarization

# With FastAPI BackgroundTasks
background_tasks.add_task(process_hash_notarization, doc_id=123)
```

---

### `process_nft_notarization(doc_id: int)`

Processes document for NFT minting with Arweave storage.

**Flow:**
1. Fetch document from database
2. Update status to `PROCESSING`
3. Upload file to Arweave → get file URL
4. Upload metadata to Arweave → get metadata URL
5. Mint NFT via `abs_blockchain.mint_nft()`
6. Monitor transaction until confirmed
7. Generate signed certificates
8. Update document with all details
9. On error: retry or mark as `ERROR`

**Example:**
```python
from abs_worker import process_nft_notarization

# With FastAPI BackgroundTasks
background_tasks.add_task(process_nft_notarization, doc_id=456)
```

---

### `monitor_transaction(doc_id: int, tx_hash: str)`

Polls blockchain until transaction is confirmed.

**Parameters:**
- `doc_id` - Document ID to update
- `tx_hash` - Transaction hash to monitor

**Behavior:**
- Polls every `POLL_INTERVAL` seconds
- Waits for `REQUIRED_CONFIRMATIONS` blocks
- Times out after `MAX_CONFIRMATION_WAIT` seconds
- Handles reverted transactions

---

### `handle_failed_transaction(doc_id: int, error: Exception)`

Handles transaction failures with intelligent retry logic.

**Retryable Errors:**
- Network timeouts
- Gas estimation failures
- Nonce errors
- Connection errors

**Non-Retryable Errors:**
- Contract reverts
- Insufficient funds
- Invalid signatures
- Duplicate file hash

---

## Error Handling

All errors are logged with structured logging via `abs_utils`:

```python
# Automatic retry for temporary failures
# Logs include full context
{
  "level": "ERROR",
  "message": "Transaction failed, retrying",
  "extra": {
    "document_id": 123,
    "error": "Connection timeout",
    "retry_attempt": 1,
    "max_retries": 3
  }
}

# Permanent failures marked in database
{
  "level": "ERROR",
  "message": "Transaction permanently failed",
  "extra": {
    "document_id": 123,
    "error": "Contract execution reverted",
    "marked_as_error": true
  }
}
```

## Certificate Generation

Each notarized document gets two certificates:

### Signed JSON Certificate
```json
{
  "document_id": 123,
  "file_name": "contract.pdf",
  "file_hash": "0xabc123...",
  "transaction_hash": "0xdef456...",
  "block_number": 12345678,
  "timestamp": "2024-01-01T12:00:00Z",
  "type": "hash",
  "blockchain": "polygon",
  "signature": "0x...",
  "certificate_version": "1.0"
}
```

### Signed PDF Certificate
- Document details (name, hash, type)
- Blockchain proof (transaction hash, block number, timestamp)
- QR code linking to blockchain explorer
- Digital signature
- Arweave links (for NFT type)

## Project Structure

```
abs_worker/
├── src/abs_worker/
│   ├── __init__.py              # Public API
│   ├── config.py                # Pydantic settings
│   ├── notarization.py          # Core notarization logic
│   ├── monitoring.py            # Transaction monitoring
│   ├── error_handler.py         # Error handling & retry
│   ├── certificates.py          # Certificate generation
│   └── tasks.py                 # Celery task wrappers (Phase 2)
├── examples/
│   ├── 01_basic_usage.py        # Simple hash notarization
│   ├── 02_nft_minting.py        # NFT minting example
│   └── README.md
├── tests/
│   ├── conftest.py              # Test fixtures
│   ├── test_notarization.py    # Notarization tests
│   ├── test_monitoring.py       # Monitoring tests
│   ├── test_error_handler.py   # Error handling tests
│   └── test_certificates.py    # Certificate generation tests
├── pyproject.toml               # Package configuration
├── Makefile                     # Development commands
├── CLAUDE.md                    # LLM quick start guide
└── README.md                    # This file
```

## Development

**All development commands use Poetry:**

```bash
# Install dev dependencies
make dev-install
# Or: poetry install

# Run tests
make test
# Or: poetry run pytest -v

# Run tests in parallel
make test-parallel
# Or: poetry run pytest -n auto -v

# Format code
make format
# Or: poetry run black src tests

# Lint code
make lint
# Or: poetry run ruff check src tests && poetry run mypy src

# Clean build artifacts
make clean
```

## Testing

```bash
# Run all tests
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=abs_worker --cov-report=term-missing

# Run specific test file
poetry run pytest tests/test_notarization.py -v

# Run tests in parallel
poetry run pytest -n auto -v
```

## Integration with Other Libraries

**Dependencies:**
- `abs_orm` - Database models and repositories
- `abs_blockchain` - Blockchain operations (record_hash, mint_nft, Arweave uploads)
- `abs_utils` - Structured logging and utilities

**Used By:**
- `abs_api_server` - FastAPI endpoints enqueue background tasks

## Common Patterns

### Pattern 1: Hash Notarization API Endpoint
```python
from fastapi import FastAPI, BackgroundTasks, HTTPException
from abs_orm import DocumentRepository, get_session
from abs_worker import process_hash_notarization

@app.post("/documents/{doc_id}/notarize")
async def notarize_document(doc_id: int, background_tasks: BackgroundTasks):
    # Validate document exists and user owns it
    async with get_session() as session:
        doc_repo = DocumentRepository(session)
        doc = await doc_repo.get(doc_id)

        if not doc:
            raise HTTPException(404, "Document not found")

        # Enqueue background task
        background_tasks.add_task(process_hash_notarization, doc_id)

    return {"status": "processing", "doc_id": doc_id}
```

### Pattern 2: NFT Minting with Validation
```python
from fastapi import FastAPI, BackgroundTasks, HTTPException
from abs_orm import DocumentRepository, DocType, get_session
from abs_worker import process_nft_notarization

@app.post("/documents/{doc_id}/mint-nft")
async def mint_document_nft(doc_id: int, background_tasks: BackgroundTasks):
    async with get_session() as session:
        doc_repo = DocumentRepository(session)
        doc = await doc_repo.get(doc_id)

        if not doc:
            raise HTTPException(404, "Document not found")

        if doc.type != DocType.NFT:
            raise HTTPException(400, "Document type must be NFT")

        # Enqueue NFT minting
        background_tasks.add_task(process_nft_notarization, doc_id)

    return {"status": "processing", "doc_id": doc_id}
```

### Pattern 3: Status Polling (Frontend Integration)
```python
@app.get("/documents/{doc_id}/status")
async def get_document_status(doc_id: int):
    """Frontend polls this endpoint every 2-3 seconds"""
    async with get_session() as session:
        doc_repo = DocumentRepository(session)
        doc = await doc_repo.get(doc_id)

        if not doc:
            raise HTTPException(404, "Document not found")

        return {
            "status": doc.status,  # pending, processing, on_chain, error
            "transaction_hash": doc.transaction_hash,
            "signed_json_path": doc.signed_json_path,
            "signed_pdf_path": doc.signed_pdf_path,
            "error_message": doc.error_message,
        }
```

## Migration Path to Celery

When you need Celery for production scale:

1. **Install Celery extras:**
   ```bash
   poetry install -E celery
   ```

2. **Start Redis broker:**
   ```bash
   docker run -d -p 6379:6379 redis:alpine
   ```

3. **Start Celery worker:**
   ```bash
   poetry run celery -A abs_worker.tasks worker --loglevel=info
   ```

4. **Update API to use Celery:**
   ```python
   # Before (FastAPI BackgroundTasks)
   background_tasks.add_task(process_hash_notarization, doc_id)

   # After (Celery)
   from abs_worker.tasks import process_hash_notarization
   process_hash_notarization.delay(doc_id)
   ```

The business logic remains the same!

## License

MIT

## Links

- **Repository**: https://github.com/ingmarAvocado/abs_worker
- **Issues**: https://github.com/ingmarAvocado/abs_worker/issues
- **abs_notary Project**: Part of the abs_notary ecosystem
