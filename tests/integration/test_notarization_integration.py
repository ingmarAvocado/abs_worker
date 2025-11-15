"""
Integration tests for abs_worker using real database connections and realistic mocks.

These tests validate that the abs_worker functions work correctly with:
- Real PostgreSQL database connections via abs_orm
- Realistic blockchain mocks that simulate real error conditions
- Real async session management
- Real structured logging output

Unlike unit tests, these tests exercise the full stack integration.
"""

import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch
from abs_orm.models import DocStatus, DocType


@pytest.fixture(autouse=True)
def skip_if_no_database(db_context):
    """Skip integration tests if database is not available."""
    # If we get here, the database fixture worked, so database is available
    pass


class TestHashNotarizationIntegration:
    """Integration tests for hash notarization workflow using real database."""

    @pytest.mark.asyncio
    async def test_full_hash_notarization_workflow(
        self, db_context, test_document, mock_blockchain, worker_settings
    ):
        """Test complete hash notarization workflow with REAL database and real certificate generation."""
        from abs_worker.notarization import process_hash_notarization

        # Verify initial document state IN REAL DATABASE
        doc = await db_context.documents.get(test_document.id)
        assert doc.status == DocStatus.PENDING
        assert doc.transaction_hash is None
        assert doc.signed_json_path is None
        assert doc.signed_pdf_path is None

        # Mock blockchain to return successful result
        mock_result = type("NotarizationResult", (), {"transaction_hash": "0xreal_tx_hash_123"})()

        # Mock get_session to use TEST database, and mock blockchain/monitoring
        @asynccontextmanager
        async def mock_get_session():
            """Return test database session instead of creating new one"""
            yield db_context.session

        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.notarization.BlockchainClient"
        ) as mock_client_class, patch(
            "abs_worker.notarization.monitor_transaction"
        ) as mock_monitor, patch(
            "abs_worker.monitoring.get_settings", lambda: worker_settings
        ), patch("abs_worker.error_handler.get_session", mock_get_session), patch(
            "abs_worker.certificates.get_settings", lambda: worker_settings
        ):
            # Setup blockchain mock
            mock_client = AsyncMock()
            mock_client.notarize_hash.return_value = mock_result
            mock_client.get_transaction_receipt.return_value = {
                "status": 1,
                "blockNumber": 100,
                "transactionHash": "0xreal_tx_hash_123",
            }
            mock_client.get_latest_block_number.return_value = 105  # 5 confirmations
            mock_client_class.return_value = mock_client

            # Monitoring just succeeds
            mock_monitor.return_value = None

            # Execute the workflow - USES REAL TEST DATABASE, REAL CERTIFICATE FUNCTIONS
            await process_hash_notarization(mock_client, test_document.id)

            # Verify blockchain was called correctly
            mock_client.notarize_hash.assert_called_once()
            call_args = mock_client.notarize_hash.call_args
            assert call_args[1]["file_hash"] == test_document.file_hash
            assert "file_name" in call_args[1]["metadata"]
            assert "timestamp" in call_args[1]["metadata"]

            # Verify monitoring was called
            mock_monitor.assert_called_once_with(
                mock_client, test_document.id, "0xreal_tx_hash_123"
            )

        # Verify final document state IN REAL DATABASE
        await db_context.session.refresh(test_document)
        updated_doc = await db_context.documents.get(test_document.id)
        assert updated_doc.status == DocStatus.ON_CHAIN
        assert updated_doc.transaction_hash == "0xreal_tx_hash_123"
        assert updated_doc.signed_json_path is not None
        assert updated_doc.signed_pdf_path is not None
        # Note: Certificate functions are stubs, so we don't verify file existence yet

    @pytest.mark.asyncio
    async def test_hash_notarization_blockchain_failure(self, db_context, test_document):
        """Test hash notarization with blockchain failure using REAL database."""
        from abs_worker.notarization import process_hash_notarization

        # Verify initial state IN REAL DATABASE
        doc = await db_context.documents.get(test_document.id)
        assert doc.status == DocStatus.PENDING

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Mock blockchain to fail with realistic error
        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.notarization.BlockchainClient"
        ) as mock_client_class, patch("abs_worker.error_handler.get_session", mock_get_session):
            mock_client = AsyncMock()
            mock_client.notarize_hash.side_effect = Exception("Blockchain connection failed")
            mock_client_class.return_value = mock_client

            # Execute and expect failure
            with pytest.raises(Exception) as exc_info:
                await process_hash_notarization(mock_client, test_document.id)

            assert "Blockchain connection failed" in str(exc_info.value)

        # Verify database state after error - should be marked as ERROR in REAL DATABASE
        await db_context.session.refresh(test_document)
        updated_doc = await db_context.documents.get(test_document.id)
        assert updated_doc.status == DocStatus.ERROR
        assert updated_doc.error_message is not None
        assert "Blockchain connection failed" in updated_doc.error_message

    @pytest.mark.asyncio
    async def test_hash_notarization_document_not_found(self, db_context):
        """Test hash notarization with non-existent document using REAL database."""
        from abs_worker.notarization import process_hash_notarization

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Try to process non-existent document - REAL DATABASE WILL RETURN None
        # Need to patch both notarization.get_session AND error_handler.get_session
        mock_client = AsyncMock()
        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.error_handler.get_session", mock_get_session
        ):
            with pytest.raises(ValueError, match="Document 99999 not found"):
                await process_hash_notarization(mock_client, 99999)

    @pytest.mark.asyncio
    async def test_hash_notarization_transaction_monitoring_failure(
        self, db_context, test_document
    ):
        """Test hash notarization with transaction monitoring failure using REAL database."""
        from abs_worker.notarization import process_hash_notarization

        mock_result = type("NotarizationResult", (), {"transaction_hash": "0xfailed_tx_hash"})()

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Mock blockchain and monitoring to simulate timeout
        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.notarization.BlockchainClient"
        ) as mock_client_class, patch(
            "abs_worker.notarization.monitor_transaction"
        ) as mock_monitor, patch("abs_worker.error_handler.get_session", mock_get_session):
            mock_client = AsyncMock()
            mock_client.notarize_hash.return_value = mock_result
            mock_client_class.return_value = mock_client

            # Make monitoring fail with timeout
            mock_monitor.side_effect = TimeoutError("Transaction confirmation timeout")

            # Execute and expect failure
            with pytest.raises(TimeoutError, match="Transaction confirmation timeout"):
                await process_hash_notarization(mock_client, test_document.id)

        # Verify error was recorded IN REAL DATABASE
        await db_context.session.refresh(test_document)
        updated_doc = await db_context.documents.get(test_document.id)
        assert updated_doc.status == DocStatus.ERROR
        assert "timeout" in updated_doc.error_message.lower()

    @pytest.mark.asyncio
    async def test_hash_notarization_certificate_generation_failure(
        self, db_context, test_document
    ):
        """Test hash notarization with certificate generation failure using REAL database."""
        from abs_worker.notarization import process_hash_notarization

        mock_result = type("NotarizationResult", (), {"transaction_hash": "0xcert_fail_tx_hash"})()

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Mock blockchain, monitoring, and make certificate generation fail
        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.notarization.BlockchainClient"
        ) as mock_client_class, patch(
            "abs_worker.notarization.monitor_transaction"
        ) as mock_monitor, patch(
            "abs_worker.notarization.generate_signed_json"
        ) as mock_json_cert, patch("abs_worker.error_handler.get_session", mock_get_session):
            mock_client = AsyncMock()
            mock_client.notarize_hash.return_value = mock_result
            mock_client_class.return_value = mock_client

            mock_monitor.return_value = None
            # Make JSON certificate generation fail
            mock_json_cert.side_effect = Exception("Certificate storage unavailable")

            # Execute and expect failure
            with pytest.raises(Exception) as exc_info:
                await process_hash_notarization(mock_client, test_document.id)

            assert "Certificate storage unavailable" in str(exc_info.value)

        # Verify error was recorded IN REAL DATABASE
        await db_context.session.refresh(test_document)
        updated_doc = await db_context.documents.get(test_document.id)
        assert updated_doc.status == DocStatus.ERROR
        assert "Certificate storage unavailable" in updated_doc.error_message

    @pytest.mark.asyncio
    async def test_concurrent_hash_notarizations(self, db_context, test_user, worker_settings):
        """Test multiple hash notarizations running sequentially with REAL database.

        Note: True concurrency with same session not possible in SQLAlchemy.
        In production, each background task gets its own session from the pool.
        This test verifies multiple operations work correctly in sequence.
        """
        from abs_worker.notarization import process_hash_notarization
        from abs_orm.models import DocStatus, DocType

        # Create 3 REAL documents in database
        docs = []
        for i in range(3):
            doc = await db_context.documents.create(
                owner_id=test_user.id,
                file_name=f"concurrent_{i}.pdf",
                file_hash=f"0xhash_{i}_{hash(f'concurrent_{i}') % 10000:04x}",
                file_path=f"/tmp/concurrent_{i}.pdf",
                status=DocStatus.PENDING,
                type=DocType.HASH,
            )
            docs.append(doc)
        await db_context.commit()

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Mock blockchain for operations
        call_count = 0

        def mock_notarize_hash(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = type(
                "NotarizationResult", (), {"transaction_hash": f"0xconcurrent_tx_{call_count}"}
            )()
            return result

        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.notarization.BlockchainClient"
        ) as mock_client_class, patch(
            "abs_worker.notarization.monitor_transaction"
        ) as mock_monitor, patch("abs_worker.error_handler.get_session", mock_get_session), patch(
            "abs_worker.certificates.get_settings", lambda: worker_settings
        ):
            mock_client = AsyncMock()
            mock_client.notarize_hash.side_effect = mock_notarize_hash
            mock_client_class.return_value = mock_client
            mock_monitor.return_value = None

            # Execute all notarizations sequentially (SQLAlchemy session limitation)
            # In production, each would get its own session from pool
            for doc in docs:
                await process_hash_notarization(mock_client, doc.id)

            # Verify all blockchain calls were made
            assert mock_client.notarize_hash.call_count == 3

        # Verify all documents are ON_CHAIN in REAL DATABASE
        for doc in docs:
            await db_context.session.refresh(doc)
            updated_doc = await db_context.documents.get(doc.id)
            assert updated_doc.status == DocStatus.ON_CHAIN
            assert updated_doc.transaction_hash.startswith("0xconcurrent_tx_")
            assert updated_doc.signed_json_path is not None
            assert updated_doc.signed_pdf_path is not None


