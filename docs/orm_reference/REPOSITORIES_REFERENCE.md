# abs_orm Repositories Reference

Complete reference for all repository methods and patterns in abs_orm.

## Table of Contents

1. [Overview](#overview)
2. [BaseRepository](#baserepository)
3. [UserRepository](#userrepository)
4. [DocumentRepository](#documentrepository)
5. [ApiKeyRepository](#apikeyrepository)
6. [Common Patterns](#common-patterns)

---

## Overview

Repositories provide a clean abstraction layer for database operations. Each repository:

- Is async/await based with SQLAlchemy
- Includes automatic structured logging (via abs_utils)
- Is type-safe with generics
- Handles entity lifecycle (CRUD operations)

### Setup

```python
from abs_orm import get_session, UserRepository, DocumentRepository, ApiKeyRepository

async with get_session() as session:
    user_repo = UserRepository(session)
    doc_repo = DocumentRepository(session)
    key_repo = ApiKeyRepository(session)

    # Use repositories...

    await session.commit()  # Always commit at the end
```

---

## BaseRepository

Base class with generic CRUD operations. All repositories inherit these methods.

### Create

```python
async def create(**kwargs) -> T
```

Create a new entity and add it to the session.

```python
user = await user_repo.create(
    email="user@example.com",
    hashed_password="hashed_pwd",
    role=UserRole.USER
)
# Returns User instance (not yet persisted until commit)
```

### Get

```python
async def get(id: int) -> Optional[T]
```

Get entity by primary key.

```python
user = await user_repo.get(user_id)
if user:
    print(f"Found: {user.email}")
else:
    print("User not found")
```

### Get All

```python
async def get_all(limit: Optional[int] = None, offset: Optional[int] = None) -> List[T]
```

Get all entities with optional pagination.

```python
# Get all users
all_users = await user_repo.get_all()

# Get first 10 users
first_page = await user_repo.get_all(limit=10, offset=0)

# Get next 10 users
second_page = await user_repo.get_all(limit=10, offset=10)
```

### Get By

```python
async def get_by(field: str, value: Any) -> Optional[T]
```

Get single entity by field value.

```python
user = await user_repo.get_by("email", "user@example.com")
doc = await doc_repo.get_by("file_hash", "0xabc123...")
api_key = await key_repo.get_by("key_hash", "hash_value")
```

### Filter By

```python
async def filter_by(**kwargs) -> List[T]
```

Get multiple entities matching field values.

```python
# Get all admins
admins = await user_repo.filter_by(role=UserRole.ADMIN)

# Get all pending documents
pending = await doc_repo.filter_by(status=DocStatus.PENDING)

# Multiple conditions (AND logic)
hash_docs = await doc_repo.filter_by(type=DocType.HASH, status=DocStatus.ON_CHAIN)
```

### Update

```python
async def update(id: int, **kwargs) -> Optional[T]
```

Update entity by ID. Returns updated entity or None if not found.

```python
updated_user = await user_repo.update(user_id, email="newemail@example.com")
if updated_user:
    print("Email updated")
else:
    print("User not found")
```

### Delete

```python
async def delete(id: int) -> bool
```

Delete entity by ID. Returns True if deleted, False if not found.

```python
deleted = await user_repo.delete(user_id)
if deleted:
    print("User deleted")
else:
    print("User not found")
```

### Exists

```python
async def exists(id: int) -> bool
```

Check if entity exists by ID.

```python
if await user_repo.exists(user_id):
    print("User exists")
```

### Exists By

```python
async def exists_by(field: str, value: Any) -> bool
```

Check if entity exists by field value.

```python
if await user_repo.exists_by("email", "user@example.com"):
    print("Email already registered")
```

### Count

```python
async def count(**kwargs) -> int
```

Count entities matching criteria.

```python
total_users = await user_repo.count()
admin_count = await user_repo.count(role=UserRole.ADMIN)
pending_docs = await doc_repo.count(status=DocStatus.PENDING)
```

### Bulk Create

```python
async def bulk_create(data: List[Dict[str, Any]]) -> List[T]
```

Create multiple entities in one call.

```python
users_data = [
    {"email": "user1@example.com", "hashed_password": "hash1", "role": UserRole.USER},
    {"email": "user2@example.com", "hashed_password": "hash2", "role": UserRole.USER},
]
created_users = await user_repo.bulk_create(users_data)
```

### First

```python
async def first(**kwargs) -> Optional[T]
```

Get first entity matching criteria.

```python
first_admin = await user_repo.first(role=UserRole.ADMIN)
```

### Get Paginated

```python
async def get_paginated(page: int, page_size: int) -> List[T]
```

Get paginated results (page 1-indexed).

```python
page_1 = await user_repo.get_paginated(page=1, page_size=10)
page_2 = await user_repo.get_paginated(page=2, page_size=10)
```

---

## UserRepository

User-specific operations. Inherits all BaseRepository methods.

### Get By Email

```python
async def get_by_email(email: str) -> Optional[User]
```

Get user by email address.

```python
user = await user_repo.get_by_email("user@example.com")
```

### Email Exists

```python
async def email_exists(email: str) -> bool
```

Check if email is already registered.

```python
if await user_repo.email_exists("user@example.com"):
    raise ValueError("Email already registered")
```

### Get All Admins

```python
async def get_all_admins() -> List[User]
```

Get all admin users.

```python
admins = await user_repo.get_all_admins()
for admin in admins:
    print(f"Admin: {admin.email}")
```

### Get All Regular Users

```python
async def get_all_regular_users() -> List[User]
```

Get all non-admin users.

```python
regular_users = await user_repo.get_all_regular_users()
```

### Is Admin

```python
async def is_admin(user_id: int) -> bool
```

Check if user has admin role.

```python
if await user_repo.is_admin(user_id):
    print("User is an administrator")
```

### Promote To Admin

```python
async def promote_to_admin(user_id: int) -> bool
```

Give admin privileges to a user. Returns True if successful.

```python
if await user_repo.promote_to_admin(user_id):
    print("User promoted to admin")
else:
    print("User not found")
```

### Demote To User

```python
async def demote_to_user(user_id: int) -> bool
```

Remove admin privileges from a user. Returns True if successful.

```python
if await user_repo.demote_to_user(user_id):
    print("Admin demoted to regular user")
```

### Get Users By Role

```python
async def get_users_by_role(role: UserRole) -> List[User]
```

Get all users with specific role.

```python
admins = await user_repo.get_users_by_role(UserRole.ADMIN)
users = await user_repo.get_users_by_role(UserRole.USER)
```

### Count By Role

```python
async def count_by_role(role: UserRole) -> int
```

Count users with specific role.

```python
admin_count = await user_repo.count_by_role(UserRole.ADMIN)
print(f"Total admins: {admin_count}")
```

### Get Recent Users

```python
async def get_recent_users(days: int = 7) -> List[User]
```

Get users created in the last N days.

```python
new_users = await user_repo.get_recent_users(days=7)
very_new = await user_repo.get_recent_users(days=1)
```

### Search By Email

```python
async def search_by_email(pattern: str) -> List[User]
```

Search users by email pattern (case-insensitive).

```python
matches = await user_repo.search_by_email("john")
# Returns users with "john" in their email
```

### Get With API Keys

```python
async def get_with_api_keys(user_id: int) -> Optional[User]
```

Get user with API keys eagerly loaded (avoids N+1 queries).

```python
user = await user_repo.get_with_api_keys(user_id)
for key in user.api_keys:
    print(f"API Key: {key.prefix}")
```

### Get With Documents

```python
async def get_with_documents(user_id: int) -> Optional[User]
```

Get user with documents eagerly loaded.

```python
user = await user_repo.get_with_documents(user_id)
for doc in user.documents:
    print(f"Document: {doc.file_name} ({doc.status})")
```

### Update Password

```python
async def update_password(user_id: int, hashed_password: str) -> bool
```

Update user's hashed password. Returns True if successful.

```python
new_hash = bcrypt.hashpw(b"new_password", bcrypt.gensalt()).decode()
if await user_repo.update_password(user_id, new_hash):
    print("Password updated")
```

### Bulk Create Users

```python
async def bulk_create_users(users_data: List[Dict[str, Any]]) -> List[User]
```

Create multiple users with validation (checks for duplicate emails).

```python
users_data = [
    {"email": "user1@example.com", "hashed_password": "hash1", "role": UserRole.USER},
    {"email": "user2@example.com", "hashed_password": "hash2", "role": UserRole.ADMIN},
]
created = await user_repo.bulk_create_users(users_data)
```

### Get User Stats

```python
async def get_user_stats() -> Dict[str, int]
```

Get user statistics.

```python
stats = await user_repo.get_user_stats()
# Returns: {"total": 100, "admins": 5, "regular_users": 95}
```

---

## DocumentRepository

Document-specific operations. Inherits all BaseRepository methods.

### Get By File Hash

```python
async def get_by_file_hash(file_hash: str) -> Optional[Document]
```

Get document by SHA-256 file hash.

```python
doc = await doc_repo.get_by_file_hash("0xabc123...")
if doc:
    print(f"Found: {doc.file_name}")
```

### Get By Transaction Hash

```python
async def get_by_transaction_hash(tx_hash: str) -> Optional[Document]
```

Get document by blockchain transaction hash.

```python
doc = await doc_repo.get_by_transaction_hash("0x123def...")
```

### Get User Documents

```python
async def get_user_documents(
    user_id: int,
    status: Optional[DocStatus] = None,
    doc_type: Optional[DocType] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> List[Document]
```

Get documents owned by user with optional filters.

```python
# All user documents
all_docs = await doc_repo.get_user_documents(user_id)

# User's pending documents
pending = await doc_repo.get_user_documents(user_id, status=DocStatus.PENDING)

# User's NFT documents
nfts = await doc_repo.get_user_documents(user_id, doc_type=DocType.NFT)

# Paginated results
page_1 = await doc_repo.get_user_documents(user_id, limit=10, offset=0)
```

### Get By Status

```python
async def get_by_status(status: DocStatus) -> List[Document]
```

Get all documents with specific status.

```python
pending = await doc_repo.get_by_status(DocStatus.PENDING)
on_chain = await doc_repo.get_by_status(DocStatus.ON_CHAIN)
```

### Get By Type

```python
async def get_by_type(doc_type: DocType) -> List[Document]
```

Get all documents of specific type.

```python
hash_docs = await doc_repo.get_by_type(DocType.HASH)
nft_docs = await doc_repo.get_by_type(DocType.NFT)
```

### Get Pending Documents

```python
async def get_pending_documents(limit: Optional[int] = None) -> List[Document]
```

Get all documents awaiting processing.

```python
all_pending = await doc_repo.get_pending_documents()
next_batch = await doc_repo.get_pending_documents(limit=10)
```

### Get Processing Documents

```python
async def get_processing_documents() -> List[Document]
```

Get all documents currently being processed.

```python
processing = await doc_repo.get_processing_documents()
for doc in processing:
    print(f"Processing: {doc.file_name}")
```

### Get On Chain Documents

```python
async def get_on_chain_documents() -> List[Document]
```

Get all successfully notarized documents.

```python
completed = await doc_repo.get_on_chain_documents()
```

### Get Error Documents

```python
async def get_error_documents() -> List[Document]
```

Get all failed documents.

```python
failed = await doc_repo.get_error_documents()
for doc in failed:
    print(f"Error: {doc.file_name} - {doc.error_message}")
```

### File Hash Exists

```python
async def file_hash_exists(file_hash: str) -> bool
```

Check if file has already been uploaded.

```python
if await doc_repo.file_hash_exists(file_hash):
    raise ValueError("File already uploaded")
```

### Update Status

```python
async def update_status(doc_id: int, status: DocStatus) -> Optional[Document]
```

Update document status.

```python
doc = await doc_repo.update_status(doc_id, DocStatus.PROCESSING)
```

### Mark As On Chain

```python
async def mark_as_on_chain(
    doc_id: int,
    transaction_hash: str,
    signed_json_path: str,
    signed_pdf_path: str,
    arweave_file_url: Optional[str] = None,
    arweave_metadata_url: Optional[str] = None,
    nft_token_id: Optional[int] = None
) -> Optional[Document]
```

Mark document as successfully notarized.

```python
# For HASH documents
doc = await doc_repo.mark_as_on_chain(
    doc_id,
    transaction_hash="0x123def...",
    signed_json_path="/certs/1.json",
    signed_pdf_path="/certs/1.pdf"
)

# For NFT documents
doc = await doc_repo.mark_as_on_chain(
    doc_id,
    transaction_hash="0x456abc...",
    signed_json_path="/certs/2.json",
    signed_pdf_path="/certs/2.pdf",
    arweave_file_url="https://arweave.net/abc123",
    arweave_metadata_url="https://arweave.net/def456",
    nft_token_id=42
)
```

### Mark As Error

```python
async def mark_as_error(doc_id: int, error_message: str) -> Optional[Document]
```

Mark document as failed with error message.

```python
doc = await doc_repo.mark_as_error(doc_id, "Blockchain transaction reverted")
```

### Get Document Stats

```python
async def get_document_stats() -> Dict[str, int]
```

Get document statistics by status.

```python
stats = await doc_repo.get_document_stats()
# Returns: {
#     "total": 1000,
#     "pending": 50,
#     "processing": 10,
#     "on_chain": 930,
#     "error": 10
# }
```

---

## ApiKeyRepository

API key-specific operations. Inherits all BaseRepository methods.

### Get By Key Hash

```python
async def get_by_key_hash(key_hash: str) -> Optional[ApiKey]
```

Get API key by its hash.

```python
api_key = await key_repo.get_by_key_hash(key_hash)
```

### Get User API Keys

```python
async def get_user_api_keys(user_id: int) -> List[ApiKey]
```

Get all API keys for a user.

```python
keys = await key_repo.get_user_api_keys(user_id)
for key in keys:
    print(f"Key: {key.prefix}, Created: {key.created_at}")
```

### Key Hash Exists

```python
async def key_hash_exists(key_hash: str) -> bool
```

Check if API key exists.

```python
if await key_repo.key_hash_exists(key_hash):
    print("API key is valid")
```

### Validate API Key

```python
async def validate_api_key(key_hash: str) -> Optional[User]
```

Validate API key and return its owner. Returns None if invalid.

```python
user = await key_repo.validate_api_key(key_hash)
if user:
    print(f"API key belongs to: {user.email}")
else:
    print("Invalid API key")
```

### Revoke API Key

```python
async def revoke_api_key(key_id: int) -> bool
```

Revoke (delete) a specific API key. Returns True if successful.

```python
if await key_repo.revoke_api_key(key_id):
    print("API key revoked")
```

### Revoke User API Keys

```python
async def revoke_user_api_keys(user_id: int) -> int
```

Revoke all API keys for a user. Returns number of revoked keys.

```python
count = await key_repo.revoke_user_api_keys(user_id)
print(f"Revoked {count} API keys")
```

### Update Description

```python
async def update_description(key_id: int, description: str) -> Optional[ApiKey]
```

Update API key description.

```python
key = await key_repo.update_description(key_id, "Updated description")
```

### Create API Key

```python
async def create_api_key(
    owner_id: int,
    key_hash: str,
    prefix: str,
    description: Optional[str] = None
) -> ApiKey
```

Create a new API key with validation.

```python
key = await key_repo.create_api_key(
    owner_id=user_id,
    key_hash="sha256_hash_of_actual_key",
    prefix="sk_test_abc123",
    description="Test key"
)
```

---

## Common Patterns

### Transaction Pattern

```python
async with get_session() as session:
    try:
        user_repo = UserRepository(session)
        doc_repo = DocumentRepository(session)

        # Create user
        user = await user_repo.create(email="user@example.com", ...)

        # Create document for user
        doc = await doc_repo.create(owner_id=user.id, ...)

        # Commit all changes together
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
```

### Eager Loading Pattern

```python
# Load user with relationships to avoid N+1 queries
user = await user_repo.get_with_documents(user_id)
api_keys = await key_repo.get_user_api_keys(user_id)

# Now you can access relationships without additional queries
for doc in user.documents:
    print(doc.file_name)
```

### Pagination Pattern

```python
page_size = 20
page = 1  # 1-indexed

documents = await doc_repo.get_paginated(page=page, page_size=page_size)

# Or manual pagination
limit = 20
offset = (page - 1) * limit
documents = await doc_repo.get_all(limit=limit, offset=offset)
```

### Filtering Pattern

```python
# Multiple filters (AND logic)
docs = await doc_repo.get_user_documents(
    user_id=user_id,
    status=DocStatus.ON_CHAIN,
    doc_type=DocType.NFT
)

# Or using filter_by
same_docs = await doc_repo.filter_by(
    owner_id=user_id,
    status=DocStatus.ON_CHAIN,
    type=DocType.NFT
)
```

---

## Next Steps

- See [MODELS_REFERENCE.md](MODELS_REFERENCE.md) for model details
- See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for complete working examples
- See [CLAUDE.md](../CLAUDE.md) for quick start
