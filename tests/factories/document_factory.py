"""Factory for creating Document test data."""
import pytest_asyncio
from typing import Optional

from abs_orm.models import Document, DocStatus, DocType, User
from .base_factory import BaseFactory
from .user_factory import UserFactory


class DocumentFactory(BaseFactory):
    """Factory for creating Document instances."""

    model = Document

    @classmethod
    def get_defaults(cls) -> dict:
        """Get default values for Document."""
        return {
            "file_name": f"document_{cls.random_string(8)}.pdf",
            "file_hash": cls.random_file_hash(),
            "file_path": f"/tmp/documents/{cls.random_string(16)}.pdf",
            "status": DocStatus.PENDING,
            "type": DocType.HASH,
        }

    @classmethod
    async def create(cls, session, owner: Optional[User] = None, **kwargs):
        """Create a document, auto-creating owner if not provided."""
        if owner is None and "owner_id" not in kwargs:
            owner = await UserFactory.create(session)
            kwargs["owner_id"] = owner.id

        if owner is not None and "owner_id" not in kwargs:
            kwargs["owner_id"] = owner.id

        return await super().create(session, **kwargs)

    @classmethod
    async def create_pending(cls, session, owner: Optional[User] = None, **kwargs):
        """Create a pending document ready for processing."""
        kwargs["status"] = DocStatus.PENDING
        return await cls.create(session, owner=owner, **kwargs)

    @classmethod
    async def create_processing(cls, session, owner: Optional[User] = None, **kwargs):
        """Create a processing document (worker is working on it)."""
        kwargs["status"] = DocStatus.PROCESSING
        return await cls.create(session, owner=owner, **kwargs)

    @classmethod
    async def create_on_chain(cls, session, owner: Optional[User] = None, **kwargs):
        """Create a completed on-chain document with all details."""
        defaults = {
            "status": DocStatus.ON_CHAIN,
            "transaction_hash": cls.random_tx_hash(),
            "signed_json_path": f"/storage/certs/{cls.random_string(16)}.json",
            "signed_pdf_path": f"/storage/certs/{cls.random_string(16)}.pdf",
        }
        defaults.update(kwargs)
        return await cls.create(session, owner=owner, **defaults)

    @classmethod
    async def create_nft(cls, session, owner: Optional[User] = None, **kwargs):
        """Create an NFT document with Arweave URLs and token ID."""
        defaults = {
            "type": DocType.NFT,
            "status": DocStatus.ON_CHAIN,
            "transaction_hash": cls.random_tx_hash(),
            "arweave_file_url": cls.random_arweave_url(),
            "arweave_metadata_url": cls.random_arweave_url(),
            "nft_token_id": cls.random_int(1, 100000),
            "signed_json_path": f"/storage/certs/{cls.random_string(16)}.json",
            "signed_pdf_path": f"/storage/certs/{cls.random_string(16)}.pdf",
        }
        defaults.update(kwargs)
        return await cls.create(session, owner=owner, **defaults)

    @classmethod
    async def create_error(cls, session, owner: Optional[User] = None, **kwargs):
        """Create a document with error status."""
        defaults = {
            "status": DocStatus.ERROR,
            "error_message": kwargs.pop("error_message", f"Processing error: {cls.random_string(30)}"),
        }
        defaults.update(kwargs)
        return await cls.create(session, owner=owner, **defaults)

    @classmethod
    async def create_workflow_batch(cls, session, owner: Optional[User] = None, **kwargs):
        """Create a batch of documents representing a full workflow."""
        if owner is None:
            owner = await UserFactory.create(session)

        pending = await cls.create_pending(session, owner=owner)
        processing = await cls.create_processing(session, owner=owner)
        on_chain = await cls.create_on_chain(session, owner=owner)
        error = await cls.create_error(session, owner=owner)

        return {
            "pending": pending,
            "processing": processing,
            "on_chain": on_chain,
            "error": error,
            "owner": owner,
        }

    @classmethod
    async def create_hash_document(cls, session, owner: Optional[User] = None, **kwargs):
        """Create a hash-type document (alias for clarity)."""
        kwargs["type"] = DocType.HASH
        return await cls.create(session, owner=owner, **kwargs)

    @classmethod
    async def create_nft_pending(cls, session, owner: Optional[User] = None, **kwargs):
        """Create a pending NFT document ready for minting."""
        kwargs["type"] = DocType.NFT
        kwargs["status"] = DocStatus.PENDING
        return await cls.create(session, owner=owner, **kwargs)


@pytest_asyncio.fixture
async def document_factory():
    """Fixture that returns the DocumentFactory class."""
    return DocumentFactory
