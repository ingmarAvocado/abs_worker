# Test Factories - MANDATORY Pattern for abs_worker

## Overview

**ALL tests in abs_worker MUST use factories for creating test data.**

DO NOT:
- ❌ Create inline test data with dictionaries
- ❌ Use `AsyncMock()` for model objects
- ❌ Hardcode test values scattered across tests
- ❌ Build test objects manually in each test

DO:
- ✅ Use factories from `tests/factories/`
- ✅ Create real database records
- ✅ Extend factories when needed
- ✅ Keep test data consistent and maintainable

---

## Available Factories

### UserFactory
Create test users with various roles:

```python
from tests.factories import UserFactory
from abs_orm.models import UserRole

async def test_user_creation(db_context):
    # Create regular user
    user = await UserFactory.create(db_context, email="user@test.com")

    # Create admin user
    admin = await UserFactory.create(
        db_context,
        email="admin@test.com",
        role=UserRole.ADMIN
    )
```

### DocumentFactory
Create test documents in various states:

```python
from tests.factories import DocumentFactory
from abs_orm.models import DocStatus, DocType

async def test_document_workflow(db_context, test_user):
    # Create pending document
    doc = await DocumentFactory.create(
        db_context,
        owner_id=test_user.id,
        status=DocStatus.PENDING,
        type=DocType.HASH
    )

    # Create on-chain document
    completed = await DocumentFactory.create(
        db_context,
        owner_id=test_user.id,
        status=DocStatus.ON_CHAIN,
        transaction_hash="0xabc123",
        signed_json_path="/certs/1.json"
    )
```

### ApiKeyFactory
Create test API keys:

```python
from tests.factories import ApiKeyFactory

async def test_api_key_authentication(db_context, test_user):
    # Create active API key
    api_key = await ApiKeyFactory.create(
        db_context,
        owner_id=test_user.id,
        prefix="sk_test_",
        description="Test API Key"
    )
```

---

## Creating New Factories

When you need a new type of test data, create a factory:

### 1. Create Factory File

```python
# tests/factories/your_model_factory.py
from .base_factory import BaseFactory
from abs_orm.models import YourModel

class YourModelFactory(BaseFactory):
    """Factory for creating YourModel test instances."""

    @staticmethod
    async def create(db_context, **kwargs):
        """
        Create YourModel with sensible defaults.

        Args:
            db_context: Test database context
            **kwargs: Override default values

        Returns:
            YourModel instance
        """
        defaults = {
            "field1": "default_value",
            "field2": 123,
            "field3": True,
        }
        defaults.update(kwargs)

        model = await db_context.your_models.create(**defaults)
        await db_context.commit()
        return model

    @staticmethod
    async def create_batch(db_context, count=3, **kwargs):
        """Create multiple instances."""
        return [
            await YourModelFactory.create(db_context, **kwargs)
            for _ in range(count)
        ]
```

### 2. Export in __init__.py

```python
# tests/factories/__init__.py
from .your_model_factory import YourModelFactory

__all__ = [
    # ... existing exports ...
    "YourModelFactory",
]
```

### 3. Document Usage

Add examples to this README showing how to use your new factory.

---

## Integration Test Pattern

Integration tests MUST use factories + real database:

```python
# tests/integration/test_your_feature.py
import pytest
from tests.factories import UserFactory, DocumentFactory
from abs_orm.models import DocStatus

class TestYourFeatureIntegration:
    """Integration tests with REAL database."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, db_context):
        # Create test data with factories
        user = await UserFactory.create(db_context, email="test@example.com")
        doc = await DocumentFactory.create(
            db_context,
            owner_id=user.id,
            status=DocStatus.PENDING
        )

        # Mock ONLY external services (blockchain, etc)
        with patch('abs_worker.notarization.BlockchainClient') as mock_bc:
            mock_bc.return_value.notarize_hash.return_value = mock_result

            # Test with REAL database operations
            await process_hash_notarization(doc.id)

        # Verify REAL database state
        await db_context.session.refresh(doc)
        updated_doc = await db_context.documents.get(doc.id)
        assert updated_doc.status == DocStatus.ON_CHAIN
```

---

## Unit Test Pattern

Unit tests can use factories for consistent data:

