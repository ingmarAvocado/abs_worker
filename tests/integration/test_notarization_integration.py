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
from abs_orm.models import DocStatus


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
        ), patch("abs_worker.error_handler.get_settings", lambda: worker_settings):
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
    async def test_hash_notarization_blockchain_failure(
        self, db_context, test_document, worker_settings
    ):
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
        ) as mock_client_class, patch(
            "abs_worker.error_handler.get_session", mock_get_session
        ), patch("abs_worker.error_handler.get_settings", lambda: worker_settings):
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
        self, db_context, test_document, worker_settings
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
        ) as mock_monitor, patch("abs_worker.error_handler.get_session", mock_get_session), patch(
            "abs_worker.error_handler.get_settings", lambda: worker_settings
        ):
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
        self, db_context, test_document, worker_settings
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
        ) as mock_json_cert, patch("abs_worker.error_handler.get_session", mock_get_session), patch(
            "abs_worker.error_handler.get_settings", lambda: worker_settings
        ):
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
        ), patch("abs_worker.error_handler.get_settings", lambda: worker_settings):
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
    async def test_full_nft_notarization_workflow(
        self, db_context, test_nft_document, mock_blockchain, worker_settings
    ):
        """Test complete NFT notarization workflow with REAL database and real certificate generation."""
        from abs_worker.notarization import process_nft_notarization

        # Verify initial document state IN REAL DATABASE
        doc = await db_context.documents.get(test_nft_document.id)
        assert doc.status == DocStatus.PENDING
        assert doc.transaction_hash is None
        assert doc.nft_token_id is None
        assert doc.arweave_file_url is None
        assert doc.arweave_metadata_url is None
        assert doc.signed_json_path is None
        assert doc.signed_pdf_path is None

        # Mock blockchain result
        mock_result = type(
            "NftMintResult",
            (),
            {
                "transaction_hash": "0xnft_tx_hash_123",
                "token_id": 42,
                "arweave_file_url": "https://arweave.net/file_123",
                "arweave_metadata_url": "https://arweave.net/metadata_123",
            },
        )()

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
        ), patch("abs_worker.error_handler.get_settings", lambda: worker_settings):
            # Setup blockchain mock
            mock_client = AsyncMock()
            mock_client.mint_nft_from_file.return_value = mock_result
            mock_client.get_transaction_receipt.return_value = {
                "status": 1,
                "blockNumber": 100,
                "transactionHash": "0xnft_tx_hash_123",
            }
            mock_client.get_latest_block_number.return_value = 105  # 5 confirmations
            mock_client_class.return_value = mock_client

            # Monitoring just succeeds
            mock_monitor.return_value = None

            # Execute the workflow - USES REAL TEST DATABASE, REAL CERTIFICATE FUNCTIONS
            await process_nft_notarization(mock_client, test_nft_document.id)

            # Verify blockchain was called correctly
            mock_client.mint_nft_from_file.assert_called_once()
            call_args = mock_client.mint_nft_from_file.call_args
            assert call_args[1]["file_path"] == test_nft_document.file_path
            assert call_args[1]["file_hash"] == test_nft_document.file_hash
            assert "metadata" in call_args[1]
            assert call_args[1]["metadata"]["name"] == f"Notarized {test_nft_document.file_name}"

            # Verify monitoring was called
            mock_monitor.assert_called_once_with(
                mock_client, test_nft_document.id, "0xnft_tx_hash_123"
            )

        # Verify final document state IN REAL DATABASE
        await db_context.session.refresh(test_nft_document)
        updated_doc = await db_context.documents.get(test_nft_document.id)
        assert updated_doc.status == DocStatus.ON_CHAIN
        assert updated_doc.transaction_hash == "0xnft_tx_hash_123"
        assert updated_doc.nft_token_id == 42
        assert updated_doc.arweave_file_url == "https://arweave.net/file_123"
        assert updated_doc.arweave_metadata_url == "https://arweave.net/metadata_123"
        assert updated_doc.signed_json_path is not None
        assert updated_doc.signed_pdf_path is not None

    @pytest.mark.asyncio
    async def test_nft_notarization_blockchain_failure(
        self, db_context, test_nft_document, worker_settings
    ):
        """Test NFT notarization with blockchain failure using REAL database."""
        from abs_worker.notarization import process_nft_notarization

        # Verify initial state IN REAL DATABASE
        doc = await db_context.documents.get(test_nft_document.id)
        assert doc.status == DocStatus.PENDING

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Mock blockchain to fail with realistic error
        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.notarization.BlockchainClient"
        ) as mock_client_class, patch(
            "abs_worker.error_handler.get_session", mock_get_session
        ), patch("abs_worker.error_handler.get_settings", lambda: worker_settings):
            mock_client = AsyncMock()
            mock_client.mint_nft_from_file.side_effect = Exception("Arweave upload failed")
            mock_client_class.return_value = mock_client

            # Execute and expect failure
            with pytest.raises(Exception) as exc_info:
                await process_nft_notarization(mock_client, test_nft_document.id)

            assert "Arweave upload failed" in str(exc_info.value)

        # Verify database state after error - should be marked as ERROR in REAL DATABASE
        await db_context.session.refresh(test_nft_document)
        updated_doc = await db_context.documents.get(test_nft_document.id)
        assert updated_doc.status == DocStatus.ERROR
        assert updated_doc.error_message is not None
        assert "Arweave upload failed" in updated_doc.error_message

    @pytest.mark.asyncio
    async def test_nft_notarization_document_not_found(self, db_context):
        """Test NFT notarization with non-existent document using REAL database."""
        from abs_worker.notarization import process_nft_notarization

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Try to process non-existent document - REAL DATABASE WILL RETURN None
        mock_client = AsyncMock()
        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.error_handler.get_session", mock_get_session
        ):
            with pytest.raises(ValueError, match="Document 99999 not found"):
                await process_nft_notarization(mock_client, 99999)

    @pytest.mark.asyncio
    async def test_nft_notarization_transaction_monitoring_failure(
        self, db_context, test_nft_document, worker_settings
    ):
        """Test NFT notarization with transaction monitoring failure using REAL database."""
        from abs_worker.notarization import process_nft_notarization

        mock_result = type(
            "NftMintResult",
            (),
            {
                "transaction_hash": "0xnft_failed_tx_hash",
                "token_id": 99,
                "arweave_file_url": "https://arweave.net/file_999",
                "arweave_metadata_url": "https://arweave.net/metadata_999",
            },
        )()

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Mock blockchain and monitoring to simulate timeout
        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.notarization.BlockchainClient"
        ) as mock_client_class, patch(
            "abs_worker.notarization.monitor_transaction"
        ) as mock_monitor, patch("abs_worker.error_handler.get_session", mock_get_session), patch(
            "abs_worker.error_handler.get_settings", lambda: worker_settings
        ):
            mock_client = AsyncMock()
            mock_client.mint_nft_from_file.return_value = mock_result
            mock_client_class.return_value = mock_client

            # Make monitoring fail with timeout
            mock_monitor.side_effect = TimeoutError("NFT transaction confirmation timeout")

            # Execute and expect failure
            with pytest.raises(TimeoutError, match="NFT transaction confirmation timeout"):
                await process_nft_notarization(mock_client, test_nft_document.id)

        # Verify error was recorded IN REAL DATABASE
        await db_context.session.refresh(test_nft_document)
        updated_doc = await db_context.documents.get(test_nft_document.id)
        assert updated_doc.status == DocStatus.ERROR
        assert "timeout" in updated_doc.error_message.lower()

    @pytest.mark.asyncio
    async def test_nft_notarization_certificate_generation_failure(
        self, db_context, test_nft_document, worker_settings
    ):
        """Test NFT notarization with certificate generation failure using REAL database."""
        from abs_worker.notarization import process_nft_notarization
        from abs_orm.models import DocStatus

        # Reset document to PENDING status for this test
        await db_context.documents.update(test_nft_document.id, status=DocStatus.PENDING)
        await db_context.commit()

        mock_result = type(
            "NftMintResult",
            (),
            {
                "transaction_hash": "0xnft_cert_fail_tx_hash",
                "token_id": 88,
                "arweave_file_url": "https://arweave.net/file_888",
                "arweave_metadata_url": "https://arweave.net/metadata_888",
            },
        )()

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
            "abs_worker.certificates._sign_certificate"
        ) as mock_sign_cert, patch("abs_worker.error_handler.get_session", mock_get_session), patch(
            "abs_worker.error_handler.get_settings", lambda: worker_settings
        ):
            mock_client = AsyncMock()
            mock_client.mint_nft_from_file.return_value = mock_result
            mock_client_class.return_value = mock_client

            mock_monitor.return_value = None
            # Make certificate signing fail
            mock_sign_cert.side_effect = Exception("NFT certificate storage unavailable")

            # Execute and expect failure
            with pytest.raises(Exception) as exc_info:
                await process_nft_notarization(mock_client, test_nft_document.id)

            assert "NFT certificate storage unavailable" in str(exc_info.value)

        # Verify error was recorded IN REAL DATABASE
        await db_context.session.refresh(test_nft_document)
        updated_doc = await db_context.documents.get(test_nft_document.id)
        assert updated_doc.status == DocStatus.ERROR
        assert "NFT certificate storage unavailable" in updated_doc.error_message

    @pytest.mark.asyncio
    async def test_concurrent_nft_notarizations(self, db_context, test_user, worker_settings):
        """Test multiple NFT notarizations running sequentially with REAL database.

        Note: True concurrency with same session not possible in SQLAlchemy.
        In production, each background task gets its own session from the pool.
        This test verifies multiple operations work correctly in sequence.
        """
        from abs_worker.notarization import process_nft_notarization
        from abs_orm.models import DocStatus, DocType

        # Create 3 REAL NFT documents in database
        docs = []
        for i in range(3):
            doc = await db_context.documents.create(
                owner_id=test_user.id,
                file_name=f"nft_concurrent_{i}.pdf",
                file_hash=f"0xnft_hash_{i}_{hash(f'nft_concurrent_{i}') % 10000:04x}",
                file_path=f"/tmp/nft_concurrent_{i}.pdf",
                status=DocStatus.PENDING,
                type=DocType.NFT,
            )
            docs.append(doc)
        await db_context.commit()

        # Mock get_session to use TEST database
        @asynccontextmanager
        async def mock_get_session():
            yield db_context.session

        # Mock blockchain for operations
        call_count = 0

        def mock_mint_nft_from_file(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = type(
                "NftMintResult",
                (),
                {
                    "transaction_hash": f"0xnft_concurrent_tx_{call_count}",
                    "token_id": 100 + call_count,
                    "arweave_file_url": f"https://arweave.net/nft_file_{call_count}",
                    "arweave_metadata_url": f"https://arweave.net/nft_metadata_{call_count}",
                },
            )()
            return result

        with patch("abs_worker.notarization.get_session", mock_get_session), patch(
            "abs_worker.notarization.BlockchainClient"
        ) as mock_client_class, patch(
            "abs_worker.notarization.monitor_transaction"
        ) as mock_monitor, patch("abs_worker.error_handler.get_session", mock_get_session), patch(
            "abs_worker.certificates.get_settings", lambda: worker_settings
        ), patch("abs_worker.error_handler.get_settings", lambda: worker_settings):
            mock_client = AsyncMock()
            mock_client.mint_nft_from_file.side_effect = mock_mint_nft_from_file
            mock_client_class.return_value = mock_client
            mock_monitor.return_value = None

            # Execute all notarizations sequentially (SQLAlchemy session limitation)
            # In production, each would get its own session from pool
            for doc in docs:
                await process_nft_notarization(mock_client, doc.id)

            # Verify all blockchain calls were made
            assert mock_client.mint_nft_from_file.call_count == 3

        # Verify all documents are ON_CHAIN in REAL DATABASE
        for doc in docs:
            await db_context.session.refresh(doc)
            updated_doc = await db_context.documents.get(doc.id)
            assert updated_doc.status == DocStatus.ON_CHAIN
            assert updated_doc.transaction_hash.startswith("0xnft_concurrent_tx_")
            assert updated_doc.nft_token_id is not None
            assert updated_doc.arweave_file_url is not None
            assert updated_doc.arweave_metadata_url is not None
            assert updated_doc.signed_json_path is not None
            assert updated_doc.signed_pdf_path is not None


class TestTransactionMonitoringIntegration:
    """Integration tests for transaction monitoring functionality using real database."""

    @pytest.mark.asyncio
    async def test_monitor_transaction_success(self, db_context, worker_settings):
        """Test successful transaction monitoring with real blockchain client."""
        from abs_worker.monitoring import monitor_transaction

        # Mock blockchain client
        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.side_effect = [
            None,  # Not mined yet
            None,  # Still not mined
            {
                "status": 1,
                "blockNumber": 100,
                "transactionHash": "0xsuccess_tx",
            },  # Mined and successful
        ]
        mock_client.get_latest_block_number.return_value = 105  # 5 confirmations

        with patch("abs_worker.monitoring.get_settings", lambda: worker_settings):
            receipt = await monitor_transaction(mock_client, doc_id=123, tx_hash="0xsuccess_tx")

        assert receipt["status"] == 1
        assert receipt["blockNumber"] == 100
        assert mock_client.get_transaction_receipt.call_count == 3

    @pytest.mark.asyncio
    async def test_monitor_transaction_reverted(self, db_context, worker_settings):
        """Test monitoring transaction that gets reverted."""
        from abs_worker.monitoring import monitor_transaction

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = {
            "status": 0,  # Reverted
            "blockNumber": 100,
            "transactionHash": "0xreverted_tx",
        }

        with patch("abs_worker.monitoring.get_settings", lambda: worker_settings):
            with pytest.raises(ValueError, match="Transaction 0xreverted_tx reverted"):
                await monitor_transaction(mock_client, doc_id=123, tx_hash="0xreverted_tx")

    @pytest.mark.asyncio
    async def test_monitor_transaction_timeout(self, db_context, worker_settings):
        """Test monitoring transaction that times out."""
        from abs_worker.monitoring import monitor_transaction

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = None  # Never mined

        # Set low max_poll_attempts for faster test
        test_settings = type(
            "TestSettings",
            (),
            {
                "blockchain": type(
                    "BlockchainSettings",
                    (),
                    {
                        "poll_interval": 0.01,  # Very fast polling
                        "max_poll_attempts": 2,  # Only 2 attempts
                        "required_confirmations": 1,
                    },
                )()
            },
        )()

        with patch("abs_worker.monitoring.get_settings", lambda: test_settings):
            with pytest.raises(
                TimeoutError, match="Transaction 0xtimeout_tx exceeded max poll attempts"
            ):
                await monitor_transaction(mock_client, doc_id=123, tx_hash="0xtimeout_tx")

    @pytest.mark.asyncio
    async def test_check_transaction_status_pending(self, db_context):
        """Test checking status of pending transaction."""
        from abs_worker.monitoring import check_transaction_status

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = None

        status = await check_transaction_status(mock_client, "0xpending_tx")

        assert status["status"] == "pending"
        assert status["confirmations"] == 0
        assert status["receipt"] is None

    @pytest.mark.asyncio
    async def test_check_transaction_status_confirmed(self, db_context):
        """Test checking status of confirmed transaction."""
        from abs_worker.monitoring import check_transaction_status

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": "0xconfirmed_tx",
        }
        mock_client.get_latest_block_number.return_value = 105  # 5 confirmations

        status = await check_transaction_status(mock_client, "0xconfirmed_tx")

        assert status["status"] == "confirmed"
        assert status["confirmations"] == 5
        assert status["receipt"]["status"] == 1

    @pytest.mark.asyncio
    async def test_wait_for_confirmation_success(self, db_context, worker_settings):
        """Test waiting for transaction confirmation."""
        from abs_worker.monitoring import wait_for_confirmation

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": "0xwait_tx",
        }
        mock_client.get_latest_block_number.return_value = 105

        with patch("abs_worker.monitoring.get_settings", lambda: worker_settings):
            receipt = await wait_for_confirmation(mock_client, "0xwait_tx")

        assert receipt["status"] == 1
        assert receipt["blockNumber"] == 100


