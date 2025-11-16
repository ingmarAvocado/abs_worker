"""
Tests for transaction monitoring module
"""

import pytest
import asyncio
from contextlib import asynccontextmanager
from abs_worker.monitoring import (
    monitor_transaction,
    check_transaction_status,
    wait_for_confirmation,
)


class TestMonitorTransaction:
    """Tests for monitor_transaction function"""

    @pytest.mark.asyncio
    async def test_confirmed_transaction(self, monkeypatch, worker_settings):
        """Test monitoring of confirmed transaction"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mock blockchain with confirmed transaction
        blockchain = MockBlockchain()
        tx_hash = "0xconfirmed123"
        blockchain.transactions[tx_hash] = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 105  # 5 confirmations

        # Mock BlockchainClient
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = blockchain.transactions.get(tx_hash)
        mock_client.get_latest_block_number.return_value = blockchain.current_block

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)

        # Should return receipt after confirmations met
        receipt = await monitor_transaction(mock_client, 123, tx_hash)

        assert receipt is not None
        assert receipt["status"] == 1
        assert receipt["transactionHash"] == tx_hash
        assert receipt["blockNumber"] == 100

    @pytest.mark.asyncio
    async def test_reverted_transaction_raises(self, monkeypatch, worker_settings):
        """Test that reverted transactions raise ValueError"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mock blockchain with reverted transaction
        blockchain = MockBlockchain()
        tx_hash = "0xreverted123"
        blockchain.transactions[tx_hash] = {
            "status": 0,  # Reverted
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 105

        # Mock BlockchainClient
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = blockchain.transactions.get(tx_hash)
        mock_client.get_latest_block_number.return_value = blockchain.current_block

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)

        # Should raise ValueError for reverted transaction
        with pytest.raises(ValueError, match="reverted"):
            await monitor_transaction(mock_client, 123, tx_hash)

    @pytest.mark.asyncio
    async def test_timeout_raises(self, monkeypatch, worker_settings, tmp_path):
        """Test that timeout is raised after max_confirmation_wait"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import (
            Settings,
            BlockchainSettings,
            RetrySettings,
            WorkerSettings,
            CertificateSettings,
        )

        # Create mock blockchain with pending transaction
        blockchain = MockBlockchain()
        tx_hash = "0xpending123"

        # Mock BlockchainClient that always returns None (pending)
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = None  # Never mined
        mock_client.get_latest_block_number.return_value = 100

        # Create temporary signing key for tests
        signing_key = tmp_path / "test_signing_key.pem"
        signing_key.write_text("0x" + "1" * 64)
        signing_key.chmod(0o600)

        # Mock settings with very short timeout
        settings = Settings(
            blockchain=BlockchainSettings(
                max_confirmation_wait=2,  # 2 second timeout
                poll_interval=1,  # Poll every 1 second
                max_poll_attempts=3,  # Only 3 attempts max
            ),
            retry=RetrySettings(),
            worker=WorkerSettings(),
            certificate=CertificateSettings(
                storage_path=str(tmp_path / "certs"), signing_key_path=str(signing_key)
            ),
        )

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should raise TimeoutError (will hit max_poll_attempts before time-based timeout)
        with pytest.raises(TimeoutError, match="exceeded max poll attempts"):
            await monitor_transaction(mock_client, 123, tx_hash)

    @pytest.mark.asyncio
    async def test_required_confirmations_waited(self, monkeypatch, worker_settings, tmp_path):
        """Test that function waits for required confirmations"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import (
            Settings,
            BlockchainSettings,
            RetrySettings,
            WorkerSettings,
            CertificateSettings,
        )

        # Create mock blockchain with transaction that gains confirmations
        blockchain = MockBlockchain()
        tx_hash = "0xwaiting123"
        blockchain.transactions[tx_hash] = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 101  # Initially only 1 confirmation

        poll_count = 0

        # Mock BlockchainClient that simulates confirmations increasing
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()  # type: ignore
        mock_client.get_transaction_receipt.return_value = blockchain.transactions.get(tx_hash)

        def get_latest_block():
            nonlocal poll_count
            poll_count += 1
            # Simulate blocks being mined
            if poll_count >= 3:
                blockchain.current_block = 103  # Now has 3 confirmations
            return blockchain.current_block

        mock_client.get_latest_block_number.side_effect = get_latest_block

        # Create temporary signing key for tests
        signing_key = tmp_path / "test_signing_key.pem"
        signing_key.write_text("0x" + "1" * 64)
        signing_key.chmod(0o600)

        settings = Settings(
            blockchain=BlockchainSettings(
                required_confirmations=3,
                poll_interval=1,  # Poll every 1 second
                max_poll_attempts=10,  # Limit attempts for faster tests
                max_confirmation_wait=60,
            ),
            retry=RetrySettings(),
            worker=WorkerSettings(),
            certificate=CertificateSettings(
                storage_path=str(tmp_path / "certs"), signing_key_path=str(signing_key)
            ),
        )

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should wait and then return receipt
        receipt = await monitor_transaction(mock_client, 123, tx_hash)  # type: ignore

        assert receipt is not None
        assert poll_count >= 3  # Polled multiple times
        assert receipt["status"] == 1

    @pytest.mark.asyncio
    async def test_max_poll_attempts_exceeded(self, monkeypatch, worker_settings, tmp_path):
        """Test that max_poll_attempts is respected"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import (
            Settings,
            BlockchainSettings,
            RetrySettings,
            WorkerSettings,
            CertificateSettings,
        )
        from unittest.mock import AsyncMock

        # Create mock blockchain with transaction that never confirms
        blockchain = MockBlockchain()
        tx_hash = "0xnever123"
        blockchain.transactions[tx_hash] = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 100  # Never increases

        # Mock BlockchainClient
        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = blockchain.transactions.get(tx_hash)
        mock_client.get_latest_block_number.return_value = blockchain.current_block  # No new blocks

        # Create temporary signing key for tests
        signing_key = tmp_path / "test_signing_key.pem"
        signing_key.write_text("0x" + "1" * 64)
        signing_key.chmod(0o600)

        settings = Settings(
            blockchain=BlockchainSettings(
                required_confirmations=3,
                poll_interval=1,  # Poll every 1 second
                max_poll_attempts=3,  # Very low limit for fast test
                max_confirmation_wait=10,  # High timeout (won't be hit)
            ),
            retry=RetrySettings(),
            worker=WorkerSettings(),
            certificate=CertificateSettings(
                storage_path=str(tmp_path / "certs"), signing_key_path=str(signing_key)
            ),
        )

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should raise TimeoutError after max attempts
        with pytest.raises(TimeoutError, match="exceeded max poll attempts"):
            await monitor_transaction(mock_client, 123, tx_hash)


class TestCheckTransactionStatus:
    """Tests for check_transaction_status function"""

    @pytest.mark.asyncio
    async def test_pending_transaction_status(self, monkeypatch, worker_settings):
        """Test status of pending transaction"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mock blockchain with no transaction (pending)
        blockchain = MockBlockchain()
        tx_hash = "0xpending456"

        # Mock BlockchainClient
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = None  # Pending transaction
        mock_client.get_latest_block_number.return_value = 100

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)

        status = await check_transaction_status(mock_client, tx_hash)

        assert status["status"] == "pending"
        assert status["confirmations"] == 0
        assert status["receipt"] is None

    @pytest.mark.asyncio
    async def test_confirmed_transaction_status(self, monkeypatch, worker_settings):
        """Test status of confirmed transaction"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mock blockchain with confirmed transaction
        blockchain = MockBlockchain()
        tx_hash = "0xconfirmed456"
        blockchain.transactions[tx_hash] = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 105  # 5 confirmations

        # Mock BlockchainClient
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = blockchain.transactions.get(tx_hash)
        mock_client.get_latest_block_number.return_value = blockchain.current_block

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)

        status = await check_transaction_status(mock_client, tx_hash)

        assert status["status"] == "confirmed"
        assert status["confirmations"] == 5
        assert status["receipt"] is not None
        assert status["receipt"]["status"] == 1

    @pytest.mark.asyncio
    async def test_reverted_transaction_status(self, monkeypatch, worker_settings):
        """Test status of reverted transaction"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mock blockchain with reverted transaction
        blockchain = MockBlockchain()
        tx_hash = "0xreverted456"
        blockchain.transactions[tx_hash] = {
            "status": 0,  # Reverted
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 105

        # Mock BlockchainClient
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = blockchain.transactions.get(tx_hash)
        mock_client.get_latest_block_number.return_value = blockchain.current_block

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: worker_settings)

        status = await check_transaction_status(mock_client, tx_hash)

        assert status["status"] == "reverted"
        assert status["confirmations"] == 0
        assert status["receipt"] is not None
        assert status["receipt"]["status"] == 0


