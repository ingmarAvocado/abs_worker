"""Base factory for creating test data with blockchain-specific helpers."""
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from abs_orm import Base

T = TypeVar("T", bound=Base)


class BaseFactory:
    """Base factory class for creating test objects."""

    model: Type[Base] = None

    @classmethod
    def random_string(cls, length: int = 10, prefix: str = "") -> str:
        """Generate a random string."""
        chars = string.ascii_letters + string.digits
        random_part = "".join(random.choice(chars) for _ in range(length))
        return f"{prefix}{random_part}" if prefix else random_part

    @classmethod
    def random_hex(cls, length: int = 64) -> str:
        """Generate a random hex string (for hashes, addresses, etc)."""
        chars = string.hexdigits.lower()[:16]  # 0-9a-f
        return "".join(random.choice(chars) for _ in range(length))

    @classmethod
    def random_address(cls) -> str:
        """Generate a random Ethereum address."""
        return "0x" + cls.random_hex(40)

    @classmethod
    def random_tx_hash(cls) -> str:
        """Generate a random transaction hash."""
        return "0x" + cls.random_hex(64)

    @classmethod
    def random_file_hash(cls) -> str:
        """Generate a random file hash (SHA-256)."""
        return "0x" + cls.random_hex(64)

    @classmethod
    def random_arweave_id(cls) -> str:
        """Generate a random Arweave transaction ID."""
        chars = string.ascii_letters + string.digits + "-_"
        return "".join(random.choice(chars) for _ in range(43))

    @classmethod
    def random_arweave_url(cls) -> str:
        """Generate a random Arweave URL."""
        return f"https://arweave.net/{cls.random_arweave_id()}"

    @classmethod
    def random_email(cls) -> str:
        """Generate a random email."""
        username = cls.random_string(8)
        domain = cls.random_string(5)
        return f"{username}@{domain}.com"

    @classmethod
    def random_phone(cls) -> str:
        """Generate a random phone number."""
        return "".join(random.choice(string.digits) for _ in range(10))

    @classmethod
    def random_int(cls, min_val: int = 1, max_val: int = 1000) -> int:
        """Generate a random integer."""
        return random.randint(min_val, max_val)

    @classmethod
    def random_float(cls, min_val: float = 0.0, max_val: float = 100.0, decimals: int = 2) -> float:
        """Generate a random float."""
        value = random.uniform(min_val, max_val)
        return round(value, decimals)

    @classmethod
    def random_bool(cls) -> bool:
        """Generate a random boolean."""
        return random.choice([True, False])

    @classmethod
    def random_datetime(cls, days_back: int = 30) -> datetime:
        """Generate a random datetime within the last N days."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=days_back)
        random_seconds = random.randint(0, int((now - past).total_seconds()))
        return past + timedelta(seconds=random_seconds)

    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        """Get default values for the model. Override in subclasses."""
        return {}

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        **kwargs
    ) -> T:
        """Create and persist a model instance."""
        if cls.model is None:
            raise NotImplementedError("model attribute must be set")

        # Merge defaults with provided kwargs
        defaults = cls.get_defaults()
        defaults.update(kwargs)

        # Create instance
        instance = cls.model(**defaults)

        # Add to session and flush
        session.add(instance)
        await session.flush()

        return instance

    @classmethod
    async def create_batch(
        cls,
        session: AsyncSession,
        count: int,
        **kwargs
    ) -> list[T]:
        """Create multiple instances."""
        instances = []
        for _ in range(count):
            instance = await cls.create(session, **kwargs)
            instances.append(instance)
        return instances
