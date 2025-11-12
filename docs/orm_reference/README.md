# abs_orm Documentation

Complete reference documentation for the abs_orm database layer and ORM models.

## Quick Navigation

### 📚 Start Here
- **[CLAUDE.md](../CLAUDE.md)** - Quick start guide for LLMs and developers

### 📖 Core References
- **[MODELS_REFERENCE.md](MODELS_REFERENCE.md)** - Complete model documentation
  - User model with roles
  - Document model with status workflow
  - ApiKey model for programmatic access
  - All fields, relationships, and enums

- **[REPOSITORIES_REFERENCE.md](REPOSITORIES_REFERENCE.md)** - All repository methods
  - BaseRepository (generic CRUD)
  - UserRepository (user-specific operations)
  - DocumentRepository (document-specific operations)
  - ApiKeyRepository (API key management)

- **[USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)** - Working code examples
  - User management (create, authenticate, manage roles)
  - Document workflow (upload, process, query)
  - API key management (generate, validate, revoke)
  - Advanced patterns and error handling

---

## Overview

**abs_orm** is the database abstraction layer for the abs_notary file notarization service.

### Architecture

```
┌─────────────────────────────────────┐
│  Application (FastAPI, Workers)     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     Repositories (CRUD Layer)       │
│  ├─ UserRepository                  │
│  ├─ DocumentRepository              │
│  └─ ApiKeyRepository                │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   SQLAlchemy ORM Models             │
│  ├─ User                            │
│  ├─ Document                        │
│  └─ ApiKey                          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  PostgreSQL Database                │
│  ├─ users table                     │
│  ├─ documents table                 │
│  └─ api_keys table                  │
└─────────────────────────────────────┘
```

### Key Features

- ✅ **Async/Await** - Fully asynchronous with SQLAlchemy 2.0
- ✅ **Type Safety** - Generic repositories with full type hints
- ✅ **Structured Logging** - Built-in abs_utils logging integration
- ✅ **Repository Pattern** - Clean separation of concerns
- ✅ **Relationships** - Automatic eager loading support
- ✅ **Enums** - Type-safe status and role enums

---

## Data Models

### User
Represents system users with authentication and role management.

- **Fields**: email, hashed_password, role, created_at
- **Roles**: ADMIN, USER
- **Relationships**: documents (One-to-Many), api_keys (One-to-Many)

### Document
Represents files to be notarized with blockchain data.

- **Fields**: file_name, file_hash, file_path, status, type, transaction_hash, etc.
- **Status**: PENDING → PROCESSING → ON_CHAIN (or ERROR)
- **Types**: HASH (simple notarization), NFT (with Arweave storage)
- **Relationship**: owner (Many-to-One with User)

### ApiKey
Represents API keys for programmatic access.

- **Fields**: key_hash, prefix, description, owner_id, created_at
- **Security**: Only hashes stored, actual keys shown once
- **Relationship**: owner (Many-to-One with User)

---

## Repository Pattern

Each model has a corresponding repository with CRUD operations:

```python
from abs_orm import get_session, UserRepository, DocumentRepository, ApiKeyRepository

async with get_session() as session:
    # Initialize repositories
    user_repo = UserRepository(session)
    doc_repo = DocumentRepository(session)
    key_repo = ApiKeyRepository(session)

    # Use repositories
    user = await user_repo.create(email="user@example.com", ...)
    docs = await doc_repo.get_user_documents(user.id)
    keys = await key_repo.get_user_api_keys(user.id)

    # Commit changes
    await session.commit()
```

### Common Operations

All repositories support:
- `create(**kwargs)` - Create entity
- `get(id)` - Get by ID
- `get_all(limit, offset)` - Paginated list
- `get_by(field, value)` - Get by field
- `filter_by(**kwargs)` - Filter by multiple fields
- `update(id, **kwargs)` - Update entity
- `delete(id)` - Delete entity
- `count(**kwargs)` - Count entities
- `bulk_create(data)` - Create multiple

