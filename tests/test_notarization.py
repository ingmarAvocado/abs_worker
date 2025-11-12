"""
Tests for notarization module
"""

import pytest
from contextlib import asynccontextmanager
from abs_worker.notarization import process_hash_notarization, process_nft_notarization


class TestProcessHashNotarization:
    """Tests for process_hash_notarization function"""

    @pytest.mark.asyncio
    async def test_process_hash_stub(self, monkeypatch):
        """Test process_hash_notarization with minimal mocking"""
        from tests.mocks.mock_utils import MockLogger

        # Mock just enough to prevent database connections
        logger = MockLogger("test")

        async def mock_handle_failed_transaction(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "abs_worker.notarization.handle_failed_transaction", mock_handle_failed_transaction
        )
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        doc_id = 123

        # Should attempt to run but fail due to missing database setup
        # This tests that the function signature and basic structure work
        with pytest.raises(Exception):  # Will fail due to database connection
            await process_hash_notarization(doc_id)

    @pytest.mark.asyncio
    async def test_successful_hash_notarization(self, mock_document, monkeypatch):
        """Test complete hash notarization workflow"""
        from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, MockAsyncSession
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_document.id] = mock_document
        session = MockAsyncSession()
        blockchain = MockBlockchain()
        logger = MockLogger("test")

        # Mock dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)
        # Mock BlockchainClient
        mock_client = type("MockClient", (), {"notarize_hash": blockchain.notarize_hash})()
        monkeypatch.setattr("abs_worker.notarization.BlockchainClient", lambda: mock_client)

        async def mock_monitor_transaction(*args, **kwargs):
            return None

        monkeypatch.setattr("abs_worker.notarization.monitor_transaction", mock_monitor_transaction)

        async def mock_generate_json(doc):
            return f"/certs/{doc.id}.json"

        async def mock_generate_pdf(doc):
            return f"/certs/{doc.id}.pdf"

        monkeypatch.setattr("abs_worker.notarization.generate_signed_json", mock_generate_json)
        monkeypatch.setattr("abs_worker.notarization.generate_signed_pdf", mock_generate_pdf)
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        # Execute notarization
        await process_hash_notarization(mock_document.id)

        # Verify document status progression
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "on_chain"
        assert updated_doc.transaction_hash is not None
        assert updated_doc.signed_json_path == f"/certs/{mock_document.id}.json"
        assert updated_doc.signed_pdf_path == f"/certs/{mock_document.id}.pdf"
        assert session.committed is True

    @pytest.mark.asyncio
    async def test_document_not_found_raises(self, monkeypatch):
        """Test that missing document raises error"""
        from tests.mocks.mock_orm import MockDocumentRepository, MockAsyncSession
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()  # Empty repository
        session = MockAsyncSession()
        logger = MockLogger("test")

        # Mock dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)

        # Mock error handler to avoid database access
        async def mock_handle_failed_transaction(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "abs_worker.notarization.handle_failed_transaction", mock_handle_failed_transaction
        )
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        # Should raise ValueError for non-existent document
        with pytest.raises(ValueError, match="Document 999 not found"):
            await process_hash_notarization(999)

    @pytest.mark.asyncio
    async def test_blockchain_error_handled(self, mock_document, monkeypatch):
        """Test that blockchain errors are handled properly"""
        from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, MockAsyncSession
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_document.id] = mock_document
        session = MockAsyncSession()
        logger = MockLogger("test")

        # Mock dependencies with failing blockchain
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        async def failing_notarize_hash(*args, **kwargs):
            raise Exception("Transaction reverted")

        monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)
        # Mock BlockchainClient with failing method
        mock_client = type("MockClient", (), {"notarize_hash": failing_notarize_hash})()
        monkeypatch.setattr("abs_worker.notarization.BlockchainClient", lambda: mock_client)

        # Mock error handler to update document status
        async def mock_handle_failed_transaction(doc_id, error):
            # Simulate what the real handler does
            await repo.update(doc_id, status=DocStatus.ERROR, error_message=str(error))

        monkeypatch.setattr(
            "abs_worker.notarization.handle_failed_transaction", mock_handle_failed_transaction
        )
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        # Should handle blockchain error gracefully
        with pytest.raises(Exception, match="Transaction reverted"):
            await process_hash_notarization(mock_document.id)

        # Document should be marked as ERROR
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "error"

    @pytest.mark.asyncio
    async def test_certificates_generated(self, mock_document, monkeypatch):
        """Test that certificates are generated when enabled"""
        from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, MockAsyncSession
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_document.id] = mock_document
        session = MockAsyncSession()
        blockchain = MockBlockchain()
        logger = MockLogger("test")

        # Track certificate generation calls
        json_calls = []
        pdf_calls = []

        async def mock_generate_json(doc):
            json_calls.append(doc)
            return f"/certs/{doc.id}.json"

        async def mock_generate_pdf(doc):
            pdf_calls.append(doc)
            return f"/certs/{doc.id}.pdf"

        # Mock dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)
        # Mock BlockchainClient
        mock_client = type("MockClient", (), {"notarize_hash": blockchain.notarize_hash})()
        monkeypatch.setattr("abs_worker.notarization.BlockchainClient", lambda: mock_client)

        async def mock_monitor_transaction(*args, **kwargs):
            return None

        monkeypatch.setattr("abs_worker.notarization.monitor_transaction", mock_monitor_transaction)
        monkeypatch.setattr("abs_worker.notarization.generate_signed_json", mock_generate_json)
        monkeypatch.setattr("abs_worker.notarization.generate_signed_pdf", mock_generate_pdf)
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        # Execute notarization
        await process_hash_notarization(mock_document.id)

        # Verify certificates were generated
        assert len(json_calls) == 1
        assert len(pdf_calls) == 1
        assert json_calls[0] == mock_document
        assert pdf_calls[0] == mock_document

        # Verify document has certificate paths
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.signed_json_path == f"/certs/{mock_document.id}.json"
        assert updated_doc.signed_pdf_path == f"/certs/{mock_document.id}.pdf"

    @pytest.mark.asyncio
    async def test_hash_notarization_with_invalid_status(self, mock_document, monkeypatch):
        """Test that documents with invalid status are handled properly"""
        from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, MockAsyncSession
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        # Set document to already processing status
        mock_document.status = DocStatus.PROCESSING
        repo.documents[mock_document.id] = mock_document
        session = MockAsyncSession()
        blockchain = MockBlockchain()
        logger = MockLogger("test")

        # Mock dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)
        # Mock BlockchainClient
        mock_client = type("MockClient", (), {"notarize_hash": blockchain.notarize_hash})()
        monkeypatch.setattr("abs_worker.notarization.BlockchainClient", lambda: mock_client)

        async def mock_monitor_transaction(*args, **kwargs):
            return None

        monkeypatch.setattr("abs_worker.notarization.monitor_transaction", mock_monitor_transaction)

        async def mock_generate_json(doc):
            return f"/certs/{doc.id}.json"

        async def mock_generate_pdf(doc):
            return f"/certs/{doc.id}.pdf"

        monkeypatch.setattr("abs_worker.notarization.generate_signed_json", mock_generate_json)
        monkeypatch.setattr("abs_worker.notarization.generate_signed_pdf", mock_generate_pdf)
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        # Mock error handler to avoid database access
        async def mock_handle_failed_transaction(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "abs_worker.notarization.handle_failed_transaction", mock_handle_failed_transaction
        )

        # Execute notarization - should raise error for non-PENDING status
        with pytest.raises(ValueError, match="is not in PENDING status"):
            await process_hash_notarization(mock_document.id)

    @pytest.mark.asyncio
    async def test_hash_notarization_monitoring_failure(self, mock_document, monkeypatch):
        """Test handling of transaction monitoring failures"""
        from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, MockAsyncSession
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_document.id] = mock_document
        session = MockAsyncSession()
        blockchain = MockBlockchain()
        logger = MockLogger("test")

        # Mock dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        async def failing_monitor_transaction(*args, **kwargs):
            raise Exception("Monitoring timeout")

        monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)
        # Mock BlockchainClient
        mock_client = type("MockClient", (), {"notarize_hash": blockchain.notarize_hash})()
        monkeypatch.setattr("abs_worker.notarization.BlockchainClient", lambda: mock_client)
        monkeypatch.setattr(
            "abs_worker.notarization.monitor_transaction", failing_monitor_transaction
        )

        # Mock error handler to update document status
        async def mock_handle_failed_transaction(doc_id, error):
            # Simulate what the real handler does
            await repo.update(doc_id, status=DocStatus.ERROR, error_message=str(error))

        monkeypatch.setattr(
            "abs_worker.notarization.handle_failed_transaction", mock_handle_failed_transaction
        )
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        # Should handle monitoring failure gracefully
        with pytest.raises(Exception, match="Monitoring timeout"):
            await process_hash_notarization(mock_document.id)

        # Document should be marked as ERROR
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "error"

    @pytest.mark.asyncio
    async def test_hash_notarization_certificate_failure(self, mock_document, monkeypatch):
        """Test handling of certificate generation failures"""
        from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, MockAsyncSession
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_document.id] = mock_document
        session = MockAsyncSession()
        blockchain = MockBlockchain()
        logger = MockLogger("test")

        # Mock dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        async def failing_generate_json(doc):
            raise Exception("JSON generation failed")

        monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)
        # Mock BlockchainClient
        mock_client = type("MockClient", (), {"notarize_hash": blockchain.notarize_hash})()
        monkeypatch.setattr("abs_worker.notarization.BlockchainClient", lambda: mock_client)

        async def mock_monitor_transaction(*args, **kwargs):
            return None

        monkeypatch.setattr("abs_worker.notarization.monitor_transaction", mock_monitor_transaction)
        monkeypatch.setattr("abs_worker.notarization.generate_signed_json", failing_generate_json)

        async def mock_generate_pdf(doc):
            return f"/certs/{doc.id}.pdf"

        monkeypatch.setattr("abs_worker.notarization.generate_signed_pdf", mock_generate_pdf)

        # Mock error handler to update document status
        async def mock_handle_failed_transaction(doc_id, error):
            # Simulate what the real handler does
            await repo.update(doc_id, status=DocStatus.ERROR, error_message=str(error))

        monkeypatch.setattr(
            "abs_worker.notarization.handle_failed_transaction", mock_handle_failed_transaction
        )
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        # Should handle certificate failure gracefully
        with pytest.raises(Exception, match="JSON generation failed"):
            await process_hash_notarization(mock_document.id)

        # Document should be marked as ERROR
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "error"