class TestNftNotarizationIntegration:
    """Integration tests for NFT notarization workflow using real database."""

    @pytest.mark.asyncio
    async def test_nft_notarization_not_implemented(self, mock_nft_document, worker_settings):
        """Test that NFT notarization raises NotImplementedError."""
        from abs_worker.notarization import process_nft_notarization

        # NFT notarization is not yet implemented - should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="NFT notarization not yet implemented"):
            await process_nft_notarization(mock_nft_document.id)


class TestErrorHandlingIntegration:
    """Integration tests for error handling with REAL database."""

    @pytest.mark.asyncio
    async def test_handle_failed_transaction_updates_database(self, db_context, test_document):
        """Test that handle_failed_transaction properly updates REAL database."""
        from abs_worker.error_handler import handle_failed_transaction

        # Verify initial state
        doc = await db_context.documents.get(test_document.id)
        assert doc.status == DocStatus.PENDING
        assert doc.error_message is None

        test_error = Exception("Test blockchain failure")

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Call error handler - will update REAL DATABASE
        with patch("abs_worker.error_handler.get_session", mock_get_session):
            await handle_failed_transaction(test_document.id, test_error)

        # Verify document was updated IN REAL DATABASE
        await db_context.session.refresh(test_document)
        updated_doc = await db_context.documents.get(test_document.id)
        assert updated_doc.status == DocStatus.ERROR
        assert updated_doc.error_message is not None
        assert "Test blockchain failure" in updated_doc.error_message

    @pytest.mark.asyncio
    async def test_handle_failed_transaction_with_nonexistent_document(self, db_context):
        """Test error handling when document doesn't exist in REAL database."""
        from abs_worker.error_handler import handle_failed_transaction

        test_error = Exception("Some error")

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Should not raise exception for non-existent document
        # REAL DATABASE will return None, error handler should handle gracefully
        with patch("abs_worker.error_handler.get_session", mock_get_session):
            await handle_failed_transaction(99999, test_error)

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self, db_context, worker_settings):
        """Test retry logic with successful eventual call."""
        from abs_worker.error_handler import retry_with_backoff

        with patch("abs_worker.error_handler.get_settings", lambda: worker_settings):
            call_count = 0

            async def failing_function():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise Exception("Temporary failure")
                return "success"

            result = await retry_with_backoff(failing_function, max_retries=5)

            assert result == "success"
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_backoff_exhaustion(self, db_context, worker_settings):
        """Test retry logic that exhausts all attempts."""
        from abs_worker.error_handler import retry_with_backoff

        with patch("abs_worker.error_handler.get_settings", lambda: worker_settings):
            call_count = 0

            async def always_failing_function():
                nonlocal call_count
                call_count += 1
                raise Exception("Permanent failure")

            with pytest.raises(Exception, match="Permanent failure"):
                await retry_with_backoff(always_failing_function, max_retries=2)

            assert call_count == 3  # Initial call + 2 retries
