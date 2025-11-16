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
        mock_client = type("MockClient", (), {})()
        with pytest.raises(Exception):  # Will fail due to database connection
            await process_hash_notarization(mock_client, doc_id)

    @pytest.mark.asyncio
    async def test_successful_hash_notarization(self, mock_document, monkeypatch, worker_settings):
        """Test complete hash notarization workflow"""
        from tests.mocks.mock_orm import MockDocumentRepository, MockAsyncSession
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
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)
        monkeypatch.setattr("abs_worker.error_handler.get_settings", lambda: worker_settings)

        # Create mock client with required methods
        mock_client = type("MockClient", (), {"notarize_hash": blockchain.notarize_hash})()

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
        await process_hash_notarization(mock_client, mock_document.id)

        # Verify document status progression
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "on_chain"
        assert updated_doc.transaction_hash is not None
        assert updated_doc.signed_json_path == f"/certs/{mock_document.id}.json"
        assert updated_doc.signed_pdf_path == f"/certs/{mock_document.id}.pdf"
        assert session.committed is True

    @pytest.mark.asyncio
    async def test_certificates_generated(self, mock_document, monkeypatch, worker_settings):
        """Test that certificates are generated when enabled"""
        from tests.mocks.mock_orm import MockDocumentRepository, MockAsyncSession
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

        async def mock_monitor_transaction(*args, **kwargs):
            return None

        monkeypatch.setattr("abs_worker.notarization.monitor_transaction", mock_monitor_transaction)
        monkeypatch.setattr("abs_worker.notarization.generate_signed_json", mock_generate_json)
        monkeypatch.setattr("abs_worker.notarization.generate_signed_pdf", mock_generate_pdf)
        monkeypatch.setattr("abs_worker.notarization.logger", logger)
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)
        monkeypatch.setattr("abs_worker.error_handler.get_settings", lambda: worker_settings)

        # Execute notarization
        await process_hash_notarization(mock_client, mock_document.id)

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

        # Create mock client
        mock_client = type("MockClient", (), {})()

        # Mock error handler to avoid database access
        async def mock_handle_failed_transaction(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "abs_worker.notarization.handle_failed_transaction", mock_handle_failed_transaction
        )

        # Execute notarization - should raise error for non-PENDING status
        with pytest.raises(ValueError, match="is not in PENDING status"):
            await process_hash_notarization(mock_client, mock_document.id)

    @pytest.mark.asyncio
    async def test_hash_notarization_monitoring_failure(
        self, mock_document, monkeypatch, worker_settings
    ):
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
        # Create mock client
        mock_client = type("MockClient", (), {"notarize_hash": blockchain.notarize_hash})()
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
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)
        monkeypatch.setattr("abs_worker.error_handler.get_settings", lambda: worker_settings)

        # Should handle monitoring failure gracefully
        with pytest.raises(Exception, match="Monitoring timeout"):
            await process_hash_notarization(mock_client, mock_document.id)

        # Document should be marked as ERROR
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "error"

    @pytest.mark.asyncio
    async def test_hash_notarization_certificate_failure(
        self, mock_document, monkeypatch, worker_settings
    ):
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
        # Create mock client
        mock_client = type("MockClient", (), {"notarize_hash": blockchain.notarize_hash})()

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
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)
        monkeypatch.setattr("abs_worker.error_handler.get_settings", lambda: worker_settings)

        # Should handle certificate failure gracefully
        with pytest.raises(Exception, match="JSON generation failed"):
            await process_hash_notarization(mock_client, mock_document.id)

        # Document should be marked as ERROR
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "error"


