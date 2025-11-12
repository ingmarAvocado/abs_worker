# CLAUDE.md - Quick Start Guide for LLMs

## What This Is

`abs_worker` is the background task processor for the abs_notary file notarization service. It handles asynchronous blockchain operations that are too slow to run synchronously in API requests.

## Key Concepts

**Why This Exists:**
- Blockchain transactions take time (seconds to minutes) to confirm
- API endpoints can't block waiting for transactions
- Users need immediate responses while work happens in the background

**Architecture Strategy:**
- Business logic library used with FastAPI BackgroundTasks
- Async/await for non-blocking operations
- Built-in retry logic with exponential backoff

**Core Responsibilities:**
1. **Process hash notarizations** - Call blockchain to record file hashes
2. **Process NFT minting** - Upload to Arweave + mint NFT
3. **Poll for confirmations** - Wait for blockchain tx confirmations
4. **Update database** - Mark documents as on_chain or error
5. **Error handling & retry** - Automatic retry with exponential backoff

## Quick Examples

### FastAPI BackgroundTasks Integration

#### Business Logic Functions

```python
from abs_worker.notarization import process_hash_notarization, process_nft_notarization
from abs_worker.monitoring import check_transaction_status
from fastapi import BackgroundTasks

# In abs_api_server - enqueue background task
@router.post("/documents/sign/{doc_id}")
async def sign_document(doc_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_hash_notarization, doc_id)
    return {"status": "processing", "doc_id": doc_id}
```

#### Hash Notarization Flow

```python
from abs_worker import process_hash_notarization

# Called as background task
async def process_hash_notarization(doc_id: int):
    """
    1. Get document from database
    2. Update status to PROCESSING
    3. Call abs_blockchain.record_hash()
    4. Wait for transaction confirmation
    5. Update document with tx_hash, status=ON_CHAIN
    6. Generate signed certificates
    """
    # Implementation handles all steps automatically
    await process_hash_notarization(doc_id)
```

#### NFT Minting Flow

```python
from abs_worker import process_nft_notarization

# Called as background task
async def process_nft_notarization(doc_id: int):
    """
    1. Get document from database
    2. Update status to PROCESSING
    3. Upload file to Arweave
    4. Upload metadata to Arweave
    5. Call abs_blockchain.mint_nft()
    6. Wait for transaction confirmation
    7. Update document with tx_hash, arweave URLs, token_id, status=ON_CHAIN
    8. Generate signed certificates
    """
    # Implementation handles all steps automatically
    await process_nft_notarization(doc_id)
```

### Error Handling

```python
from abs_worker import handle_failed_transaction

# Automatically called on errors
async def handle_failed_transaction(doc_id: int, error: Exception):
    """
    1. Log error with context
    2. Check if retryable (gas errors, network issues)
    3. If retryable: retry with exponential backoff
    4. If not: mark document as ERROR with error_message
    """
    # Built-in retry logic with abs_utils logging
```

### Transaction Monitoring

```python
from abs_worker import monitor_transaction

# Background task to poll blockchain
async def monitor_transaction(doc_id: int, tx_hash: str):
    """
    1. Poll blockchain for transaction receipt
    2. Check if confirmed (enough blocks)
    3. Update document status when confirmed
    4. Handle reverted transactions
    """
    # Automatic polling with configurable intervals
```

## Module Structure

```
src/abs_worker/
├── __init__.py              # Public API exports
├── config.py                # Pydantic settings (retry config, timeouts, etc.)
├── notarization.py          # Core notarization logic
│   ├── process_hash_notarization()
│   ├── process_nft_notarization()
│   └── _upload_to_arweave()
├── monitoring.py            # Transaction monitoring
│   ├── monitor_transaction()
│   ├── check_transaction_status()
│   └── wait_for_confirmation()
├── error_handler.py         # Error handling & retry
│   ├── handle_failed_transaction()
│   ├── retry_with_backoff()
│   └── is_retryable_error()
├── certificates.py          # Certificate generation
│   ├── generate_signed_json()
│   ├── generate_signed_pdf()
│   └── _sign_certificate()
└── tasks.py                 # Task definitions (placeholder)
```

## Core Functions Reference

### `process_hash_notarization(doc_id: int)`
**Purpose:** Process document for hash-only blockchain notarization

**Flow:**
1. Fetch Document from abs_orm
2. Update status to PROCESSING
3. Call `abs_blockchain.record_hash(file_hash, metadata)`
4. Get transaction hash
5. Monitor transaction until confirmed
6. Generate signed JSON + PDF certificates
7. Update Document: status=ON_CHAIN, transaction_hash, certificate paths
8. If error: call `handle_failed_transaction()`

**Usage:**
```python
# From FastAPI endpoint
background_tasks.add_task(process_hash_notarization, doc_id)
```

---

### `process_nft_notarization(doc_id: int)`
**Purpose:** Process document for NFT minting with Arweave storage

**Flow:**
1. Fetch Document from abs_orm
2. Update status to PROCESSING
3. Upload file to Arweave → get file_url
4. Upload metadata JSON to Arweave → get metadata_url
5. Call `abs_blockchain.mint_nft(owner_address, token_id, metadata_url)`
6. Get transaction hash
7. Monitor transaction until confirmed
8. Generate signed JSON + PDF certificates
9. Update Document: status=ON_CHAIN, tx_hash, arweave URLs, token_id, certificates
10. If error: call `handle_failed_transaction()`

