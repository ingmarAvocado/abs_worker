# abs_worker Examples

Comprehensive examples showing how to use `abs_worker` for background processing of blockchain operations in the abs_notary system.

## 📋 Example Index

### Basic Usage
- **01_basic_usage.py** - Simple hash notarization with FastAPI BackgroundTasks
- **02_nft_minting.py** - NFT minting workflow with Arweave storage
- **03_status_monitoring.py** - Transaction monitoring and status polling

### Production Patterns
- **04_complete_api_integration.py** - Full FastAPI app with all endpoints
- **05_batch_operations.py** - Batch processing multiple documents
- **06_admin_cli.py** - Admin command-line tools
- **07_webhook_handler.py** - External webhook processing
- **08_error_recovery.py** - Error handling and retry strategies

## 🚀 Running Examples

All examples are **standalone** and will run even though abs_orm and abs_blockchain aren't implemented yet. They show the expected API usage patterns.

```bash
# Install dependencies
cd abs_worker
poetry install

# Run basic example
poetry run python examples/01_basic_usage.py

# Run FastAPI server example
poetry run uvicorn examples.04_complete_api_integration:app --reload

# Run admin CLI
poetry run python examples/06_admin_cli.py --help
```

## 📖 What Each Example Shows

### 01_basic_usage.py
**Purpose:** Introduction to abs_worker basics

**Shows:**
- FastAPI endpoint with BackgroundTasks
- Simple hash notarization
- Status polling endpoint
- Standalone usage without FastAPI

**Key Patterns:**
```python
@app.post("/documents/{doc_id}/notarize")
async def notarize(doc_id: int, bg: BackgroundTasks):
    bg.add_task(process_hash_notarization, doc_id)
    return {"status": "processing"}
```

---

### 02_nft_minting.py
**Purpose:** NFT minting workflow

**Shows:**
- NFT minting with Arweave uploads
- NFT-specific endpoints
- Batch NFT minting
- OpenSea integration links

**Key Patterns:**
```python
@app.post("/documents/{doc_id}/mint-nft")
async def mint_nft(doc_id: int, bg: BackgroundTasks):
    bg.add_task(process_nft_notarization, doc_id)
    return {"status": "processing"}
```

---

### 03_status_monitoring.py
**Purpose:** Transaction monitoring patterns

**Shows:**
- Monitoring transactions until confirmed
- Quick status checks
- Frontend polling patterns
- Multiple transaction monitoring

**Key Patterns:**
```python
# Frontend polling every 2 seconds
while status == "processing":
    status = await check_status(doc_id)
    await asyncio.sleep(2)
```

---

### 04_complete_api_integration.py
**Purpose:** Production-ready FastAPI application

**Shows:**
- Complete REST API with authentication
- Document upload workflow
- User-triggered notarization
- Certificate download endpoints
- Error handling middleware
- CORS configuration
- Health checks

**Endpoints:**
```
POST   /api/v1/documents/upload      # Upload file
POST   /api/v1/documents/{id}/sign   # Trigger notarization
GET    /api/v1/documents/{id}         # Get status
GET    /api/v1/documents/{id}/cert    # Download certificate
GET    /api/v1/health                 # Health check
```

---

### 05_batch_operations.py
**Purpose:** Batch processing workflows

**Shows:**
- Processing multiple documents in parallel
- Rate limiting and throttling
- Progress tracking
- Batch status reports
- Scheduled batch jobs

**Use Cases:**
- Nightly batch processing
- Migration scripts
- Admin bulk operations
- Retry failed documents

**Key Patterns:**
```python
# Process 100 documents in parallel with limit
async for batch in chunked(doc_ids, size=10):
    await asyncio.gather(*[process_hash(id) for id in batch])
```

---

### 06_admin_cli.py
**Purpose:** Command-line admin tools

**Shows:**
- CLI with argparse/click
- Manual document processing
- Status checking tools
- Batch retry commands
- Statistics and reporting

**Commands:**
```bash
# Process specific document
python admin_cli.py process --doc-id 123

# Retry all failed documents
python admin_cli.py retry-failed

# Get statistics
python admin_cli.py stats

# Monitor pending documents
python admin_cli.py monitor
```

---

### 07_webhook_handler.py
**Purpose:** External webhook integration

**Shows:**
- Webhook endpoint for external triggers
- Signature verification
- Async webhook processing
- Idempotency handling
- Webhook retry logic