```python
# tests/unit/test_your_module.py
from tests.factories import DocumentFactory

async def test_validation_logic(db_context):
    # Use factory even for unit tests
    doc = await DocumentFactory.create(
        db_context,
        file_hash="0xinvalid"
    )

    # Test validation logic
    with pytest.raises(ValidationError):
        validate_document(doc)
```

---

## Factory Best Practices

### ✅ DO

**Use sensible defaults:**
```python
defaults = {
    "email": f"user_{uuid.uuid4().hex[:8]}@test.com",  # Unique
    "created_at": datetime.utcnow(),
    "is_active": True,
}
```

**Allow overrides:**
```python
defaults.update(kwargs)  # Let tests customize
```

**Create related objects:**
```python
@staticmethod
async def create_with_documents(db_context, doc_count=3):
    """Create user with multiple documents."""
    user = await UserFactory.create(db_context)
    docs = await DocumentFactory.create_batch(
        db_context,
        count=doc_count,
        owner_id=user.id
    )
    return user, docs
```

**Provide batch creation:**
```python
@staticmethod
async def create_batch(db_context, count=3, **kwargs):
    """Create multiple instances efficiently."""
    return [await Factory.create(db_context, **kwargs) for _ in range(count)]
```

### ❌ DON'T

**Don't create complex test scenarios in factories:**
```python
# BAD - too specific
async def create_failed_blockchain_document(...):
    # This is a test scenario, not a factory concern
```

**Don't add business logic:**
```python
# BAD - factories should create, not process
async def create_and_notarize_document(...):
    doc = await create(...)
    await process_notarization(doc.id)  # NO!
```

**Don't couple factories:**
```python
# BAD - tight coupling
class DocumentFactory:
    async def create(...):
        user = await UserFactory.create(...)  # Use dependency injection instead
```

---

## Fixture Integration

Factories work seamlessly with pytest fixtures:

```python
# tests/conftest.py
@pytest_asyncio.fixture
async def test_user(db_context):
    """Provide a test user for all tests."""
    return await UserFactory.create(db_context, email="fixture@test.com")

@pytest_asyncio.fixture
async def test_document(db_context, test_user):
    """Provide a test document."""
    return await DocumentFactory.create(
        db_context,
        owner_id=test_user.id,
        status=DocStatus.PENDING
    )
```

Then use in tests:
```python
async def test_something(test_document):
    # test_document is already created by factory
    assert test_document.status == DocStatus.PENDING
```

---

## Why This Matters

### Consistency
All tests use the same data creation pattern. No surprises.

### Maintainability
Change default values in ONE place. All tests update automatically.

### Real Integration
Factories create real database records. Tests validate actual behavior.

### DRY Principle
Write data creation logic once. Reuse everywhere.

### Discoverability
New developers find all test data patterns in `tests/factories/`.

---

## CI/CD Enforcement

The CI pipeline validates factory usage:

```yaml
# .github/workflows/test.yml
- name: Check Factory Pattern
  run: |
    # Fail if tests use AsyncMock for models
    if grep -r "AsyncMock()" tests/ --exclude-dir=mocks --exclude-dir=factories; then
      echo "ERROR: Use factories, not AsyncMock"
      exit 1
    fi
```

---

## Migration Guide

### From Inline Test Data

**Before:**
```python
async def test_old_way():
    mock_doc = type('MockDoc', (), {
        'id': 1,
        'file_name': 'test.pdf',
        'status': 'pending'
    })()
```

**After:**
```python
async def test_new_way(db_context):
    doc = await DocumentFactory.create(
        db_context,
        file_name='test.pdf',
        status=DocStatus.PENDING
    )
```

### From AsyncMock

**Before:**
```python
async def test_old_way():
    mock_doc = AsyncMock()
    mock_doc.id = 1
    mock_doc.file_name = "test.pdf"
```

**After:**
```python
async def test_new_way(db_context):
    doc = await DocumentFactory.create(db_context, file_name="test.pdf")
```

---

## Questions?

If you need a new factory or pattern:
1. Check existing factories for similar patterns
2. Review `BaseFactory` for common functionality
3. Look at integration tests for usage examples
4. Create factory following this guide
5. Update this README with your additions

**Remember: If you're creating test data, you should be using a factory!**
