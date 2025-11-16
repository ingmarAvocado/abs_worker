"""
Mock implementations of abs_blockchain interfaces for testing and examples.

This module provides drop-in replacements for abs_blockchain components that can be used
in tests and examples without requiring real blockchain connections.
"""

import random
from typing import Dict, Any


class BlockchainException(Exception):
    """Base exception for blockchain operations"""

    pass


class InsufficientFundsException(BlockchainException):
    """Raised when account has insufficient funds for transaction"""

    pass


class ContractRevertedException(BlockchainException):
    """Raised when smart contract execution reverts"""

    pass


class GasEstimationException(BlockchainException):
    """Raised when gas estimation fails"""

    pass


class NetworkTimeoutException(BlockchainException):
    """Raised when network operations timeout"""

    pass


class NotarizationResult:
    """Mock result object returned by notarize_hash"""

    def __init__(self, transaction_hash: str):
        self.transaction_hash = transaction_hash


class NftMintResult:
    """Mock result object returned by mint_nft_from_file"""

    def __init__(
        self, transaction_hash: str, token_id: int, arweave_file_url: str, arweave_metadata_url: str
    ):
        self.transaction_hash = transaction_hash
        self.token_id = token_id
        self.arweave_file_url = arweave_file_url
        self.arweave_metadata_url = arweave_metadata_url


class MockBlockchain:
    """Mock blockchain interface matching abs_blockchain interface"""

    def __init__(self):
        self.transactions: Dict[str, Dict[str, Any]] = {}
        self.next_tx_id = 1000
        self.current_block = 12345678

    async def notarize_hash(self, file_hash: str, metadata: dict) -> NotarizationResult:
        """Mock notarize_hash - returns NotarizationResult object"""
        tx_hash = f"0x{self.next_tx_id:064x}"
        self.next_tx_id += 1

        self.transactions[tx_hash] = {
            "type": "record_hash",
            "file_hash": file_hash,
            "metadata": metadata,
            "block_number": self.current_block,
            "status": 1,  # Success
        }

        return NotarizationResult(tx_hash)

    async def record_hash(self, file_hash: str, metadata: dict) -> str:
        """Mock record_hash - returns fake transaction hash (deprecated, use notarize_hash)"""
        result = await self.notarize_hash(file_hash, metadata)
        return result.transaction_hash

    async def mint_nft(self, owner_address: str, token_id: int, metadata_url: str) -> str:
        """Mock mint_nft - returns fake transaction hash"""
        tx_hash = f"0x{self.next_tx_id:064x}"
        self.next_tx_id += 1

        self.transactions[tx_hash] = {
            "type": "mint_nft",
            "owner_address": owner_address,
            "token_id": token_id,
            "metadata_url": metadata_url,
            "block_number": self.current_block,
            "status": 1,  # Success
        }

        return tx_hash

    async def mint_nft_from_file(
        self, file_path: str, file_hash: str, metadata: dict
    ) -> NftMintResult:
        """Mock mint_nft_from_file - returns NftMintResult with automatic Arweave upload"""
        tx_hash = f"0x{self.next_tx_id:064x}"
        self.next_tx_id += 1
        token_id = self.next_tx_id  # Use next_tx_id as token_id for simplicity
        arweave_file_url = f"https://arweave.net/{random.randint(100000, 999999)}"
        arweave_metadata_url = f"https://arweave.net/{random.randint(100000, 999999)}"

        self.transactions[tx_hash] = {
            "type": "mint_nft_from_file",
            "file_path": file_path,
            "file_hash": file_hash,
            "metadata": metadata,
            "token_id": token_id,
            "arweave_file_url": arweave_file_url,
            "arweave_metadata_url": arweave_metadata_url,
            "block_number": self.current_block,
            "status": 1,  # Success
        }

        return NftMintResult(tx_hash, token_id, arweave_file_url, arweave_metadata_url)

    async def upload_to_arweave(self, file_data: bytes, content_type: str) -> str:
        """Mock upload_to_arweave - returns fake Arweave URL"""
        # Generate fake Arweave transaction ID
        arweave_id = f"{random.randint(100000, 999999)}"
        return f"https://arweave.net/{arweave_id}"

    async def get_transaction_receipt(self, tx_hash: str) -> Dict[str, Any]:
        """Mock get_transaction_receipt - returns transaction receipt"""
        if tx_hash not in self.transactions:
            return {
                "transactionHash": tx_hash,
                "blockNumber": None,
                "status": 0,  # Not found
                "confirmations": 0,
            }

        tx = self.transactions[tx_hash]
        confirmations = min(3, self.current_block - tx["block_number"])

        return {
            "transactionHash": tx_hash,
            "blockNumber": tx["block_number"],
            "blockHash": f"0xblock{tx['block_number']:064x}",
            "status": tx["status"],
            "confirmations": confirmations,
            "gasUsed": 50000,
            "from": "0xmock_sender",
            "to": "0xmock_contract",
        }

    async def get_latest_block_number(self) -> int:
        """Mock get_latest_block_number"""
        return self.current_block

    async def wait_for_confirmations(
        self, tx_hash: str, required_confirmations: int = 3
    ) -> Dict[str, Any]:
        """Mock wait_for_confirmations - simulates waiting for block confirmations"""
        # Advance block number to simulate mining
        self.current_block += required_confirmations

        receipt = await self.get_transaction_receipt(tx_hash)
        return receipt

    # Methods to simulate failures for testing
    def set_next_transaction_failure(self, exception_instance: Exception):
        """Set the next transaction to fail with given exception"""
        self._next_failure = exception_instance

    async def _check_for_failure(self):
        """Check if next operation should fail"""
        if hasattr(self, "_next_failure"):
            exc = self._next_failure
            delattr(self, "_next_failure")
            raise exc


# Convenience functions for testing different scenarios
def create_successful_blockchain() -> MockBlockchain:
    """Create a blockchain that always succeeds"""
    return MockBlockchain()


def create_failing_blockchain() -> MockBlockchain:
    """Create a blockchain that fails on next operation"""
    blockchain = MockBlockchain()
    blockchain.set_next_transaction_failure(ContractRevertedException("Mock contract revert"))
    return blockchain


def create_timeout_blockchain() -> MockBlockchain:
    """Create a blockchain that times out on next operation"""
    blockchain = MockBlockchain()
    blockchain.set_next_transaction_failure(NetworkTimeoutException("Mock network timeout"))
    return blockchain