Plus model-specific methods. See [REPOSITORIES_REFERENCE.md](REPOSITORIES_REFERENCE.md).

---

## Common Workflows

### Create User

```python
from abs_orm import get_session, UserRepository
import bcrypt

async with get_session() as session:
    repo = UserRepository(session)

    user = await repo.create(
        email="user@example.com",
        hashed_password=bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(),
        role=UserRole.USER
    )
    await session.commit()
```

### Upload Document

```python
from abs_orm import get_session, DocumentRepository, DocStatus, DocType

async with get_session() as session:
    repo = DocumentRepository(session)

    doc = await repo.create(
        owner_id=user_id,
        file_name="contract.pdf",
        file_hash="0xabc123...",
        file_path="/storage/contract.pdf",
        type=DocType.HASH,
        status=DocStatus.PENDING
    )
    await session.commit()
```

### Mark Document On-Chain

```python
from abs_orm import get_session, DocumentRepository

async with get_session() as session:
    repo = DocumentRepository(session)

    await repo.mark_as_on_chain(
        doc_id,
        transaction_hash="0x123def...",
        signed_json_path="/certs/1.json",
        signed_pdf_path="/certs/1.pdf"
    )
    await session.commit()
```

### Validate API Key

```python
from abs_orm import get_session, ApiKeyRepository
import hashlib

async with get_session() as session:
    repo = ApiKeyRepository(session)

    key_hash = hashlib.sha256(api_key_string.encode()).hexdigest()
    user = await repo.validate_api_key(key_hash)

    if user:
        print(f"Valid key for user: {user.email}")
```

---

## Environment Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Poetry (package manager)

### Installation

```bash
# Install dependencies
poetry install

# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=password
export DB_NAME=abs_notary

# Initialize database
poetry run python -c "from abs_orm import init_db; import asyncio; asyncio.run(init_db())"
```

### Database Migrations

```bash
# Create migration after model changes
poetry run alembic revision --autogenerate -m "Add field to table"

# Apply migrations
poetry run alembic upgrade head

# Rollback last migration
poetry run alembic downgrade -1
```

---

## Testing

abs_orm includes comprehensive test coverage with real database testing.

### Factory Pattern

Tests use factories to create consistent test data:

```python
from tests.factories import UserFactory, DocumentFactory, ApiKeyFactory

# Create test user
user = await UserFactory.create(session, email="test@example.com")

# Create test document
doc = await DocumentFactory.create_pending(session, owner=user)

# Create test API key
key = await ApiKeyFactory.create(session, owner=user)
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/abs_orm

# Run specific test
poetry run pytest tests/repositories/test_user_repository.py

# Run in parallel
poetry run pytest -n auto
```

---

## Project Structure

```
abs_orm/
├── src/
│   └── abs_orm/
│       ├── models/              # SQLAlchemy models
│       │   ├── base.py
│       │   ├── user.py
│       │   ├── document.py
│       │   └── api_key.py
│       ├── repositories/        # Repository layer
│       │   ├── base.py
│       │   ├── user.py
│       │   ├── document.py
│       │   └── api_key.py
│       ├── schemas/             # Pydantic schemas
│       ├── database.py          # Database configuration
│       └── __init__.py
├── tests/                       # Test suite
│       ├── factories/           # Test data factories
│       ├── repositories/        # Repository tests
│       └── conftest.py          # Test configuration
├── alembic/                     # Database migrations
├── docs/                        # Documentation (this folder)
└── README.md
```

---

## Integration with Other Modules

### abs_api_server
FastAPI backend uses abs_orm for:
- User authentication and authorization
- Document upload and retrieval
- API key validation

### abs_worker
Background worker uses abs_orm for:
- Document processing status updates
- Blockchain transaction tracking
- Error logging

### abs_utils
Shared utilities provide:
- Structured logging
- Logger integration in all repositories
- Configuration management