**Use Cases:**
- Third-party notarization services
- API integrations
- Zapier/IFTTT workflows
- Payment gateway triggers

**Key Patterns:**
```python
@app.post("/webhooks/notarize")
async def handle_webhook(request: Request, bg: BackgroundTasks):
    # Verify signature
    # Extract document ID
    # Enqueue notarization
    return {"received": True}
```

---

### 08_error_recovery.py
**Purpose:** Error handling strategies

**Shows:**
- Retry logic for transient errors
- Dead letter queue patterns
- Circuit breaker implementation
- Graceful degradation
- Error notification

**Error Types Handled:**
- Network timeouts ✅ Retry
- Gas estimation failures ✅ Retry
- Insufficient funds ❌ No retry
- Contract reverts ❌ No retry
- Unknown errors ✅ Retry with caution

**Key Patterns:**
```python
try:
    await process_hash_notarization(doc_id)
except RetryableError as e:
    # Retry with backoff
    await retry_with_backoff(process_hash, doc_id)
except PermanentError as e:
    # Mark as failed, notify user
    await mark_as_failed(doc_id, str(e))
```

## 🏗️ Architecture Patterns

### Pattern 1: API Triggered (User Action)
```
User → API Endpoint → BackgroundTasks → Worker → Blockchain
                  ↓
            Return 202 Accepted
                  ↓
        User polls status endpoint
```

### Pattern 2: Scheduled Batch
```
Cron Job → CLI Script → Batch Worker → Multiple Docs in Parallel
                                    ↓
                          Generate Summary Report
```

### Pattern 3: Webhook Triggered
```
External Service → Webhook → Verify → BackgroundTasks → Worker
                         ↓
                   Return 200 OK
```

### Pattern 4: Admin Manual
```
Admin CLI → Direct Worker Call → Process Specific Doc
                             ↓
                    Show Progress in Terminal
```

## 🔧 Development Workflow

### Testing Examples

```bash
# Test config only (fast)
poetry run pytest tests/test_config.py -v

# Test with examples
poetry run python examples/01_basic_usage.py

# Test FastAPI app
poetry run uvicorn examples.04_complete_api_integration:app --reload
# Then: curl http://localhost:8000/api/v1/health
```

### Debugging Examples

All examples include verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run example and see detailed logs
await process_hash_notarization(doc_id)
```

## 📝 Implementation Status

| Example | Status | Notes |
|---------|--------|-------|
| 01_basic_usage.py | ✅ Working | Stub implementation |
| 02_nft_minting.py | ✅ Working | Stub implementation |
| 03_status_monitoring.py | ✅ Working | Stub implementation |
| 04_complete_api_integration.py | ✅ Working | Production-ready structure |
| 05_batch_operations.py | ✅ Working | Shows patterns |
| 06_admin_cli.py | ✅ Working | CLI framework |
| 07_webhook_handler.py | ✅ Working | Webhook patterns |
| 08_error_recovery.py | ✅ Working | Error strategies |

**Note:** All examples run successfully but use stub implementations. Real blockchain operations require abs_orm and abs_blockchain integration.

## 🔗 Integration with Other Libraries

These examples assume:
- **abs_orm** - Database models (User, Document, ApiKey)
- **abs_blockchain** - Blockchain operations (record_hash, mint_nft, Arweave)
- **abs_utils** - Structured logging and utilities

See the commented-out imports in each example for integration points.

## 💡 Best Practices Shown

1. **Always use BackgroundTasks** - Never block API responses
2. **Return immediately** - Give user a "processing" status
3. **Poll for status** - Frontend checks status endpoint
4. **Handle errors gracefully** - Retry transient errors, fail fast on permanent errors
5. **Log everything** - Use structured logging for debugging
6. **Generate certificates** - Always provide proof documents
7. **Test with stubs** - Develop API layer before blockchain integration

## 🚀 Production Deployment

When deploying examples to production:

1. **Update dependencies** - Uncomment real abs_orm and abs_blockchain imports
2. **Configure settings** - Set environment variables in .env
3. **Test integration** - Run integration tests
4. **Monitor workers** - Add health checks and monitoring
5. **Scale horizontally** - Use multiple worker processes
6. **Consider Celery** - Migrate to Celery for Phase 2 if needed

## 🤝 Contributing

Found a useful pattern? Add it as a new example!

Each example should:
- Be standalone and runnable
- Include detailed comments
- Show one clear pattern
- Have a descriptive name
- Include error handling
