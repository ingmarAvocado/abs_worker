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
    async def test_confirmed_transaction(self, monkeypatch):
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
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return blockchain.transactions.get(tx_hash)

            async def get_latest_block_number(self):
                return blockchain.current_block

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))

        # Should return receipt after confirmations met
        receipt = await monitor_transaction(123, tx_hash)

        assert receipt is not None
        assert receipt["status"] == 1
        assert receipt["transactionHash"] == tx_hash
        assert receipt["blockNumber"] == 100

    @pytest.mark.asyncio
    async def test_reverted_transaction_raises(self, monkeypatch):
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
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return blockchain.transactions.get(tx_hash)

            async def get_latest_block_number(self):
                return blockchain.current_block

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))

        # Should raise ValueError for reverted transaction
        with pytest.raises(ValueError, match="reverted"):
            await monitor_transaction(123, tx_hash)

    @pytest.mark.asyncio
    async def test_timeout_raises(self, monkeypatch):
        """Test that timeout is raised after max_confirmation_wait"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import Settings

        # Create mock blockchain with pending transaction
        blockchain = MockBlockchain()
        tx_hash = "0xpending123"

        # Mock BlockchainClient that always returns None (pending)
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return None  # Never mined

            async def get_latest_block_number(self):
                return 100

        # Mock settings with very short timeout
        settings = Settings(
            max_confirmation_wait=1,  # 1 second timeout
            poll_interval=0.1,  # Poll every 0.1 seconds
            max_poll_attempts=100,
        )

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should raise TimeoutError
        with pytest.raises(TimeoutError, match="timeout"):
            await monitor_transaction(123, tx_hash)

    @pytest.mark.asyncio
    async def test_required_confirmations_waited(self, monkeypatch):
        """Test that function waits for required confirmations"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import Settings

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
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return blockchain.transactions.get(tx_hash)

            async def get_latest_block_number(self):
                nonlocal poll_count
                poll_count += 1
                # Simulate blocks being mined
                if poll_count >= 3:
                    blockchain.current_block = 103  # Now has 3 confirmations
                return blockchain.current_block

        settings = Settings(
            required_confirmations=3,
            poll_interval=0.01,  # Fast polling for test
            max_poll_attempts=100,
        )

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should wait and then return receipt
        receipt = await monitor_transaction(123, tx_hash)

        assert receipt is not None
        assert poll_count >= 3  # Polled multiple times
        assert receipt["status"] == 1

    @pytest.mark.asyncio
    async def test_max_poll_attempts_exceeded(self, monkeypatch):
        """Test that max_poll_attempts is respected"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import Settings

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
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return blockchain.transactions.get(tx_hash)

            async def get_latest_block_number(self):
                return blockchain.current_block  # No new blocks

        settings = Settings(
            required_confirmations=3,
            poll_interval=0.001,  # Very fast
            max_poll_attempts=5,  # Very low limit
            max_confirmation_wait=10,  # High timeout (won't be hit)
        )

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should raise TimeoutError after max attempts
        with pytest.raises(TimeoutError, match="exceeded max poll attempts"):
            await monitor_transaction(123, tx_hash)


class TestCheckTransactionStatus:
    """Tests for check_transaction_status function"""

    @pytest.mark.asyncio
    async def test_pending_transaction_status(self, monkeypatch):
        """Test status of pending transaction"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger

        # Create mock blockchain with no transaction (pending)
        blockchain = MockBlockchain()
        tx_hash = "0xpending456"

        # Mock BlockchainClient
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return None  # Pending transaction

            async def get_latest_block_number(self):
                return 100

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))

        status = await check_transaction_status(tx_hash)

        assert status["status"] == "pending"
        assert status["confirmations"] == 0
        assert status["receipt"] is None

    @pytest.mark.asyncio
    async def test_confirmed_transaction_status(self, monkeypatch):
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
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return blockchain.transactions.get(tx_hash)

            async def get_latest_block_number(self):
                return blockchain.current_block

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))

        status = await check_transaction_status(tx_hash)

        assert status["status"] == "confirmed"
        assert status["confirmations"] == 5
        assert status["receipt"] is not None
        assert status["receipt"]["status"] == 1

    @pytest.mark.asyncio
    async def test_reverted_transaction_status(self, monkeypatch):
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
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return blockchain.transactions.get(tx_hash)

            async def get_latest_block_number(self):
                return blockchain.current_block

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))

        status = await check_transaction_status(tx_hash)

        assert status["status"] == "reverted"
        assert status["confirmations"] == 0
        assert status["receipt"] is not None
        assert status["receipt"]["status"] == 0


class TestWaitForConfirmation:
    """Tests for wait_for_confirmation function"""

    @pytest.mark.asyncio
    async def test_custom_confirmations(self, monkeypatch):
        """Test waiting for custom confirmation count"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import Settings

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
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return blockchain.transactions.get(tx_hash)

            async def get_latest_block_number(self):
                return blockchain.current_block

        settings = Settings(required_confirmations=3)

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should use custom confirmation count (parameter overrides config)
        receipt = await wait_for_confirmation(tx_hash, required_confirmations=2)

        assert receipt is not None
        assert receipt["status"] == 1

    @pytest.mark.asyncio
    async def test_default_confirmations(self, monkeypatch):
        """Test that default confirmations from config are used"""
        from tests.mocks.mock_blockchain import MockBlockchain
        from tests.mocks.mock_utils import MockLogger
        from abs_worker.config import Settings

        # Create mock blockchain with confirmed transaction
        blockchain = MockBlockchain()
        tx_hash = "0xdefault789"
        blockchain.transactions[tx_hash] = {
            "status": 1,
            "blockNumber": 100,
            "transactionHash": tx_hash,
        }
        blockchain.current_block = 103  # 3 confirmations

        # Mock BlockchainClient
        class MockClient:
            async def get_transaction_receipt(self, tx_hash):
                return blockchain.transactions.get(tx_hash)

            async def get_latest_block_number(self):
                return blockchain.current_block

        settings = Settings(required_confirmations=3, poll_interval=0.01)

        monkeypatch.setattr("abs_worker.monitoring.BlockchainClient", lambda: MockClient())
        monkeypatch.setattr("abs_worker.monitoring.logger", MockLogger("monitoring"))
        monkeypatch.setattr("abs_worker.monitoring.get_settings", lambda: settings)

        # Should use config default (no parameter passed)
        receipt = await wait_for_confirmation(tx_hash)

        assert receipt is not None
        assert receipt["status"] == 1