---

## Best Practices

### 1. Always Commit
```python
async with get_session() as session:
    repo = UserRepository(session)
    user = await repo.create(...)
    await session.commit()  # Essential!
```

### 2. Use Relationships
```python
# Good: Load relationships to avoid N+1 queries
user = await user_repo.get_with_documents(user_id)
for doc in user.documents:
    print(doc.file_name)

# Avoid: Multiple queries
user = await user_repo.get(user_id)
docs = await doc_repo.get_user_documents(user_id)  # Separate query
```

### 3. Hash Sensitive Data
```python
# Always hash passwords and API keys
hashed_pwd = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
key_hash = hashlib.sha256(api_key.encode()).hexdigest()
```

### 4. Error Handling
```python
try:
    user = await user_repo.create(...)
    await session.commit()
except IntegrityError:
    await session.rollback()
    raise ValueError("Email already exists")
```

### 5. Use Enums
```python
# Good: Type-safe
doc = await doc_repo.create(status=DocStatus.PENDING, type=DocType.HASH)

# Avoid: String values
doc = await doc_repo.create(status="pending", type="hash")
```

---

## Logging

All repository operations include automatic structured logging:

```python
# When you call:
user = await user_repo.get_by_email("test@example.com")

# It logs (JSON format):
{
  "message": "Fetching user by email",
  "extra": {"email": "test@example.com"}
}

# If not found:
{
  "message": "User not found",
  "extra": {"email": "test@example.com"}
}
```

Configure logging in your application:

```python
from abs_utils.logger import setup_logging

setup_logging(
    level="INFO",
    log_format="json",
    service_name="abs_api_server"
)
```

---

## Troubleshooting

### Connection Issues
- Check PostgreSQL is running: `psql -U postgres`
- Verify environment variables: `echo $DB_HOST`
- Test connection: `poetry run python -c "from abs_orm import init_db; asyncio.run(init_db())"`

### Migration Issues
- Check migration status: `poetry run alembic current`
- View migrations: `poetry run alembic history`
- Reset to initial: `poetry run alembic downgrade base`

### Type Errors
- Ensure enum values match: `DocStatus.PENDING`, not `"pending"`
- Check relationship loading: Use `get_with_documents()`, not direct access
- Validate model fields: See [MODELS_REFERENCE.md](MODELS_REFERENCE.md)

---

## Further Reading

### Documentation
- [CLAUDE.md](../CLAUDE.md) - Quick start for LLMs
- [MODELS_REFERENCE.md](MODELS_REFERENCE.md) - Model documentation
- [REPOSITORIES_REFERENCE.md](REPOSITORIES_REFERENCE.md) - API reference
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - Working examples

### External Resources
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Alembic Docs](https://alembic.sqlalchemy.org/)
- [Pydantic Docs](https://docs.pydantic.dev/)

### Related Repositories
- [abs_api_server](https://github.com/ingmarAvocado/abs_api_server) - FastAPI backend
- [abs_worker](https://github.com/ingmarAvocado/abs_worker) - Background worker
- [abs_utils](https://github.com/ingmarAvocado/abs_utils) - Shared utilities
- [abs_blockchain](https://github.com/ingmarAvocado/abs_blockchain) - Blockchain integration

---

## Contributing

When making changes to models or repositories:

1. Update the model in `src/abs_orm/models/`
2. Update the repository in `src/abs_orm/repositories/`
3. Create a database migration: `poetry run alembic revision --autogenerate -m "description"`
4. Update tests in `tests/`
5. Update documentation in `docs/`
6. Run tests: `poetry run pytest`

---

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review [MODELS_REFERENCE.md](MODELS_REFERENCE.md) and [REPOSITORIES_REFERENCE.md](REPOSITORIES_REFERENCE.md)
3. See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for similar patterns
4. Open an issue on GitHub

---

**Last Updated**: November 2025

For the latest information, see the project README.md and source code documentation.
