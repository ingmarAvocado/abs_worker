"""
Tests for error handler module
"""

import asyncio
import pytest
from contextlib import asynccontextmanager
from abs_worker.error_handler import (
    is_retryable_error,
    handle_failed_transaction,
    retry_with_backoff,
)


class TestIsRetryableError:
    """Tests for is_retryable_error function"""

    def test_timeout_error_is_retryable(self):
        """Test that timeout errors are retryable"""
        error = Exception("Connection timeout occurred")
        assert is_retryable_error(error) is True

    def test_connection_error_is_retryable(self):
        """Test that connection errors are retryable"""
        error = Exception("Connection refused")
        assert is_retryable_error(error) is True

    def test_network_error_is_retryable(self):
        """Test that network errors are retryable"""
        error = Exception("Network unreachable")
        assert is_retryable_error(error) is True

    def test_gas_estimation_error_is_retryable(self):
        """Test that gas estimation errors are retryable"""
        error = Exception("Gas estimation failed")
        assert is_retryable_error(error) is True

    def test_nonce_error_is_retryable(self):
        """Test that nonce errors are retryable"""
        error = Exception("Nonce too low")
        assert is_retryable_error(error) is True

    def test_reverted_error_not_retryable(self):
        """Test that reverted transactions are not retryable"""
        error = Exception("Transaction reverted")
        assert is_retryable_error(error) is False

    def test_insufficient_funds_not_retryable(self):
        """Test that insufficient funds errors are not retryable"""
        error = Exception("Insufficient funds")
        assert is_retryable_error(error) is False

    def test_invalid_signature_not_retryable(self):
        """Test that invalid signature errors are not retryable"""
        error = Exception("Invalid signature")
        assert is_retryable_error(error) is False

    def test_already_exists_not_retryable(self):
        """Test that duplicate errors are not retryable"""
        error = Exception("Hash already exists")
        assert is_retryable_error(error) is False

    def test_unauthorized_not_retryable(self):
        """Test that authorization errors are not retryable"""
        error = Exception("Unauthorized access")
        assert is_retryable_error(error) is False

    def test_unknown_error_is_retryable(self):
        """Test that unknown errors default to retryable"""
        error = Exception("Some random error message")
        assert is_retryable_error(error) is True


class TestHandleFailedTransaction:
    """Tests for handle_failed_transaction function"""

    @pytest.mark.asyncio
    async def test_handle_failed_transaction_stub(self, monkeypatch):
        """Test handle_failed_transaction with mocked dependencies"""
        from tests.mocks.mock_orm import MockDocumentRepository, MockAsyncSession
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        session = MockAsyncSession()
        logger = MockLogger("test")

        # Mock the dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        monkeypatch.setattr("abs_worker.error_handler.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.error_handler.DocumentRepository", lambda s: repo)
        monkeypatch.setattr("abs_worker.error_handler.logger", logger)

        doc_id = 123
        error = Exception("Test error")

        # Should not raise exception
        await handle_failed_transaction(doc_id, error)

    @pytest.mark.asyncio
    async def test_handle_retryable_error(self, mock_document, monkeypatch):
        """Test handling of retryable errors"""
        from tests.mocks.mock_orm import MockDocumentRepository, MockAsyncSession
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_document.id] = mock_document
        session = MockAsyncSession()
        logger = MockLogger("test")

        # Mock the dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        monkeypatch.setattr("abs_worker.error_handler.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.error_handler.DocumentRepository", lambda s: repo)
        monkeypatch.setattr("abs_worker.error_handler.logger", logger)

        error = Exception("Connection timeout")
        await handle_failed_transaction(mock_document.id, error)

        # Check that document was updated
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "error"  # Compare enum values, not classes
        assert updated_doc.error_message == str(error)
        assert session.committed is True

    @pytest.mark.asyncio
    async def test_handle_non_retryable_error(self, mock_document, monkeypatch):
        """Test handling of non-retryable errors"""
        from tests.mocks.mock_orm import MockDocumentRepository, MockAsyncSession
        from tests.mocks.mock_utils import MockLogger

        # Create mocks
        repo = MockDocumentRepository()
        repo.documents[mock_document.id] = mock_document
        session = MockAsyncSession()
        logger = MockLogger("test")

        # Mock the dependencies
        @asynccontextmanager
        async def mock_get_session():
            try:
                yield session
            finally:
                await session.close()

        monkeypatch.setattr("abs_worker.error_handler.get_session", mock_get_session)
        monkeypatch.setattr("abs_worker.error_handler.DocumentRepository", lambda s: repo)
        monkeypatch.setattr("abs_worker.error_handler.logger", logger)

        error = Exception("Transaction reverted")
        await handle_failed_transaction(mock_document.id, error)

        # Check that document was updated
        updated_doc = repo.documents[mock_document.id]
        assert updated_doc.status.value == "error"  # Compare enum values, not classes
        assert updated_doc.error_message == str(error)
        assert session.committed is True


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function"""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test that successful calls don't retry"""
        call_count = 0

        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(successful_func, max_retries=3)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retryable_error_retries(self):
        """Test that retryable errors trigger retries"""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Connection timeout")
            return "success"

        result = await retry_with_backoff(failing_func, max_retries=3)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error_no_retry(self):
        """Test that non-retryable errors don't retry"""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Transaction reverted")

        with pytest.raises(Exception, match="Transaction reverted"):
            await retry_with_backoff(failing_func, max_retries=3)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that backoff delays increase exponentially"""
        delays = []

        async def failing_func():
            raise Exception("Connection timeout")

        # Mock asyncio.sleep to capture delays
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.001)  # Very short sleep for testing

        asyncio.sleep = mock_sleep

        try:
            with pytest.raises(Exception):
                await retry_with_backoff(
                    failing_func, max_retries=2, initial_delay=1, backoff_multiplier=2
                )
        finally:
            asyncio.sleep = original_sleep

        # Should have delays: 1, 2 (1*2^1)
        assert len(delays) == 2
        assert delays[0] == 1
        assert delays[1] == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries limit is respected"""
        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Connection timeout")

        with pytest.raises(Exception, match="Connection timeout"):
            await retry_with_backoff(failing_func, max_retries=2)

        assert call_count == 3  # initial + 2 retries