class TestWaitForConfirmation:
    """Tests for wait_for_confirmation function"""

    @pytest.mark.asyncio
    async def test_required_confirmations_waited(self, monkeypatch, worker_settings, tmp_path):
        """Test that function waits for required confirmations"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import (
            Settings,
            BlockchainSettings,
            RetrySettings,
            WorkerSettings,
            CertificateSettings,
        )
        from unittest.mock import AsyncMock

        # Create mock blockchain with transaction that gains confirmations
        blockchain = MockBlockchain()
        tx_hash = "0xwaiting123"
        blockchain.transactions[tx_hash] = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 101  # Initially only 1 confirmation

        poll_count = 0

        # Mock BlockchainClient that simulates confirmations increasing
        mock_client = AsyncMock()  # type: ignore
        mock_client.get_transaction_receipt.return_value = blockchain.transactions.get(tx_hash)

        def get_latest_block():
            nonlocal poll_count
            poll_count += 1
            # Simulate blocks being mined
            if poll_count >= 3:
                blockchain.current_block = 103  # Now has 3 confirmations
            return blockchain.current_block

        mock_client.get_latest_block_number.side_effect = get_latest_block

        # Create temporary signing key for tests
        signing_key = tmp_path / "test_signing_key.pem"
        signing_key.write_text("0x" + "1" * 64)
        signing_key.chmod(0o600)

        settings = Settings(
            blockchain=BlockchainSettings(
                required_confirmations=3,
                poll_interval=1,  # Poll every 1 second
                max_poll_attempts=10,  # Limit attempts for faster tests
                max_confirmation_wait=60,
            ),
            retry=RetrySettings(),
            worker=WorkerSettings(),
            certificate=CertificateSettings(
                storage_path=str(tmp_path / "certs"), signing_key_path=str(signing_key)
            ),
        )

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should wait and then return receipt
        receipt = await monitor_transaction(mock_client, 123, tx_hash)

        assert receipt is not None
        assert poll_count >= 3  # Polled multiple times
        assert receipt["status"] == 1

    @pytest.mark.asyncio
    async def test_custom_confirmations(self, monkeypatch, worker_settings, tmp_path):
        """Test waiting for custom confirmation count"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import (
            Settings,
            BlockchainSettings,
            RetrySettings,
            WorkerSettings,
            CertificateSettings,
        )

        # Create mock blockchain with confirmed transaction
        blockchain = MockBlockchain()
        tx_hash = "0xcustom789"
        blockchain.transactions[tx_hash] = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 105  # 5 confirmations

        # Mock BlockchainClient
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_transaction_receipt.return_value = blockchain.transactions.get(tx_hash)
        mock_client.get_latest_block_number.return_value = blockchain.current_block

        # Create temporary signing key for tests
        signing_key = tmp_path / "test_signing_key.pem"
        signing_key.write_text("0x" + "1" * 64)
        signing_key.chmod(0o600)

        settings = Settings(
            blockchain=BlockchainSettings(required_confirmations=3),
            retry=RetrySettings(),
            worker=WorkerSettings(),
            certificate=CertificateSettings(
                storage_path=str(tmp_path / "certs"), signing_key_path=str(signing_key)
            ),
        )

        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should use custom confirmation count (parameter overrides config)
        receipt = await wait_for_confirmation(mock_client, tx_hash, required_confirmations=2)

        assert receipt is not None
        assert receipt["status"] == 1
