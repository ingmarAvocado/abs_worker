# Mock Dependencies for abs_worker

This directory contains mock implementations of external dependencies used by abs_worker. These mocks define the interface contracts that the real implementations must follow.

## Overview

abs_worker depends on three external libraries:
- `abs_orm` - Database models and repositories
- `abs_blockchain` - Blockchain operations
- `abs_utils` - Utilities (logging, etc.)

These mocks allow:
- Running examples without real dependencies
- Writing unit tests for business logic
- Validating interface contracts

## abs_orm Interface Contracts

### DocumentRepository

```python
class DocumentRepository:
    async def get(self, doc_id: int) -> Document | None:
        """Get document by ID"""

    async def update(self, doc_id: int, **kwargs) -> Document:
        """Update document fields and return updated document"""

    async def create(self, doc_data: dict) -> Document:
        """Create new document and return it"""
```

### Document Model

```python
class Document:
    id: int
    file_name: str
    file_hash: str
    file_path: str  # For NFT minting
    status: DocStatus  # PENDING, PROCESSING, ON_CHAIN, ERROR
    type: DocType  # HASH, NFT
    transaction_hash: str | None
    arweave_file_url: str | None
    arweave_metadata_url: str | None
    nft_token_id: int | None
    error_message: str | None
    owner_id: int
    created_at: datetime
```

### Enums

```python
class DocStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ON_CHAIN = "on_chain"
    ERROR = "error"

class DocType(str, Enum):
    HASH = "hash"
    NFT = "nft"
```

### Database Session

```python
async def get_session() -> AsyncContextManager[AsyncSession]:
    """Async context manager for database sessions"""
```

## abs_blockchain Interface Contracts

### record_hash()

```python
async def record_hash(
    file_hash: str,
    metadata: dict
) -> str:  # Returns transaction hash
    """Record file hash on blockchain"""
```

### mint_nft()

```python
async def mint_nft(
    owner_address: str,
    token_id: int,
    metadata_url: str
) -> str:  # Returns transaction hash
    """Mint NFT on blockchain"""
```

### upload_to_arweave()

```python
async def upload_to_arweave(
    file_data: bytes,
    content_type: str
) -> str:  # Returns Arweave URL
    """Upload file to Arweave storage"""
```

### Transaction Receipt Format

```python
{
    "transactionHash": "0x...",
    "blockNumber": 12345678,
    "status": 1,  # 1 = success, 0 = reverted
    "confirmations": 3
}
```

### Exceptions

- `InsufficientFundsException`
- `ContractRevertedException`
- `GasEstimationException`
- `NetworkTimeoutException`

## abs_utils Interface Contracts

### Structured Logging

```python
from abs_utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Processing document", extra={"doc_id": 123})
```

### Exception Serialization

```python
try:
    # some operation
except Exception as e:
    error_dict = e.to_dict()  # Convert to dict for logging
```

## Usage in Tests

```python
import pytest
from tests.mocks.mock_orm import MockDocumentRepository, MockDocument
from tests.mocks.mock_blockchain import MockBlockchain

def test_some_business_logic(mock_document_repository, mock_blockchain):
    # Use mocks in tests
    pass
```

## Usage in Examples

```python
# Instead of importing real dependencies:
# from abs_orm import DocumentRepository, get_session
# from abs_blockchain import record_hash, mint_nft

# Import mocks:
from tests.mocks.mock_orm import MockDocumentRepository, get_session
from tests.mocks.mock_blockchain import MockBlockchain

# Use as drop-in replacements
blockchain = MockBlockchain()
repo = MockDocumentRepository()
```

## Mock vs Real Implementation

| Component | Mock Behavior | Real Implementation |
|-----------|---------------|-------------------|
| DocumentRepository.get() | Returns mock Document | Queries database |
| record_hash() | Returns fake tx hash | Calls blockchain contract |
| upload_to_arweave() | Returns fake URL | Uploads to Arweave |
| get_logger() | Prints to console | Structured JSON logging |

## Validation

Run contract validation tests:

```bash
poetry run pytest tests/unit/test_mocks.py -v
```

Verify examples work with mocks:

```bash
python examples/01_basic_usage.py
```