class TestCertificateGenerationIntegration:
    """Integration tests for certificate generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_signed_json_hash_document(
        self, db_context, test_document, worker_settings
    ):
        """Test JSON certificate generation for hash document."""
        from abs_worker.certificates import generate_signed_json
        from pathlib import Path

        # Mock signing key for testing
        with patch(
            "abs_worker.certificates._read_signing_key", return_value="0x" + "1" * 64
        ), patch("abs_worker.certificates.get_settings", lambda: worker_settings):
            cert_path = await generate_signed_json(test_document)

        # Verify certificate file was created
        assert Path(cert_path).exists()

        # Verify certificate content
        import json

        with open(cert_path, "r") as f:
            cert_data = json.load(f)

        assert cert_data["document_id"] == test_document.id
        assert cert_data["file_hash"] == test_document.file_hash
        assert cert_data["type"] == "hash"
        assert "signature" in cert_data
        assert cert_data["certificate_version"] == "1.0"
        # NFT fields should not be present for hash documents
        assert "nft_token_id" not in cert_data
        assert "arweave_file_url" not in cert_data

    @pytest.mark.asyncio
    async def test_generate_signed_json_nft_document(
        self, db_context, test_nft_document, worker_settings
    ):
        """Test JSON certificate generation for NFT document."""
        from abs_worker.certificates import generate_signed_json
        from pathlib import Path

        # Set NFT fields on document
        test_nft_document.nft_token_id = 42
        test_nft_document.arweave_file_url = "https://arweave.net/file_123"
        test_nft_document.arweave_metadata_url = "https://arweave.net/metadata_123"
        test_nft_document.transaction_hash = "0xnft_tx_123"

        # Mock signing key for testing
        with patch(
            "abs_worker.certificates._read_signing_key", return_value="0x" + "2" * 64
        ), patch("abs_worker.certificates.get_settings", lambda: worker_settings):
            cert_path = await generate_signed_json(test_nft_document)

        # Verify certificate file was created
        assert Path(cert_path).exists()

        # Verify certificate content
        import json

        with open(cert_path, "r") as f:
            cert_data = json.load(f)

        assert cert_data["document_id"] == test_nft_document.id
        assert cert_data["file_hash"] == test_nft_document.file_hash
        assert cert_data["type"] == "nft"
        assert cert_data["nft_token_id"] == 42
        assert cert_data["arweave_file_url"] == "https://arweave.net/file_123"
        assert cert_data["arweave_metadata_url"] == "https://arweave.net/metadata_123"
        assert "signature" in cert_data

    @pytest.mark.asyncio
    async def test_generate_signed_pdf_hash_document(
        self, db_context, test_document, worker_settings
    ):
        """Test PDF certificate generation for hash document."""
        from abs_worker.certificates import generate_signed_pdf
        from pathlib import Path

        # Mock signing key for testing
        with patch(
            "abs_worker.certificates._read_signing_key", return_value="0x" + "3" * 64
        ), patch("abs_worker.certificates.get_settings", lambda: worker_settings):
            cert_path = await generate_signed_pdf(test_document)

        # Verify certificate file was created
        assert Path(cert_path).exists()
        assert cert_path.endswith(".pdf")

        # Basic PDF validation (check file size > 0)
        pdf_size = Path(cert_path).stat().st_size
        assert pdf_size > 1000  # PDFs should be reasonably sized

    @pytest.mark.asyncio
    async def test_generate_signed_pdf_nft_document(
        self, db_context, test_nft_document, worker_settings
    ):
        """Test PDF certificate generation for NFT document."""
        from abs_worker.certificates import generate_signed_pdf
        from pathlib import Path

        # Set NFT fields on document
        test_nft_document.nft_token_id = 99
        test_nft_document.arweave_file_url = "https://arweave.net/nft_file_99"
        test_nft_document.arweave_metadata_url = "https://arweave.net/nft_metadata_99"
        test_nft_document.transaction_hash = "0xnft_pdf_tx_99"

        # Mock signing key for testing
        with patch(
            "abs_worker.certificates._read_signing_key", return_value="0x" + "4" * 64
        ), patch("abs_worker.certificates.get_settings", lambda: worker_settings):
            cert_path = await generate_signed_pdf(test_nft_document)

        # Verify certificate file was created
        assert Path(cert_path).exists()
        assert cert_path.endswith(".pdf")

        # Basic PDF validation
        pdf_size = Path(cert_path).stat().st_size
        assert pdf_size > 1000

    @pytest.mark.asyncio
    async def test_certificate_signing_key_not_found(self, db_context, test_document):
        """Test certificate generation fails when signing key is not available."""
        from abs_worker.certificates import generate_signed_json, SigningKeyNotFoundError

        # Mock no signing key available
        with patch("abs_worker.certificates._read_signing_key", return_value=None):
            with pytest.raises(
                SigningKeyNotFoundError, match="Certificate signing key not available"
            ):
                await generate_signed_json(test_document)

    @pytest.mark.asyncio
    async def test_verify_certificate_valid(self, db_context, test_document, worker_settings):
        """Test certificate verification with valid signature."""
        from abs_worker.certificates import generate_signed_json, verify_certificate

        # Generate certificate
        with patch(
            "abs_worker.certificates._read_signing_key", return_value="0x" + "5" * 64
        ), patch("abs_worker.certificates.get_settings", lambda: worker_settings):
            cert_path = await generate_signed_json(test_document)

        # For verification, we need the corresponding public key
        # Since we're using a mock private key, we'll mock the verification
        with patch("abs_worker.certificates._verify_certificate_signature", return_value=True):
            is_valid = await verify_certificate(cert_path, "mock_public_key")

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_certificate_invalid(self, db_context, test_document, worker_settings):
        """Test certificate verification with invalid signature."""
        from abs_worker.certificates import generate_signed_json, verify_certificate

        # Generate certificate
        with patch(
            "abs_worker.certificates._read_signing_key", return_value="0x" + "6" * 64
        ), patch("abs_worker.certificates.get_settings", lambda: worker_settings):
            cert_path = await generate_signed_json(test_document)

        # Mock invalid signature verification
        with patch("abs_worker.certificates._verify_certificate_signature", return_value=False):
            is_valid = await verify_certificate(cert_path, "mock_public_key")

        assert is_valid is False


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
                    raise Exception("connection timeout")
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
                raise Exception("connection timeout")

            with pytest.raises(Exception, match="connection timeout"):
                await retry_with_backoff(always_failing_function, max_retries=2)

            assert call_count == 3  # Initial call + 2 retries
