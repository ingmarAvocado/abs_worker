"""Factory for creating User test data."""
import bcrypt
import pytest_asyncio

from abs_orm.models import User, UserRole
from .base_factory import BaseFactory


class UserFactory(BaseFactory):
    """Factory for creating User instances."""

    model = User

    @classmethod
    def get_defaults(cls) -> dict:
        """Get default values for User."""
        return {
            "email": cls.random_email(),
            "hashed_password": bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(),
            "role": UserRole.USER,
        }

    @classmethod
    async def create_admin(cls, session, **kwargs):
        """Create an admin user."""
        kwargs["role"] = UserRole.ADMIN
        if "email" not in kwargs:
            kwargs["email"] = f"admin_{cls.random_string(8)}@example.com"
        return await cls.create(session, **kwargs)

    @classmethod
    async def create_with_documents(cls, session, doc_count: int = 3, **kwargs):
        """Create a user with multiple documents."""
        from .document_factory import DocumentFactory

        user = await cls.create(session, **kwargs)
        documents = await DocumentFactory.create_batch(session, doc_count, owner_id=user.id)

        return user, documents

    @classmethod
    async def create_with_api_keys(cls, session, key_count: int = 2, **kwargs):
        """Create a user with multiple API keys."""
        from .api_key_factory import ApiKeyFactory

        user = await cls.create(session, **kwargs)
        api_keys = await ApiKeyFactory.create_batch(session, key_count, owner_id=user.id)

        return user, api_keys


@pytest_asyncio.fixture
async def user_factory():
    """Fixture that returns the UserFactory class."""
    return UserFactory