class TestProcessNftNotarization:
    """Tests for process_nft_notarization function"""

    @pytest.mark.asyncio
    async def test_process_nft_stub(self):
        """Test process_nft_notarization stub implementation"""
        doc_id = 456

        # Should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="NFT notarization not yet implemented"):
            await process_nft_notarization(doc_id)

    @pytest.mark.asyncio
    async def test_successful_nft_minting(self, mock_nft_document, mock_blockchain):
        """Test complete NFT minting workflow"""
        # TODO: Implement when abs_orm and abs_blockchain are available
        # This would test:
        # 1. Document status updated to PROCESSING
        # 2. File uploaded to Arweave
        # 3. Metadata uploaded to Arweave
        # 4. NFT minted on blockchain
        # 5. Transaction monitored
        # 6. Certificates generated
        # 7. Document updated with all NFT details
        pass

    @pytest.mark.asyncio
    async def test_arweave_upload_error(self, mock_nft_document, mock_blockchain):
        """Test handling of Arweave upload errors"""
        # TODO: Implement with Arweave error mock
        pass

    @pytest.mark.asyncio
    async def test_nft_minting_error(self, mock_nft_document, mock_blockchain):
        """Test handling of NFT minting errors"""
        # TODO: Implement with NFT minting error mock
        pass

    @pytest.mark.asyncio
    async def test_nft_document_updated_correctly(self, mock_nft_document, mock_blockchain):
        """Test that NFT document is updated with all required fields"""
        # TODO: Implement with field verification:
        # - arweave_file_url
        # - arweave_metadata_url
        # - nft_token_id
        # - transaction_hash
        # - signed_json_path
        # - signed_pdf_path
        pass
