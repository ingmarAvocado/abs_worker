"""
Contract validation tests for mock implementations.

These tests ensure that mock interfaces match the expected contracts
defined in the issue requirements.
"""

import pytest
from tests.mocks import (
    MockDocument,
    MockDocumentRepository,
    MockBlockchain,
    DocStatus,
    DocType,
    get_session,
    BlockchainException,
    InsufficientFundsException,
    ContractRevertedException,
    GasEstimationException,
    NetworkTimeoutException,
    get_logger,
    MockException,
    ValidationError,
    ConfigurationError,
    create_document,
    create_hash_document,
    create_nft_document,
)


class TestMockDocumentContract:
    """Test MockDocument matches abs_orm.Document contract"""

    def test_document_has_required_fields(self):
        """Test document has all required fields"""
        doc = create_document()

        # Required fields
        assert hasattr(doc, 'id')
        assert hasattr(doc, 'file_name')
        assert hasattr(doc, 'file_hash')
        assert hasattr(doc, 'file_path')
        assert hasattr(doc, 'status')
        assert hasattr(doc, 'type')
        assert hasattr(doc, 'owner_id')
        assert hasattr(doc, 'created_at')

        # Optional fields
        assert hasattr(doc, 'transaction_hash')
        assert hasattr(doc, 'arweave_file_url')
        assert hasattr(doc, 'arweave_metadata_url')
        assert hasattr(doc, 'nft_token_id')
        assert hasattr(doc, 'error_message')

    def test_document_field_types(self):
        """Test document fields have correct types"""
        doc = create_document()

        assert isinstance(doc.id, int)
        assert isinstance(doc.file_name, str)
        assert isinstance(doc.file_hash, str)
        assert isinstance(doc.file_path, str)
        assert isinstance(doc.status, DocStatus)
        assert isinstance(doc.type, DocType)
        assert isinstance(doc.owner_id, int)
        assert doc.created_at is not None

    def test_document_status_enum(self):
        """Test DocStatus enum values"""
        assert DocStatus.PENDING.value == "pending"
        assert DocStatus.PROCESSING.value == "processing"
        assert DocStatus.ON_CHAIN.value == "on_chain"
        assert DocStatus.ERROR.value == "error"

    def test_document_type_enum(self):
        """Test DocType enum values"""
        assert DocType.HASH.value == "hash"
        assert DocType.NFT.value == "nft"


class TestMockDocumentRepositoryContract:
    """Test MockDocumentRepository matches abs_orm.DocumentRepository contract"""

    @pytest.mark.asyncio
    async def test_repository_get_method(self):
        """Test repository get method signature"""
        repo = MockDocumentRepository()

        # Should return None for non-existent document
        result = await repo.get(999)
        assert result is None

        # Should return document when it exists
        doc = create_document(id=1)
        repo.documents[1] = doc
        result = await repo.get(1)
        assert result == doc

    @pytest.mark.asyncio
    async def test_repository_update_method(self):
        """Test repository update method signature"""
        repo = MockDocumentRepository()
        doc = create_document(id=1, status=DocStatus.PENDING)
        repo.documents[1] = doc

        # Update status
        updated = await repo.update(1, status=DocStatus.PROCESSING)
        assert updated.status == DocStatus.PROCESSING
        assert updated.id == 1

    @pytest.mark.asyncio
    async def test_repository_create_method(self):
        """Test repository create method signature"""
        repo = MockDocumentRepository()

        doc_data = {
            'file_name': 'test.pdf',
            'file_hash': '0x123',
            'file_path': '/tmp/test.pdf',
        }

        created = await repo.create(doc_data)
        assert created.id == 1  # First document
        assert created.file_name == 'test.pdf'
        assert created.status == DocStatus.PENDING  # Default


class TestMockBlockchainContract:
    """Test MockBlockchain matches abs_blockchain contract"""

    @pytest.mark.asyncio
    async def test_record_hash_signature(self):
        """Test record_hash method signature"""
        blockchain = MockBlockchain()

        file_hash = "0xabc123"
        metadata = {"doc_id": 123}

        tx_hash = await blockchain.record_hash(file_hash, metadata)
        assert isinstance(tx_hash, str)
        assert tx_hash.startswith("0x")

    @pytest.mark.asyncio
    async def test_mint_nft_signature(self):
        """Test mint_nft method signature"""
        blockchain = MockBlockchain()

        owner_address = "0x1234567890abcdef"
        token_id = 1
        metadata_url = "https://arweave.net/abc123"

        tx_hash = await blockchain.mint_nft(owner_address, token_id, metadata_url)
        assert isinstance(tx_hash, str)
        assert tx_hash.startswith("0x")

    @pytest.mark.asyncio
    async def test_upload_to_arweave_signature(self):
        """Test upload_to_arweave method signature"""
        blockchain = MockBlockchain()

        file_data = b"test file content"
        content_type = "application/pdf"

        url = await blockchain.upload_to_arweave(file_data, content_type)
        assert isinstance(url, str)
        assert url.startswith("https://arweave.net/")

    @pytest.mark.asyncio
    async def test_get_transaction_receipt_signature(self):
        """Test get_transaction_receipt method signature"""
        blockchain = MockBlockchain()

        # Test with existing transaction
        tx_hash = "0x0000000000000000000000000000000000000000000000000000000000001000"
        receipt = await blockchain.get_transaction_receipt(tx_hash)

        assert receipt["transactionHash"] == tx_hash
        assert "blockNumber" in receipt
        assert "status" in receipt
        assert "confirmations" in receipt

    @pytest.mark.asyncio
    async def test_get_latest_block_number_signature(self):
        """Test get_latest_block_number method signature"""
        blockchain = MockBlockchain()

        block_number = await blockchain.get_latest_block_number()
        assert isinstance(block_number, int)
        assert block_number > 0


