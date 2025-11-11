# abs_worker Examples

These examples demonstrate how to use `abs_worker` for background processing of blockchain operations.

## Examples

1. **01_basic_usage.py** - Simple hash notarization with FastAPI BackgroundTasks
2. **02_nft_minting.py** - NFT minting workflow example
3. **03_status_monitoring.py** - Polling document status from frontend

## Running Examples

```bash
# Make sure dependencies are installed
poetry install

# Run an example
poetry run python examples/01_basic_usage.py
```

## Prerequisites

All examples assume:
- `abs_orm` is properly configured with database connection
- `abs_blockchain` is configured with blockchain RPC and hot wallet
- Required environment variables are set in `.env`

## Integration with FastAPI

The examples show standalone usage, but in production these functions
are called from FastAPI endpoints as background tasks:

```python
from fastapi import FastAPI, BackgroundTasks
from abs_worker import process_hash_notarization

app = FastAPI()

@app.post("/documents/{doc_id}/sign")
async def sign_document(doc_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_hash_notarization, doc_id)
    return {"status": "processing"}
```

See `abs_api_server` repository for complete API integration examples.
