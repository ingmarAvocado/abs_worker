# abs_orm Models Reference

Complete reference for all models, enums, and relationships in the abs_orm database layer.

## Table of Contents

1. [Enums](#enums)
2. [Models](#models)
3. [Relationships](#relationships)
4. [Database Schema](#database-schema)

---

## Enums

### UserRole

User permission levels in the system.

```python
from abs_orm.models import UserRole

# Values
UserRole.ADMIN  # "admin" - Full system access
UserRole.USER   # "user"  - Regular user, owns documents and API keys
```

### DocStatus

Document processing lifecycle states.

```python
from abs_orm.models import DocStatus

# Values
DocStatus.PENDING     # "pending"     - Awaiting processing
DocStatus.PROCESSING  # "processing"  - Currently being processed
DocStatus.ON_CHAIN    # "on_chain"    - Successfully notarized on blockchain
DocStatus.ERROR       # "error"       - Processing failed
```

### DocType

Types of document notarization.

```python
from abs_orm.models import DocType

# Values
DocType.HASH  # "hash" - File hash notarization
DocType.NFT   # "nft"  - NFT minting with Arweave storage
```

---

## Models

### User

Represents a user in the system with authentication and role management.

#### Fields

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| `id` | Integer | Primary Key | Unique user identifier |
| `email` | String(255) | Unique, Indexed | User email address |
| `hashed_password` | String(255) | Required | Bcrypt hashed password (never store plaintext) |
| `role` | Enum(UserRole) | Default: USER | User permission level |
| `created_at` | DateTime | Server default: now() | Account creation timestamp |

#### Relationships

- **documents**: One-to-Many with Document
  - A user can own multiple documents
  - Cascade delete: Deleting user deletes their documents

- **api_keys**: One-to-Many with ApiKey
  - A user can have multiple API keys
  - Cascade delete: Deleting user deletes their API keys

#### Example Usage

```python
from abs_orm.models import User, UserRole
from abs_orm import UserRepository, get_session
import bcrypt

async with get_session() as session:
    user_repo = UserRepository(session)

    # Create a regular user
    user = await user_repo.create(
        email="john@example.com",
        hashed_password=bcrypt.hashpw(b"secure_password", bcrypt.gensalt()).decode(),
        role=UserRole.USER
    )
    await session.commit()

    # Retrieve user by email
    user = await user_repo.get_by_email("john@example.com")

    # Get admin users
    admins = await user_repo.get_all_admins()

    # Promote user to admin
    await user_repo.promote_to_admin(user.id)
```

---

### Document

Represents a file to be notarized with blockchain storage information.

#### Fields

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| `id` | Integer | Primary Key | Unique document identifier |
| `file_name` | String(255) | Required | Original filename |
| `file_hash` | String(66) | Unique, Indexed | SHA-256 hash of file content |
| `file_path` | Text | Required | Local storage path to original file |
| `status` | Enum(DocStatus) | Default: PENDING | Current processing status |
| `type` | Enum(DocType) | Required | Document type (HASH or NFT) |
| `transaction_hash` | String(66) | Unique, Nullable | Ethereum transaction hash after notarization |
| `arweave_file_url` | Text | Nullable | Arweave URL for stored file (NFT only) |
| `arweave_metadata_url` | Text | Nullable | Arweave URL for metadata JSON (NFT only) |
| `nft_token_id` | Integer | Nullable | NFT token ID on blockchain (NFT only) |
| `signed_json_path` | Text | Nullable | Local path to signed JSON certificate |
| `signed_pdf_path` | Text | Nullable | Local path to signed PDF certificate |
| `error_message` | Text | Nullable | Error description if processing failed |
| `created_at` | DateTime | Server default: now() | Document creation timestamp |
| `updated_at` | DateTime | Server default: now(), Auto-update | Last modification timestamp |

#### Relationships

- **owner**: Many-to-One with User
  - Each document is owned by exactly one user
  - `owner_id` is the foreign key

#### Status Workflow

```
PENDING ──→ PROCESSING ──→ ON_CHAIN (success)
                    └──→ ERROR (failure)
```

#### Type-Specific Fields

**HASH Documents:**
- Require: `file_hash`, `transaction_hash`, `signed_json_path`, `signed_pdf_path`
- No Arweave or NFT fields

**NFT Documents:**
- Require: Everything from HASH plus:
  - `arweave_file_url`
  - `arweave_metadata_url`
  - `nft_token_id`

#### Example Usage

```python
from abs_orm.models import Document, DocStatus, DocType
from abs_orm import DocumentRepository, get_session

async with get_session() as session:
    doc_repo = DocumentRepository(session)

    # Create a pending document
    doc = await doc_repo.create(
        owner_id=user_id,
        file_name="contract.pdf",
        file_hash="0xabc123...",
        file_path="/storage/contracts/contract.pdf",
        type=DocType.HASH,
        status=DocStatus.PENDING
    )
    await session.commit()

    # Mark as processing
    await doc_repo.update_status(doc.id, DocStatus.PROCESSING)

    # Mark as on-chain with certificates
    await doc_repo.mark_as_on_chain(
        doc.id,
        transaction_hash="0x123def...",
        signed_json_path="/certs/1.json",
        signed_pdf_path="/certs/1.pdf"
    )

    # Get pending documents
    pending = await doc_repo.get_pending_documents(limit=10)

    # Get user's documents by status
    user_pending = await doc_repo.get_user_documents(
        user_id=user_id,
        status=DocStatus.PENDING
    )
```

---

### ApiKey

Represents an API key for programmatic access to the system.

#### Fields

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| `id` | Integer | Primary Key | Unique key identifier |
| `key_hash` | String(255) | Unique, Indexed | SHA-256 hash of the actual API key |
| `prefix` | String(100) | Required | Publicly visible key prefix (e.g., `sk_test_`) |
| `description` | Text | Nullable | Human-readable key description |
| `owner_id` | Integer | Foreign Key to User | User who owns this key |
| `created_at` | DateTime | Server default: now() | Key creation timestamp |
| `updated_at` | DateTime | Server default: now(), Auto-update | Last modification timestamp |

#### Relationships

- **owner**: Many-to-One with User
  - Each API key belongs to exactly one user
  - `owner_id` is the foreign key

#### Security Notes

- **Never store actual keys** - only store hashes
- **Show only the prefix to users** - e.g., `sk_test_abc123...` (truncated)
- **Hash with SHA-256** before storing
- **Revoke immediately** if compromised

#### Example Usage

```python
from abs_orm.models import ApiKey
from abs_orm import ApiKeyRepository, get_session
import hashlib

async with get_session() as session:
    key_repo = ApiKeyRepository(session)

    # Create API key (store actual key separately, hash for DB)
    actual_key = "sk_test_abc123def456"  # Generate and show to user once
    key_hash = hashlib.sha256(actual_key.encode()).hexdigest()

    api_key = await key_repo.create(
        owner_id=user_id,
        key_hash=key_hash,
        prefix="sk_test_abc123",
        description="Test API key for CI/CD"
    )
    await session.commit()

    # Validate incoming API key
    incoming_hash = hashlib.sha256(incoming_key.encode()).hexdigest()
    user = await key_repo.validate_api_key(incoming_hash)

    # Get user's API keys
    keys = await key_repo.get_user_api_keys(user_id)

    # Revoke a key
    await key_repo.revoke_api_key(api_key.id)

    # Revoke all keys for a user
    await key_repo.revoke_user_api_keys(user_id)
```

---

## Relationships

### User → Document (One-to-Many)

```
User (1) ──→ (Many) Document
    ↓
  documents (relationship)
```

```python
# Access user's documents
user = await user_repo.get_with_documents(user_id)
for doc in user.documents:
    print(f"Document: {doc.file_name}, Status: {doc.status}")

# Create document for user
doc = await doc_repo.create(
    owner_id=user.id,
    file_name="file.pdf",
    # ... other fields
)
```

### User → ApiKey (One-to-Many)

```
User (1) ──→ (Many) ApiKey
    ↓
  api_keys (relationship)
```

```python
# Access user's API keys
user = await user_repo.get_with_api_keys(user_id)
for key in user.api_keys:
    print(f"Key: {key.prefix}, Created: {key.created_at}")

# Create API key for user
api_key = await key_repo.create(
    owner_id=user.id,
    key_hash=hash_value,
    prefix="sk_test_"
)
```

---

## Database Schema

### Table: users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role userrole DEFAULT 'user' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT unique_email UNIQUE(email),
    CONSTRAINT idx_email INDEX(email)
);
```

### Table: documents

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_hash VARCHAR(66) UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    status docstatus DEFAULT 'pending' NOT NULL,
    type doctype NOT NULL,
    transaction_hash VARCHAR(66) UNIQUE,
    arweave_file_url TEXT,
    arweave_metadata_url TEXT,
    nft_token_id INTEGER,
    signed_json_path TEXT,
    signed_pdf_path TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT unique_file_hash UNIQUE(file_hash),
    CONSTRAINT unique_tx_hash UNIQUE(transaction_hash),
    CONSTRAINT idx_owner_id INDEX(owner_id),
    CONSTRAINT idx_status INDEX(status),
    CONSTRAINT idx_file_hash INDEX(file_hash)
);
```

### Table: api_keys

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    prefix VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT unique_key_hash UNIQUE(key_hash),
    CONSTRAINT idx_key_hash INDEX(key_hash),
    CONSTRAINT idx_owner_id INDEX(owner_id)
);
```

### Enums

```sql
CREATE TYPE userrole AS ENUM ('admin', 'user');
CREATE TYPE docstatus AS ENUM ('pending', 'processing', 'on_chain', 'error');
CREATE TYPE doctype AS ENUM ('hash', 'nft');
```

---

## Common Queries

### Get User with All Data

```python
user = await user_repo.get_with_documents(user_id)
api_keys = await key_repo.get_user_api_keys(user_id)

print(f"User: {user.email}")
print(f"Documents: {len(user.documents)}")
print(f"API Keys: {len(api_keys)}")
```

### Count Documents by Status

```python
pending = len(await doc_repo.get_pending_documents())
processing = len(await doc_repo.get_processing_documents())
on_chain = len(await doc_repo.get_by_status(DocStatus.ON_CHAIN))
errors = len(await doc_repo.get_error_documents())

print(f"Pending: {pending}, Processing: {processing}, On-Chain: {on_chain}, Errors: {errors}")
```

### Find User by Document

```python
doc = await doc_repo.get_by_id(doc_id)
user = await user_repo.get(doc.owner_id)
print(f"Document owner: {user.email}")
```

### Get Statistics

```python
user_stats = await user_repo.get_user_stats()
doc_stats = await doc_repo.get_document_stats()

print(f"Total users: {user_stats['total']}")
print(f"Total documents: {doc_stats['total']}")
```

---

## Type Safety

All models use SQLAlchemy with type hints for IDE support:

```python
from abs_orm import UserRepository, get_session
from abs_orm.models import User

async with get_session() as session:
    repo: UserRepository = UserRepository(session)
    user: Optional[User] = await repo.get(user_id)

    if user:
        email: str = user.email
        role: UserRole = user.role
        docs: List[Document] = user.documents
```

---

## Next Steps

- See [REPOSITORIES_REFERENCE.md](REPOSITORIES_REFERENCE.md) for all available repository methods
- See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for complete working examples
- See [CLAUDE.md](../CLAUDE.md) for quick start guide