**Usage:**
```python
# From FastAPI endpoint
background_tasks.add_task(process_nft_notarization, doc_id)
```

---

### `monitor_transaction(doc_id: int, tx_hash: str, max_retries: int = 100)`
**Purpose:** Poll blockchain until transaction is confirmed

**Flow:**
1. Get transaction receipt from blockchain
2. Check if enough confirmations (e.g., 3 blocks)
3. If not confirmed yet: sleep and retry
4. If confirmed: return success
5. If reverted: raise error
6. If max_retries exceeded: raise timeout error

**Returns:** Transaction receipt when confirmed

---

### `handle_failed_transaction(doc_id: int, error: Exception)`
**Purpose:** Handle transaction failures with retry logic

**Flow:**
1. Log error with abs_utils structured logging
2. Check if error is retryable:
   - Gas estimation errors → retryable
   - Network timeouts → retryable
   - Contract reverts → NOT retryable
   - Insufficient funds → NOT retryable
3. If retryable: schedule retry with exponential backoff
4. If not retryable: mark Document as ERROR with error_message

**Retryable Errors:**
- Connection errors
- Gas estimation failures
- Timeout errors
- Nonce too low errors

**Non-Retryable Errors:**
- Contract execution reverted
- Insufficient funds
- Invalid signature
- File hash already exists

---

### `generate_signed_json(doc: Document) -> str`
**Purpose:** Generate signed JSON certificate for notarized document

**Returns:** Path to signed JSON file

**Format:**
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

---

### `generate_signed_pdf(doc: Document) -> str`
**Purpose:** Generate signed PDF certificate for notarized document

**Returns:** Path to signed PDF file

**Contains:**
- Document details (name, hash, type)
- Blockchain proof (tx_hash, block number, timestamp)
- QR code linking to blockchain explorer
- Digital signature
- Arweave links (for NFT type)

## Common Patterns

### Pattern 1: Simple Hash Notarization
```python
# User uploads file via API
# API stores file, creates Document record
# API enqueues background task

from fastapi import BackgroundTasks
from abs_worker import process_hash_notarization

@router.post("/documents/sign/{doc_id}")
async def sign_document(doc_id: int, bg: BackgroundTasks):
    # Validate ownership first
    # ...

    # Enqueue background task
    bg.add_task(process_hash_notarization, doc_id)

    return {"status": "processing"}
```

### Pattern 2: NFT Minting
```python
from fastapi import BackgroundTasks
from abs_worker import process_nft_notarization

@router.post("/documents/sign/{doc_id}")
async def sign_document(doc_id: int, bg: BackgroundTasks):
    # Validate ownership
    # ...

    # Enqueue NFT minting task
    bg.add_task(process_nft_notarization, doc_id)

    return {"status": "processing"}
```

### Pattern 3: Status Polling (Frontend)
```python
# Frontend polls this endpoint every 2 seconds
@router.get("/documents/{doc_id}")
async def get_document_status(doc_id: int):
    doc = await doc_repo.get(doc_id)

    return {
        "status": doc.status,  # pending, processing, on_chain, error
        "transaction_hash": doc.transaction_hash,
        "error_message": doc.error_message
    }
```

## Configuration

```python
# src/abs_worker/config.py
from pydantic_settings import BaseSettings

class WorkerSettings(BaseSettings):
    # Blockchain confirmation settings
    required_confirmations: int = 3
    max_confirmation_wait: int = 600  # seconds

    # Retry settings
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    retry_backoff_multiplier: float = 2.0

    # Transaction monitoring
    poll_interval: int = 2  # seconds
    max_poll_attempts: int = 100

    # Certificate settings
    cert_storage_path: str = "/var/abs_notary/certificates"

    class Config:
        env_file = ".env"
```

## Development Workflow

**This project uses Poetry for all commands.**

1. **Install dependencies**: `poetry install`
2. **Run tests**: `poetry run pytest -v` or `make test`
3. **Format code**: `poetry run black src tests` or `make format`
4. **Type checking**: `poetry run mypy src` or `make lint`


## Important Notes

- **Always use abs_utils logging** for structured JSON logs
- **Never block API requests** - always use background tasks
- **Always handle errors gracefully** - mark documents as ERROR with clear messages
- **Transaction monitoring is critical** - don't mark as on_chain until confirmed
- **Retry logic prevents user frustration** - temporary network issues shouldn't fail permanently
- **Certificate generation is mandatory** - users need proof documents

## Integration with Other Libraries

**Uses:**
- `abs_orm` - Database models, repositories, session management
- `abs_blockchain` - Blockchain operations (record_hash, mint_nft, upload to Arweave)
- `abs_utils` - Structured logging, error handling utilities

**Used by:**
- `abs_api_server` - FastAPI endpoints enqueue tasks here

## Next Steps

This library provides the business logic for background processing using FastAPI BackgroundTasks.

Check `abs_api_server` for integration examples of how endpoints enqueue these tasks.
