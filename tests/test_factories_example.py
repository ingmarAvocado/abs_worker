"""
Example tests demonstrating factory usage patterns.

This file shows different ways to use the factory pattern for creating test data.
"""

import pytest
from abs_orm.models import DocStatus, DocType
from tests.factories import UserFactory, DocumentFactory, ApiKeyFactory


class TestFactoryBasicUsage:
    """Demonstrate basic factory usage with fixtures."""

    @pytest.mark.asyncio
    async def test_with_fixture(self, test_user, test_document):
        """Use pre-configured fixtures (easiest for simple tests)."""
        # Fixtures are created automatically with sensible defaults
        assert test_user.id is not None
        assert test_document.owner_id == test_user.id
        assert test_document.status == DocStatus.PENDING

    @pytest.mark.asyncio
    async def test_with_factory_class(self, db_context, user_factory, document_factory):
        """Use factory classes directly for more control."""
        # Create a user with specific email
        user = await user_factory.create(
            db_context.session,
            email="custom@example.com"
        )
        await db_context.commit()

        # Create a document for that user
        doc = await document_factory.create_pending(
            db_context.session,
            owner=user,
            file_name="custom_file.pdf"
        )
        await db_context.commit()

        assert user.email == "custom@example.com"
        assert doc.file_name == "custom_file.pdf"
        assert doc.owner_id == user.id


class TestFactoryAdvancedPatterns:
    """Demonstrate advanced factory patterns."""

    @pytest.mark.asyncio
    async def test_create_batch(self, db_context):
        """Create multiple records at once."""
        # Create 5 users in one call
        users = await UserFactory.create_batch(db_context.session, count=5)
        await db_context.commit()

        assert len(users) == 5
        # All have unique emails
        emails = [u.email for u in users]
        assert len(emails) == len(set(emails))

    @pytest.mark.asyncio
    async def test_workflow_scenario(self, db_context):
        """Create a complete workflow scenario."""
        # Create a user with multiple documents in different states
        user = await UserFactory.create(db_context.session)

        pending = await DocumentFactory.create_pending(db_context.session, owner=user)
        processing = await DocumentFactory.create_processing(db_context.session, owner=user)
        on_chain = await DocumentFactory.create_on_chain(db_context.session, owner=user)
        error = await DocumentFactory.create_error(db_context.session, owner=user)

        await db_context.commit()

        # Verify the complete workflow exists
        assert pending.status == DocStatus.PENDING
        assert processing.status == DocStatus.PROCESSING
        assert on_chain.status == DocStatus.ON_CHAIN
        assert on_chain.transaction_hash is not None
        assert error.status == DocStatus.ERROR
        assert error.error_message is not None

    @pytest.mark.asyncio
    async def test_nft_document(self, db_context):
        """Create NFT documents with complete blockchain data."""
        user = await UserFactory.create(db_context.session)

        # Create a completed NFT
        nft = await DocumentFactory.create_nft(db_context.session, owner=user)
        await db_context.commit()

        assert nft.type == DocType.NFT
        assert nft.status == DocStatus.ON_CHAIN
        assert nft.arweave_file_url is not None
        assert nft.arweave_metadata_url is not None
        assert nft.nft_token_id is not None
        assert nft.transaction_hash is not None

    @pytest.mark.asyncio
    async def test_user_with_relationships(self, db_context):
        """Create users with related documents and API keys."""
        # Create user with documents
        user, documents = await UserFactory.create_with_documents(
            db_context.session,
            doc_count=3
        )
        await db_context.commit()

        assert len(documents) == 3
        assert all(doc.owner_id == user.id for doc in documents)

        # Add API keys to the same user
        api_key = await ApiKeyFactory.create(db_context.session, owner=user)
        await db_context.commit()

        assert api_key.owner_id == user.id


class TestFactoryHelpers:
    """Demonstrate factory helper methods."""

    @pytest.mark.asyncio
    async def test_random_data_generation(self, db_context):
        """Factories generate random but valid data."""
        # Create multiple documents - each has unique hash
        doc1 = await DocumentFactory.create(db_context.session)
        doc2 = await DocumentFactory.create(db_context.session)
        await db_context.commit()

        # File hashes are unique and properly formatted
        assert doc1.file_hash != doc2.file_hash
        assert doc1.file_hash.startswith("0x")
        assert len(doc1.file_hash) == 66  # 0x + 64 hex chars

    @pytest.mark.asyncio
    async def test_blockchain_specific_data(self, db_context):
        """Factories generate proper blockchain-specific data."""
        doc = await DocumentFactory.create_on_chain(db_context.session)
        await db_context.commit()

        # Transaction hash is properly formatted
        assert doc.transaction_hash.startswith("0x")
        assert len(doc.transaction_hash) == 66

        # Create NFT with Arweave URLs
        nft = await DocumentFactory.create_nft(db_context.session)
        await db_context.commit()

        # Arweave URLs are properly formatted
        assert nft.arweave_file_url.startswith("https://arweave.net/")
        assert len(nft.arweave_file_url.split("/")[-1]) == 43  # Arweave ID length


class TestFactoryWithRepositories:
    """Show how factories work with repositories."""

    @pytest.mark.asyncio
    async def test_query_factory_created_data(self, db_context):
        """Factory-created data can be queried through repositories."""
        # Create test data
        user = await UserFactory.create(db_context.session, email="query@test.com")
        doc = await DocumentFactory.create_pending(db_context.session, owner=user)
        await db_context.commit()

        # Query it back through repository
        found_user = await db_context.users.get_by_email("query@test.com")
        found_doc = await db_context.documents.get(doc.id)

        assert found_user.id == user.id
        assert found_doc.id == doc.id
        assert found_doc.owner_id == found_user.id

    @pytest.mark.asyncio
    async def test_status_queries(self, db_context):
        """Create various statuses and query them."""
        user = await UserFactory.create(db_context.session)

        # Create documents in different states
        doc1 = await DocumentFactory.create_pending(db_context.session, owner=user)
        doc2 = await DocumentFactory.create_pending(db_context.session, owner=user)
        doc3 = await DocumentFactory.create_processing(db_context.session, owner=user)
        doc4 = await DocumentFactory.create_on_chain(db_context.session, owner=user)

        await db_context.commit()

        # Query by status using repository
        user_docs = await db_context.documents.get_user_documents(user.id)

        # Filter by status in memory (or use repository methods)
        pending_docs = [d for d in user_docs if d.status == DocStatus.PENDING]
        processing_docs = [d for d in user_docs if d.status == DocStatus.PROCESSING]
        on_chain_docs = [d for d in user_docs if d.status == DocStatus.ON_CHAIN]

        assert len(pending_docs) == 2
        assert len(processing_docs) == 1
        assert len(on_chain_docs) == 1


class TestMigrationFromMocks:
    """Show backward compatibility with old mock fixtures."""

    @pytest.mark.asyncio
    async def test_old_mock_fixture_still_works(self, mock_document):
        """Old mock_document fixture now uses real database."""
        # This test uses the old fixture name but gets real data
        assert mock_document.id is not None
        assert mock_document.file_hash.startswith("0x")

    @pytest.mark.asyncio
    async def test_new_fixture_name(self, test_document):
        """New fixture name - recommended for new tests."""
        # Same functionality, clearer naming
        assert test_document.id is not None
        assert test_document.file_hash.startswith("0x")