class TestBlockchainExceptions:
    """Test blockchain exception hierarchy"""

    def test_exception_inheritance(self):
        """Test exceptions inherit from BlockchainException"""
        assert issubclass(InsufficientFundsException, BlockchainException)
        assert issubclass(ContractRevertedException, BlockchainException)
        assert issubclass(GasEstimationException, BlockchainException)
        assert issubclass(NetworkTimeoutException, BlockchainException)

    def test_exception_creation(self):
        """Test exceptions can be created"""
        exc = InsufficientFundsException("Not enough funds")
        assert str(exc) == "Not enough funds"

        exc = ContractRevertedException("Contract failed")
        assert str(exc) == "Contract failed"


class TestMockUtilsContract:
    """Test mock utils match abs_utils contract"""

    def test_get_logger_signature(self):
        """Test get_logger returns logger with correct interface"""
        logger = get_logger("test")

        # Should have logging methods
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')

    def test_logger_extra_parameter(self):
        """Test logger accepts extra parameter"""
        logger = get_logger("test")

        # Should not raise exception
        logger.info("Test message", extra={"key": "value"})

    def test_mock_exception_to_dict(self):
        """Test MockException.to_dict() method"""
        exc = MockException("Test error", "TEST_ERROR", {"field": "value"})

        dict_repr = exc.to_dict()
        assert dict_repr["error_code"] == "TEST_ERROR"
        assert dict_repr["message"] == "Test error"
        assert dict_repr["details"]["field"] == "value"
        assert "exception_type" in dict_repr

    def test_validation_error(self):
        """Test ValidationError creation"""
        exc = ValidationError("Invalid input", "email")
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details["field"] == "email"

    def test_configuration_error(self):
        """Test ConfigurationError creation"""
        exc = ConfigurationError("Missing config", "database_url")
        assert exc.error_code == "CONFIGURATION_ERROR"
        assert exc.details["config_key"] == "database_url"


class TestMockSessionContract:
    """Test get_session matches abs_orm session contract"""

    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test session is async context manager"""
        async with get_session() as session:
            assert hasattr(session, 'commit')
            assert hasattr(session, 'rollback')
            assert hasattr(session, 'close')

            # Test session methods are async
            await session.commit()
            await session.rollback()
            await session.close()


class TestFactoryFunctions:
    """Test factory functions create valid objects"""

    def test_create_document_factory(self):
        """Test create_document factory"""
        doc = create_document(id=999, file_name="custom.pdf")
        assert doc.id == 999
        assert doc.file_name == "custom.pdf"
        assert doc.status == DocStatus.PENDING

    def test_create_hash_document_factory(self):
        """Test create_hash_document factory"""
        doc = create_hash_document(id=100)
        assert doc.type == DocType.HASH
        assert doc.id == 100

    def test_create_nft_document_factory(self):
        """Test create_nft_document factory"""
        doc = create_nft_document(id=200)
        assert doc.type == DocType.NFT
        assert doc.id == 200

    def test_document_factories_have_correct_defaults(self):
        """Test factory functions have sensible defaults"""
        hash_doc = create_hash_document()
        nft_doc = create_nft_document()

        assert hash_doc.type == DocType.HASH
        assert nft_doc.type == DocType.NFT
        assert hash_doc.status == DocStatus.PENDING
        assert nft_doc.status == DocStatus.PENDING


class TestMockImports:
    """Test that mock modules can be imported successfully"""

    def test_mock_orm_imports(self):
        """Test mock_orm module imports"""
        from tests.mocks.mock_orm import MockDocument, MockDocumentRepository, DocStatus, DocType
        assert MockDocument is not None
        assert MockDocumentRepository is not None
        assert DocStatus is not None
        assert DocType is not None

    def test_mock_blockchain_imports(self):
        """Test mock_blockchain module imports"""
        from tests.mocks.mock_blockchain import MockBlockchain, BlockchainException
        assert MockBlockchain is not None
        assert BlockchainException is not None

    def test_mock_utils_imports(self):
        """Test mock_utils module imports"""
        from tests.mocks.mock_utils import get_logger, MockException
        assert get_logger is not None
        assert MockException is not None

    def test_factories_imports(self):
        """Test factories module imports"""
        from tests.mocks.factories import create_document, create_hash_document
        assert create_document is not None
        assert create_hash_document is not None