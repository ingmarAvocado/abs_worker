# abs_orm Usage Examples

Complete working examples demonstrating common patterns and use cases.

## Table of Contents

1. [Setup & Initialization](#setup--initialization)
2. [User Management](#user-management)
3. [Document Workflow](#document-workflow)
4. [API Key Management](#api-key-management)
5. [Advanced Patterns](#advanced-patterns)
6. [Error Handling](#error-handling)

---

## Setup & Initialization

### Basic Setup

```python
from abs_orm import (
    get_session,
    UserRepository,
    DocumentRepository,
    ApiKeyRepository,
    UserRole,
    DocStatus,
    DocType,
    init_db
)
from abs_utils.logger import setup_logging, get_logger
import asyncio

# Setup logging once at app startup
setup_logging(level="INFO", log_format="json", service_name="abs_api")

logger = get_logger(__name__)

async def main():
    # Initialize database (creates tables if needed)
    await init_db()

    # Use repositories
    async with get_session() as session:
        user_repo = UserRepository(session)
        doc_repo = DocumentRepository(session)
        key_repo = ApiKeyRepository(session)

        # ... do work ...

        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
```

### Setup with Custom Logging

```python
from abs_utils.logger import setup_logging

# Setup at application startup
setup_logging(
    level="DEBUG",
    log_format="json",  # or "text"
    service_name="my_service",
    include_timestamp=True
)

# All repository operations will now log automatically
```

---

## User Management

### Create Users

```python
import bcrypt
from abs_orm import get_session, UserRepository, UserRole

async def create_user(email: str, password: str, is_admin: bool = False):
    """Create a new user."""
    async with get_session() as session:
        user_repo = UserRepository(session)

        # Check if email already exists
        if await user_repo.email_exists(email):
            raise ValueError(f"Email {email} already registered")

        # Hash password (never store plaintext)
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Create user
        role = UserRole.ADMIN if is_admin else UserRole.USER
        user = await user_repo.create(
            email=email,
            hashed_password=hashed,
            role=role
        )

        await session.commit()
        logger.info(f"User created: {email} (admin={is_admin})")
        return user

# Usage
async def example():
    await create_user("john@example.com", "secure_password")
    await create_user("admin@example.com", "admin_password", is_admin=True)
```

### Authenticate User

```python
import bcrypt
from abs_orm import get_session, UserRepository

async def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate user by email and password."""
    async with get_session() as session:
        user_repo = UserRepository(session)

        user = await user_repo.get_by_email(email)
        if not user:
            logger.warning(f"Login attempt with unknown email: {email}")
            return None

        # Verify password
        password_matches = bcrypt.checkpw(
            password.encode(),
            user.hashed_password.encode()
        )

        if not password_matches:
            logger.warning(f"Failed login attempt for: {email}")
            return None

        logger.info(f"User authenticated: {email}")
        return user

# Usage
async def example():
    user = await authenticate_user("john@example.com", "secure_password")
    if user:
        print(f"Welcome {user.email}")
```

### Manage User Roles

```python
from abs_orm import get_session, UserRepository, UserRole

async def promote_user_example():
    """Promote a regular user to admin."""
    async with get_session() as session:
        user_repo = UserRepository(session)

        # Promote to admin
        if await user_repo.promote_to_admin(user_id=1):
            logger.info(f"User promoted to admin")
        else:
            logger.warning(f"User not found")

        await session.commit()

async def demote_admin_example():
    """Demote an admin to regular user."""
    async with get_session() as session:
        user_repo = UserRepository(session)

        if await user_repo.demote_to_user(user_id=1):
            logger.info(f"Admin demoted to regular user")
        else:
            logger.warning(f"User not found")

        await session.commit()

async def get_admins_example():
    """Get all admin users."""
    async with get_session() as session:
        user_repo = UserRepository(session)

        admins = await user_repo.get_all_admins()
        logger.info(f"Found {len(admins)} admins")

        for admin in admins:
            print(f"  - {admin.email}")
```

### Get User Statistics

```python
from abs_orm import get_session, UserRepository

async def get_user_stats_example():
    """Get user statistics."""
    async with get_session() as session:
        user_repo = UserRepository(session)

        stats = await user_repo.get_user_stats()

        print(f"Total users: {stats['total']}")
        print(f"Admins: {stats['admins']}")
        print(f"Regular users: {stats['regular_users']}")
```

---

## Document Workflow

### Upload Document

```python
import hashlib
from abs_orm import get_session, DocumentRepository, DocStatus, DocType

async def upload_document(user_id: int, file_path: str) -> Document:
    """Upload a document for notarization."""
    async with get_session() as session:
        doc_repo = DocumentRepository(session)

        # Read file and compute hash
        with open(file_path, 'rb') as f:
            content = f.read()
            file_hash = "0x" + hashlib.sha256(content).hexdigest()

        # Check if already uploaded
        if await doc_repo.file_hash_exists(file_hash):
            raise ValueError("File already uploaded")

        # Get filename
        import os
        file_name = os.path.basename(file_path)

        # Create document record
        doc = await doc_repo.create(
            owner_id=user_id,
            file_name=file_name,
            file_hash=file_hash,
            file_path=file_path,
            type=DocType.HASH,
            status=DocStatus.PENDING
        )

        await session.commit()
        logger.info(f"Document uploaded: {file_name} (ID: {doc.id})")
        return doc

# Usage
async def example():
    doc = await upload_document(user_id=1, file_path="/path/to/contract.pdf")
    print(f"Document created with ID: {doc.id}")
```

### Process Document (Worker Pattern)

```python
from abs_orm import get_session, DocumentRepository, DocStatus

async def process_pending_documents():
    """Process pending documents (for background worker)."""
    async with get_session() as session:
        doc_repo = DocumentRepository(session)

        # Get pending documents
        pending = await doc_repo.get_pending_documents(limit=10)
        logger.info(f"Found {len(pending)} pending documents")

        for doc in pending:
            try:
                # Mark as processing
                await doc_repo.update_status(doc.id, DocStatus.PROCESSING)
                await session.commit()

                logger.info(f"Processing document: {doc.file_name}")

                # Simulate notarization
                # In real app, would:
                # 1. Call blockchain API
                # 2. Get transaction hash
                # 3. Generate certificates

                tx_hash = "0x123abc..."
                json_path = f"/certs/{doc.id}.json"
                pdf_path = f"/certs/{doc.id}.pdf"

                # Mark as on-chain
                await doc_repo.mark_as_on_chain(
                    doc.id,
                    transaction_hash=tx_hash,
                    signed_json_path=json_path,
                    signed_pdf_path=pdf_path
                )
                await session.commit()

                logger.info(f"Document completed: {doc.file_name}")

            except Exception as e:
                # Mark as error
                await doc_repo.mark_as_error(
                    doc.id,
                    error_message=str(e)
                )
                await session.commit()
                logger.error(f"Failed to process document: {doc.file_name} - {e}")

async def example():
    await process_pending_documents()
```

### Query Documents

```python
from abs_orm import get_session, DocumentRepository, DocStatus, DocType

async def query_documents_example():
    """Various ways to query documents."""
    async with get_session() as session:
        doc_repo = DocumentRepository(session)

        # Get all documents (careful with large datasets)
        all_docs = await doc_repo.get_all()

        # Get paginated
        page_1 = await doc_repo.get_paginated(page=1, page_size=20)

        # Get by status
        pending = await doc_repo.get_by_status(DocStatus.PENDING)
        on_chain = await doc_repo.get_by_status(DocStatus.ON_CHAIN)

        # Get by type
        hash_docs = await doc_repo.get_by_type(DocType.HASH)
        nft_docs = await doc_repo.get_by_type(DocType.NFT)

        # Get user's documents
        user_docs = await doc_repo.get_user_documents(user_id=1)

        # Get user's pending documents
        user_pending = await doc_repo.get_user_documents(
            user_id=1,
            status=DocStatus.PENDING
        )

        # Get user's NFT documents
        user_nfts = await doc_repo.get_user_documents(
            user_id=1,
            doc_type=DocType.NFT
        )

        # Get by hash
        doc = await doc_repo.get_by_file_hash("0xabc123...")

        # Get statistics
        stats = await doc_repo.get_document_stats()
        print(f"Total documents: {stats['total']}")
        print(f"Pending: {stats['pending']}")
        print(f"Processing: {stats['processing']}")
        print(f"On-chain: {stats['on_chain']}")
        print(f"Errors: {stats['error']}")
```

### Create NFT Document

```python
from abs_orm import get_session, DocumentRepository, DocStatus, DocType

async def create_nft_document(user_id: int, file_path: str) -> Document:
    """Create and process an NFT document."""
    async with get_session() as session:
        doc_repo = DocumentRepository(session)

        # Create NFT document
        doc = await doc_repo.create(
            owner_id=user_id,
            file_name="artwork.png",
            file_hash="0xdef456...",
            file_path=file_path,
            type=DocType.NFT,
            status=DocStatus.PENDING
        )

        await session.commit()

        # Later, after blockchain processing...
        async with get_session() as session:
            doc_repo = DocumentRepository(session)

            # Mark NFT as on-chain with Arweave URLs
            await doc_repo.mark_as_on_chain(
                doc.id,
                transaction_hash="0xminting_tx...",
                signed_json_path="/certs/nft_1.json",
                signed_pdf_path="/certs/nft_1.pdf",
                arweave_file_url="https://arweave.net/abc123def456",
                arweave_metadata_url="https://arweave.net/xyz789",
                nft_token_id=42
            )

            await session.commit()

        return doc
```

---

## API Key Management

### Generate API Key

```python
import hashlib
import secrets
from abs_orm import get_session, ApiKeyRepository

async def generate_api_key(user_id: int, description: str = None):
    """Generate a new API key for user."""
    async with get_session() as session:
        key_repo = ApiKeyRepository(session)

        # Generate actual key (show to user once)
        actual_key = f"sk_test_{secrets.token_urlsafe(32)}"

        # Hash for database
        key_hash = hashlib.sha256(actual_key.encode()).hexdigest()

        # Extract prefix (show in admin panel)
        prefix = actual_key[:20] + "..."

        # Create in database
        api_key = await key_repo.create(
            owner_id=user_id,
            key_hash=key_hash,
            prefix=prefix,
            description=description or "API Key"
        )

        await session.commit()
        logger.info(f"API key created for user {user_id}")

        # Return actual key (can only be shown once)
        return {
            "actual_key": actual_key,
            "prefix": prefix,
            "created_at": api_key.created_at
        }

# Usage
async def example():
    result = await generate_api_key(user_id=1, description="CI/CD Pipeline")
    print(f"Your API key: {result['actual_key']}")
    print(f"Keep it safe! It won't be shown again.")
```

### Validate API Key

```python
import hashlib
from abs_orm import get_session, ApiKeyRepository

async def validate_api_key(key_string: str):
    """Validate API key from request."""
    async with get_session() as session:
        key_repo = ApiKeyRepository(session)

        # Hash the provided key
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()

        # Validate and get owner
        user = await key_repo.validate_api_key(key_hash)

        if user:
            logger.info(f"API key validated for user: {user.email}")
            return user
        else:
            logger.warning(f"Invalid API key attempted")
            return None

# Usage in request handler
async def api_request_handler(request_key: str):
    user = await validate_api_key(request_key)
    if not user:
        return {"error": "Unauthorized"}, 401

    # Proceed with request as user
```

### Manage API Keys

```python
from abs_orm import get_session, ApiKeyRepository

async def list_user_api_keys_example():
    """List all API keys for a user."""
    async with get_session() as session:
        key_repo = ApiKeyRepository(session)

        keys = await key_repo.get_user_api_keys(user_id=1)

        for key in keys:
            print(f"Key: {key.prefix}")
            print(f"  Description: {key.description}")
            print(f"  Created: {key.created_at}")

async def revoke_api_key_example():
    """Revoke a specific API key."""
    async with get_session() as session:
        key_repo = ApiKeyRepository(session)

        if await key_repo.revoke_api_key(key_id=1):
            logger.info(f"API key revoked")
        else:
            logger.warning(f"API key not found")

        await session.commit()

async def revoke_all_user_keys_example():
    """Revoke all API keys for a user."""
    async with get_session() as session:
        key_repo = ApiKeyRepository(session)

        count = await key_repo.revoke_user_api_keys(user_id=1)
        logger.info(f"Revoked {count} API keys")

        await session.commit()
```

---

## Advanced Patterns

### Load User with All Data

```python
from abs_orm import get_session, UserRepository, ApiKeyRepository

async def get_user_profile(user_id: int):
    """Load user with all related data."""
    async with get_session() as session:
        user_repo = UserRepository(session)
        key_repo = ApiKeyRepository(session)

        # Get user with documents
        user = await user_repo.get_with_documents(user_id)

        # Get user's API keys
        api_keys = await key_repo.get_user_api_keys(user_id)

        # Construct profile
        profile = {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "documents_count": len(user.documents),
            "api_keys_count": len(api_keys),
            "documents": [
                {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "status": doc.status.value,
                    "type": doc.type.value,
                    "created_at": doc.created_at.isoformat()
                }
                for doc in user.documents
            ]
        }

        return profile
```

### Bulk Operations

```python
from abs_orm import get_session, UserRepository

async def bulk_create_users_example():
    """Create multiple users at once."""
    async with get_session() as session:
        user_repo = UserRepository(session)

        users_data = [
            {
                "email": "user1@example.com",
                "hashed_password": "hash1",
                "role": UserRole.USER
            },
            {
                "email": "user2@example.com",
                "hashed_password": "hash2",
                "role": UserRole.USER
            },
            {
                "email": "admin@example.com",
                "hashed_password": "hash3",
                "role": UserRole.ADMIN
            },
        ]

        # Bulk create with validation
        created_users = await user_repo.bulk_create_users(users_data)
        await session.commit()

        logger.info(f"Created {len(created_users)} users")
```

### Pagination

```python
from abs_orm import get_session, DocumentRepository

async def paginate_documents(page: int = 1, page_size: int = 20):
    """Get paginated documents."""
    async with get_session() as session:
        doc_repo = DocumentRepository(session)

        # Get page
        documents = await doc_repo.get_paginated(page=page, page_size=page_size)

        # Get total count
        total = await doc_repo.count()

        # Calculate pagination info
        total_pages = (total + page_size - 1) // page_size

        return {
            "documents": documents,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
```

---

## Error Handling

### Safe User Creation

```python
from abs_orm import get_session, UserRepository
from sqlalchemy.exc import IntegrityError

async def safe_create_user(email: str, password: str):
    """Create user with proper error handling."""
    async with get_session() as session:
        user_repo = UserRepository(session)

        try:
            # Check if email exists
            if await user_repo.email_exists(email):
                return {"error": "Email already registered"}

            # Create user
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            user = await user_repo.create(
                email=email,
                hashed_password=hashed
            )

            await session.commit()
            return {"user_id": user.id, "email": user.email}

        except IntegrityError:
            await session.rollback()
            return {"error": "Email already registered"}
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create user: {e}")
            return {"error": "Failed to create user"}
```

### Safe Document Processing

```python
async def safe_process_document(doc_id: int):
    """Process document with error handling."""
    async with get_session() as session:
        doc_repo = DocumentRepository(session)

        try:
            # Get document
            doc = await doc_repo.get(doc_id)
            if not doc:
                return {"error": "Document not found"}

            # Mark as processing
            await doc_repo.update_status(doc.id, DocStatus.PROCESSING)
            await session.commit()

            # Notarize (might fail)
            try:
                # Call blockchain API, etc.
                tx_hash = await notarize_on_blockchain(doc)

                # Mark as on-chain
                await doc_repo.mark_as_on_chain(
                    doc.id,
                    transaction_hash=tx_hash,
                    signed_json_path="/path/to/json",
                    signed_pdf_path="/path/to/pdf"
                )
                await session.commit()

                return {"success": True, "transaction_hash": tx_hash}

            except Exception as e:
                # Mark as error
                await doc_repo.mark_as_error(doc.id, str(e))
                await session.commit()
                logger.error(f"Failed to notarize: {e}")
                return {"error": str(e)}

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": "Unexpected error"}
```

---

## Next Steps

- See [MODELS_REFERENCE.md](MODELS_REFERENCE.md) for model details
- See [REPOSITORIES_REFERENCE.md](REPOSITORIES_REFERENCE.md) for all methods
- See [CLAUDE.md](../CLAUDE.md) for quick start