class TestProcessNftNotarization:
    """Tests for process_nft_notarization function"""

    @pytest.mark.asyncio
    async def test_process_nft_stub(self, monkeypatch):
        """Test process_nft_notarization with minimal mocking"""
        from tests.mocks.mock_utils import MockLogger

        # Mock just enough to prevent database connections
        logger = MockLogger("test")

        async def mock_handle_failed_transaction(*args, **kwargs):
            pass

        monkeypatch.setattr(
            "abs_worker.notarization.handle_failed_transaction", mock_handle_failed_transaction
        )
        monkeypatch.setattr("abs_worker.notarization.logger", logger)

        doc_id = 456

        # Should attempt to run but fail due to missing database setup
        # This tests that the function signature and basic structure work
        mock_client = type("MockClient", (), {})()
        with pytest.raises(Exception):  # Will fail due to database connection
            await process_nft_notarization(mock_client, doc_id)

    @pytest.mark.asyncio
    async def test_successful_nft_minting(self, mock_nft_document, monkeypatch):
        """Test complete NFT minting workflow"""
        from tests.mocks.mock_orm import MockDocumentRepository, MockAsyncSession
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_nft_document.id] = mock_nft_document
        session = MockAsyncSession()
        blockchain = MockBlockchain()
        logger = MockLogger("test")

        # Mock file reading
        import tempfile
        import os

        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"fake pdf content")
            temp_file_path = tmp.name

        try:
            # Set the document's file_path to the temp file
            mock_nft_document.file_path = temp_file_path

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
            mock_client = type(
                "MockClient",
                (),
                {
                    "upload_to_arweave": blockchain.upload_to_arweave,
                    "mint_nft": blockchain.mint_nft,
                    "mint_nft_from_file": blockchain.mint_nft_from_file,
                },
            )()
            monkeypatch.setattr("abs_worker.notarization.BlockchainClient", lambda: mock_client)

            async def mock_monitor_transaction(*args, **kwargs):
                return None

            monkeypatch.setattr(
                "abs_worker.notarization.monitor_transaction", mock_monitor_transaction
            )

            async def mock_generate_json(doc):
                return f"/certs/{doc.id}.json"

            async def mock_generate_pdf(doc):
                return f"/certs/{doc.id}.pdf"

            monkeypatch.setattr("abs_worker.notarization.generate_signed_json", mock_generate_json)
            monkeypatch.setattr("abs_worker.notarization.generate_signed_pdf", mock_generate_pdf)
            monkeypatch.setattr("abs_worker.notarization.logger", logger)

            # Execute NFT minting
            await process_nft_notarization(mock_client, mock_nft_document.id)

            # Verify document status progression
            updated_doc = repo.documents[mock_nft_document.id]
            assert updated_doc.status.value == "on_chain"
            assert updated_doc.transaction_hash is not None
            assert updated_doc.arweave_file_url is not None
            assert updated_doc.arweave_metadata_url is not None
            assert updated_doc.nft_token_id is not None
            assert updated_doc.signed_json_path == f"/certs/{mock_nft_document.id}.json"
            assert updated_doc.signed_pdf_path == f"/certs/{mock_nft_document.id}.pdf"
            assert session.committed is True

        finally:
            # Clean up temp file
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_arweave_upload_error(self, mock_nft_document, monkeypatch):
        """Test handling of Arweave upload errors"""
        from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, MockAsyncSession
        from tests.mocks.mock_utils import MockLogger
        import tempfile
        import os

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_nft_document.id] = mock_nft_document
        session = MockAsyncSession()
        logger = MockLogger("test")

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"fake pdf content")
            temp_file_path = tmp.name

        try:
            mock_nft_document.file_path = temp_file_path

            # Mock BlockchainClient that fails on Arweave upload
            class FailingArweaveClient:
                async def upload_to_arweave(self, file_data: bytes, content_type: str):
                    raise Exception("Arweave upload failed: network timeout")

                async def mint_nft(self, *args, **kwargs):
                    return {"transactionHash": "0xabc123"}

                async def mint_nft_from_file(self, *args, **kwargs):
                    raise Exception("Arweave upload failed: network timeout")

            # Mock dependencies
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def mock_get_session():
                try:
                    yield session
                finally:
                    await session.close()

            monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
            monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)
            monkeypatch.setattr(
                "abs_worker.notarization.BlockchainClient", lambda: FailingArweaveClient()
            )

            # Mock error handler to track errors
            error_captured = []

            async def mock_handle_failed_transaction(doc_id, error):
                error_captured.append((doc_id, str(error)))
                await repo.update(doc_id, status=DocStatus.ERROR, error_message=str(error))

            monkeypatch.setattr(
                "abs_worker.notarization.handle_failed_transaction",
                mock_handle_failed_transaction,
            )
            monkeypatch.setattr("abs_worker.notarization.logger", logger)

            # Should raise error when Arweave upload fails
            client = FailingArweaveClient()
            with pytest.raises(Exception, match="Arweave upload failed"):
                await process_nft_notarization(client, mock_nft_document.id)

            # Verify error was handled
            assert len(error_captured) == 1
            assert error_captured[0][0] == mock_nft_document.id
            assert "Arweave upload failed" in error_captured[0][1]

            # Verify document marked as error
            updated_doc = repo.documents[mock_nft_document.id]
            assert updated_doc.status.value == "error"

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_nft_minting_error(self, mock_nft_document, monkeypatch):
        """Test handling of NFT minting errors"""
        from tests.mocks.mock_orm import MockDocumentRepository, DocStatus, MockAsyncSession
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        import tempfile
        import os

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_nft_document.id] = mock_nft_document
        session = MockAsyncSession()
        blockchain = MockBlockchain()
        logger = MockLogger("test")

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"fake pdf content")
            temp_file_path = tmp.name

        try:
            mock_nft_document.file_path = temp_file_path

            # Mock BlockchainClient that succeeds on Arweave but fails on NFT minting
            class FailingMintClient:
                async def upload_to_arweave(self, file_data: bytes, content_type: str):
                    return await blockchain.upload_to_arweave(file_data, content_type)

                async def mint_nft(self, owner_address, metadata_uri, token_id):
                    raise Exception("NFT minting failed: contract execution reverted")

                async def mint_nft_from_file(self, *args, **kwargs):
                    raise Exception("NFT minting failed: contract execution reverted")

            # Mock dependencies
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def mock_get_session():
                try:
                    yield session
                finally:
                    await session.close()

            monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
            monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)
            monkeypatch.setattr(
                "abs_worker.notarization.BlockchainClient", lambda: FailingMintClient()
            )

            # Mock error handler to track errors
            error_captured = []

            async def mock_handle_failed_transaction(doc_id, error):
                error_captured.append((doc_id, str(error)))
                await repo.update(doc_id, status=DocStatus.ERROR, error_message=str(error))

            monkeypatch.setattr(
                "abs_worker.notarization.handle_failed_transaction",
                mock_handle_failed_transaction,
            )
            monkeypatch.setattr("abs_worker.notarization.logger", logger)

            # Should raise error when NFT minting fails
            client = FailingMintClient()
            with pytest.raises(Exception, match="NFT minting failed"):
                await process_nft_notarization(client, mock_nft_document.id)

            # Verify error was handled
            assert len(error_captured) == 1
            assert error_captured[0][0] == mock_nft_document.id
            assert "NFT minting failed" in error_captured[0][1]

            # Verify document marked as error
            updated_doc = repo.documents[mock_nft_document.id]
            assert updated_doc.status.value == "error"

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_nft_document_updated_correctly(self, mock_nft_document, monkeypatch):
        """Test that NFT document is updated with all required fields"""
        from tests.mocks.mock_orm import MockDocumentRepository, MockAsyncSession
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        import tempfile
        import os

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_nft_document.id] = mock_nft_document
        session = MockAsyncSession()
        blockchain = MockBlockchain()
        logger = MockLogger("test")

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"fake pdf content")
            temp_file_path = tmp.name

        try:
            mock_nft_document.file_path = temp_file_path

            # Mock dependencies
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def mock_get_session():
                try:
                    yield session
                finally:
                    await session.close()

            monkeypatch.setattr("abs_worker.notarization.get_session", mock_get_session)
            monkeypatch.setattr("abs_worker.notarization.DocumentRepository", lambda s: repo)

            # Mock BlockchainClient
            mock_client = type(
                "MockClient",
                (),
                {
                    "upload_to_arweave": blockchain.upload_to_arweave,
                    "mint_nft": blockchain.mint_nft,
                    "mint_nft_from_file": blockchain.mint_nft_from_file,
                },
            )()
            monkeypatch.setattr("abs_worker.notarization.BlockchainClient", lambda: mock_client)

            async def mock_monitor_transaction(*args, **kwargs):
                return None

            monkeypatch.setattr(
                "abs_worker.notarization.monitor_transaction", mock_monitor_transaction
            )

            async def mock_generate_json(doc):
                return f"/certs/{doc.id}.json"

            async def mock_generate_pdf(doc):
                return f"/certs/{doc.id}.pdf"

            monkeypatch.setattr("abs_worker.notarization.generate_signed_json", mock_generate_json)
            monkeypatch.setattr("abs_worker.notarization.generate_signed_pdf", mock_generate_pdf)
            monkeypatch.setattr("abs_worker.notarization.logger", logger)

            # Execute NFT minting
            await process_nft_notarization(mock_client, mock_nft_document.id)

            # Verify ALL NFT-specific fields are updated correctly
            updated_doc = repo.documents[mock_nft_document.id]

            # Verify required fields from acceptance criteria
            assert updated_doc.arweave_file_url is not None, "arweave_file_url must be set"
            assert updated_doc.arweave_file_url.startswith(
                "https://arweave.net/"
            ), "arweave_file_url must be valid Arweave URL"

            assert updated_doc.arweave_metadata_url is not None, "arweave_metadata_url must be set"
            assert updated_doc.arweave_metadata_url.startswith(
                "https://arweave.net/"
            ), "arweave_metadata_url must be valid Arweave URL"

            assert updated_doc.nft_token_id is not None, "nft_token_id must be set"
            assert isinstance(updated_doc.nft_token_id, int), "nft_token_id must be an integer"

            assert updated_doc.transaction_hash is not None, "transaction_hash must be set"
            assert updated_doc.transaction_hash.startswith(
                "0x"
            ), "transaction_hash must be valid hex"

            assert updated_doc.signed_json_path is not None, "signed_json_path must be set"
            assert (
                updated_doc.signed_json_path == f"/certs/{mock_nft_document.id}.json"
            ), "signed_json_path must match expected path"

            assert updated_doc.signed_pdf_path is not None, "signed_pdf_path must be set"
            assert (
                updated_doc.signed_pdf_path == f"/certs/{mock_nft_document.id}.pdf"
            ), "signed_pdf_path must match expected path"

            # Verify status is ON_CHAIN
            assert updated_doc.status.value == "on_chain", "status must be ON_CHAIN"

            # Verify session was committed
            assert session.committed is True, "session must be committed"

        finally:
            os.unlink(temp_file_path)
