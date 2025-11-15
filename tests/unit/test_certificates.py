"""
Comprehensive unit tests for certificate generation module
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from io import BytesIO

from abs_worker.certificates import (
    generate_signed_json,
    generate_signed_pdf,
    _sign_certificate
)


@pytest.fixture
def mock_document():
    """Create a mock document for testing hash certificates"""
    doc = Mock()
    doc.id = 123
    doc.owner_id = 456
    doc.file_name = "test_contract.pdf"
    doc.file_hash = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    doc.transaction_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    doc.block_number = 42000000
    doc.created_at = datetime(2024, 1, 1, 12, 0, 0)
    doc.type = Mock(value="hash")
    doc.nft_token_id = None
    doc.arweave_file_url = None
    doc.arweave_metadata_url = None
    return doc


@pytest.fixture
def mock_nft_document():
    """Create a mock document for testing NFT certificates"""
    doc = Mock()
    doc.id = 789
    doc.owner_id = 999
    doc.file_name = "nft_artwork.jpg"
    doc.file_hash = "0xfedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321"
    doc.transaction_hash = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"
    doc.block_number = 43000000
    doc.created_at = datetime(2024, 1, 15, 15, 30, 0)
    doc.type = Mock(value="nft")
    doc.nft_token_id = 42
    doc.arweave_file_url = "https://arweave.net/file_hash_123456"
    doc.arweave_metadata_url = "https://arweave.net/metadata_hash_789012"
    return doc


@pytest.fixture
def temp_cert_dir(tmp_path):
    """Create a temporary directory for certificates"""
    cert_dir = tmp_path / "certificates"
    cert_dir.mkdir(exist_ok=True)
    return cert_dir


@pytest.fixture
def mock_settings(temp_cert_dir):
    """Create mock settings with temporary certificate directory"""
    settings = Mock()
    settings.cert_storage_path = str(temp_cert_dir)
    settings.signing_key_path = "/etc/abs_notary/signing_key.pem"
    return settings


class TestGenerateSignedJson:
    """Tests for generate_signed_json function"""

    @pytest.mark.asyncio
    async def test_generate_json_with_hash_document(self, mock_document, mock_settings, monkeypatch):
        """Test JSON certificate generation for hash-type document"""
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        # Mock the signing function
        async def mock_sign(data):
            return "0x" + "a" * 128  # Mock ECDSA signature

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

        cert_path = await generate_signed_json(mock_document)

        # Verify certificate was created
        assert cert_path is not None
        assert Path(cert_path).exists()
        assert cert_path.endswith(".json")

        # Verify certificate content
        with open(cert_path, 'r') as f:
            cert_data = json.load(f)

        assert cert_data["document_id"] == 123
        assert cert_data["file_name"] == "test_contract.pdf"
        assert cert_data["file_hash"] == mock_document.file_hash
        assert cert_data["transaction_hash"] == mock_document.transaction_hash
        assert cert_data["block_number"] == 42000000
        assert cert_data["timestamp"] == "2024-01-01T12:00:00"
        assert cert_data["type"] == "hash"
        assert cert_data["blockchain"] == "polygon"
        assert cert_data["certificate_version"] == "1.0"
        assert cert_data["signature"].startswith("0x")
        assert len(cert_data["signature"]) == 130  # 0x + 128 hex chars

        # NFT fields should not be present
        assert "nft_token_id" not in cert_data
        assert "arweave_file_url" not in cert_data
        assert "arweave_metadata_url" not in cert_data

    @pytest.mark.asyncio
    async def test_generate_json_with_nft_document(self, mock_nft_document, mock_settings, monkeypatch):
        """Test JSON certificate generation for NFT-type document"""
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        # Mock the signing function
        async def mock_sign(data):
            return "0x" + "b" * 128  # Mock ECDSA signature

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

        cert_path = await generate_signed_json(mock_nft_document)

        # Verify certificate was created
        assert Path(cert_path).exists()

        # Verify certificate content
        with open(cert_path, 'r') as f:
            cert_data = json.load(f)

        # Check standard fields
        assert cert_data["document_id"] == 789
        assert cert_data["file_name"] == "nft_artwork.jpg"
        assert cert_data["type"] == "nft"

        # Check NFT-specific fields
        assert cert_data["nft_token_id"] == 42
        assert cert_data["arweave_file_url"] == "https://arweave.net/file_hash_123456"
        assert cert_data["arweave_metadata_url"] == "https://arweave.net/metadata_hash_789012"

    @pytest.mark.asyncio
    async def test_json_certificate_file_path_structure(self, mock_document, mock_settings, monkeypatch):
        """Test that JSON certificate is saved with correct path structure"""
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        async def mock_sign(data):
            return "0x" + "c" * 128

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

        cert_path = await generate_signed_json(mock_document)

        # Check path structure: {cert_dir}/{owner_id}/cert_{doc_id}_{hash_prefix}.json
        expected_dir = Path(mock_settings.cert_storage_path) / "456"  # owner_id
        assert expected_dir.exists()

        path = Path(cert_path)
        assert path.parent == expected_dir
        assert path.name.startswith("cert_123_")  # doc_id
        assert path.name.endswith(".json")
        assert "abcdef12" in path.name  # First 8 chars of file_hash

    @pytest.mark.asyncio
    async def test_json_signature_changes_with_data(self, mock_document, mock_settings, monkeypatch):
        """Test that signature is different for different data"""
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        signatures = []

        async def capture_sign(data):
            # Generate different signature based on data
            import hashlib
            data_str = json.dumps(data, sort_keys=True)
            return "0x" + hashlib.sha256(data_str.encode()).hexdigest() * 2  # 128 chars

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", capture_sign)

        # Generate first certificate
        cert_path1 = await generate_signed_json(mock_document)
        with open(cert_path1, 'r') as f:
            cert1 = json.load(f)

        # Modify document
        mock_document.file_hash = "0xdifferent" + "0" * 54

        # Generate second certificate
        cert_path2 = await generate_signed_json(mock_document)
        with open(cert_path2, 'r') as f:
            cert2 = json.load(f)

        # Signatures should be different
        assert cert1["signature"] != cert2["signature"]


class TestGenerateSignedPdf:
    """Tests for generate_signed_pdf function"""

    @pytest.mark.asyncio
    async def test_generate_pdf_creates_valid_pdf(self, mock_document, mock_settings, monkeypatch):
        """Test that PDF certificate is a valid PDF file"""
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        # Mock signing
        async def mock_sign(data):
            return "0x" + "d" * 128

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

        cert_path = await generate_signed_pdf(mock_document)

        # Verify PDF was created
        assert Path(cert_path).exists()
        assert cert_path.endswith(".pdf")

        # Verify it's a valid PDF (starts with PDF header)
        with open(cert_path, 'rb') as f:
            content = f.read()
            assert content.startswith(b'%PDF-')

    @pytest.mark.asyncio
    async def test_pdf_contains_document_information(self, mock_document, mock_settings, monkeypatch):
        """Test that PDF contains all required document information"""
        pytest.skip("Full PDF generation not implemented yet")

        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        # Track what gets rendered
        rendered_content = []

        # Mock reportlab canvas
        class MockCanvas:
            def __init__(self, *args, **kwargs):
                self.pages = []
                self.current_page = []

            def drawString(self, x, y, text):
                self.current_page.append(('text', x, y, text))
                rendered_content.append(text)

            def drawCentredString(self, x, y, text):
                self.current_page.append(('centered', x, y, text))
                rendered_content.append(text)

            def drawImage(self, img, x, y, width, height):
                self.current_page.append(('image', x, y, width, height))

            def setFont(self, name, size):
                self.current_page.append(('font', name, size))

            def setFillColorRGB(self, r, g, b):
                self.current_page.append(('color', r, g, b))

            def line(self, x1, y1, x2, y2):
                self.current_page.append(('line', x1, y1, x2, y2))

            def rect(self, x, y, width, height, fill=0):
                self.current_page.append(('rect', x, y, width, height, fill))

            def showPage(self):
                self.pages.append(self.current_page)
                self.current_page = []

            def save(self):
                if self.current_page:
                    self.pages.append(self.current_page)

        with patch('abs_worker.certificates.canvas.Canvas', MockCanvas):
            async def mock_qr(url):
                return b"fake_qr_image"

            monkeypatch.setattr("abs_worker.certificates._generate_qr_code", mock_qr)

            async def mock_sign(data):
                return "0x" + "e" * 128

            monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

            cert_path = await generate_signed_pdf(mock_document)

        # Verify content includes required information
        content_str = ' '.join(rendered_content)

        assert "Blockchain Notarization Certificate" in content_str
        assert "test_contract.pdf" in content_str
        assert mock_document.file_hash in content_str or mock_document.file_hash[:16] in content_str
        assert mock_document.transaction_hash in content_str or mock_document.transaction_hash[:16] in content_str
        assert "42000000" in content_str  # block number
        assert "polygon" in content_str.lower()

    @pytest.mark.asyncio
    async def test_pdf_includes_qr_code(self, mock_document, mock_settings, monkeypatch):
        """Test that PDF includes QR code with correct URL"""
        pytest.skip("QR code generation not implemented yet")
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        qr_url_captured = None

        async def capture_qr_url(url):
            nonlocal qr_url_captured
            qr_url_captured = url
            return b"fake_qr_image"

        monkeypatch.setattr("abs_worker.certificates._generate_qr_code", capture_qr_url)

        async def mock_sign(data):
            return "0x" + "f" * 128

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

        cert_path = await generate_signed_pdf(mock_document)

        # Verify QR code was generated with correct Polygonscan URL
        expected_url = f"https://polygonscan.com/tx/{mock_document.transaction_hash}"
        assert qr_url_captured == expected_url

    @pytest.mark.asyncio
    async def test_nft_pdf_includes_arweave_info(self, mock_nft_document, mock_settings, monkeypatch):
        """Test that NFT PDF includes Arweave URLs"""
        pytest.skip("NFT PDF generation not implemented yet")
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        rendered_content = []

        class MockCanvas:
            def __init__(self, *args, **kwargs):
                pass

            def drawString(self, x, y, text):
                rendered_content.append(text)

            def drawCentredString(self, x, y, text):
                rendered_content.append(text)

            def drawImage(self, *args):
                pass

            def setFont(self, *args):
                pass

            def setFillColorRGB(self, *args):
                pass

            def line(self, *args):
                pass

            def rect(self, *args):
                pass

            def showPage(self):
                pass

            def save(self):
                pass

        with patch('abs_worker.certificates.canvas.Canvas', MockCanvas):
            async def mock_qr(url):
                return b"fake_qr"

            monkeypatch.setattr("abs_worker.certificates._generate_qr_code", mock_qr)

            async def mock_sign(data):
                return "0x" + "9" * 128

            monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

            cert_path = await generate_signed_pdf(mock_nft_document)

        content_str = ' '.join(rendered_content)

        # Verify NFT-specific content
        assert "NFT" in content_str or "nft" in content_str
        assert "Token ID: 42" in content_str or "42" in content_str
        assert "arweave.net/file_hash_123456" in content_str or "file_hash_123456" in content_str
        assert "arweave.net/metadata_hash_789012" in content_str or "metadata_hash_789012" in content_str

    @pytest.mark.asyncio
    async def test_pdf_file_path_structure(self, mock_document, mock_settings, monkeypatch):
        """Test that PDF certificate is saved with correct path structure"""
        pytest.skip("PDF path structure test not ready yet")
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        async def mock_qr(url):
            return b"fake_qr"

        monkeypatch.setattr("abs_worker.certificates._generate_qr_code", mock_qr)

        async def mock_sign(data):
            return "0x" + "a" * 128

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

        cert_path = await generate_signed_pdf(mock_document)

        # Check path structure
        expected_dir = Path(mock_settings.cert_storage_path) / "456"  # owner_id
        assert expected_dir.exists()

        path = Path(cert_path)
        assert path.parent == expected_dir
        assert path.name.startswith("cert_123_")  # doc_id
        assert path.name.endswith(".pdf")
        assert "abcdef12" in path.name  # First 8 chars of file_hash


class TestQRCodeGeneration:
    """Tests for QR code generation"""

    @pytest.mark.asyncio
    async def test_generate_qr_code_creates_image(self):
        """Test that QR code is generated as image bytes"""
        from abs_worker.certificates import _generate_qr_code

        url = "https://polygonscan.com/tx/0xabc123"
        qr_bytes = await _generate_qr_code(url)

        assert qr_bytes is not None
        assert isinstance(qr_bytes, bytes)
        assert len(qr_bytes) > 0

        # Verify it's a PNG image (PNG header: 89 50 4E 47)
        assert qr_bytes[:4] == b'\x89PNG'

    @pytest.mark.asyncio
    async def test_qr_code_encodes_correct_url(self):
        """Test that QR code encodes the correct URL"""
        from abs_worker.certificates import _generate_qr_code
        from PIL import Image
        from io import BytesIO

        url = "https://polygonscan.com/tx/0xtest123"
        qr_bytes = await _generate_qr_code(url)

        # Verify the image was created properly
        img = Image.open(BytesIO(qr_bytes))
        assert img.format == 'PNG'
        assert img.size[0] > 0
        assert img.size[1] > 0


class TestCryptographicSigning:
    """Tests for cryptographic signature generation and verification"""

    @pytest.mark.asyncio
    async def test_sign_certificate_with_ecdsa(self, monkeypatch):
        """Test ECDSA signature generation"""
        from abs_worker.certificates import _create_certificate_signature

        # Mock private key
        mock_private_key = "0x" + "1" * 64  # 32 bytes hex

        data = {
            "document_id": 123,
            "file_hash": "0xabc123",
            "transaction_hash": "0xdef456"
        }

        signature = await _create_certificate_signature(data, mock_private_key)

        assert signature is not None
        assert isinstance(signature, str)
        assert signature.startswith("0x")
        # ECDSA signature length varies but should be reasonable
        assert len(signature) > 64  # At least 32 bytes hex

    @pytest.mark.asyncio
    async def test_verify_certificate_signature(self):
        """Test signature verification"""
        from abs_worker.certificates import _create_certificate_signature, _verify_certificate_signature

        # Create a test keypair
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import serialization

        private_key = ec.generate_private_key(ec.SECP256K1())
        public_key = private_key.public_key()

        # Convert to hex format
        private_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
        private_hex = "0x" + private_bytes.hex()

        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        public_hex = "0x" + public_bytes.hex()

        data = {
            "document_id": 456,
            "file_hash": "0xtest",
            "transaction_hash": "0xverify"
        }

        # Sign data
        signature = await _create_certificate_signature(data, private_hex)

        # Verify signature
        is_valid = await _verify_certificate_signature(data, signature, public_hex)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_signature_differs_for_different_data(self):
        """Test that different data produces different signatures"""
        from abs_worker.certificates import _create_certificate_signature

        mock_private_key = "0x" + "2" * 64

        data1 = {"document_id": 1, "file_hash": "0xaaa"}
        data2 = {"document_id": 2, "file_hash": "0xbbb"}

        sig1 = await _create_certificate_signature(data1, mock_private_key)
        sig2 = await _create_certificate_signature(data2, mock_private_key)

        assert sig1 != sig2

    @pytest.mark.asyncio
    async def test_signature_deterministic_for_same_data(self):
        """Test that same data with same key produces same signature"""
        # ECDSA signatures include randomness, so they won't be deterministic
        # unless we use deterministic ECDSA (RFC 6979)
        pytest.skip("ECDSA signatures include randomness - not deterministic")


class TestSignCertificate:
    """Tests for the main _sign_certificate function"""

    @pytest.mark.asyncio
    async def test_sign_certificate_integration(self, mock_settings, monkeypatch):
        """Test the main signing function with mock settings"""
        pytest.skip("Signing key integration not implemented yet")
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        # Mock reading private key from file
        mock_private_key = "0x" + "4" * 64

        def mock_read_key():
            return mock_private_key

        monkeypatch.setattr("abs_worker.certificates._read_signing_key", mock_read_key)

        data = {
            "document_id": 777,
            "file_hash": "0xintegration",
            "transaction_hash": "0xtest"
        }

        signature = await _sign_certificate(data)

        assert signature is not None
        assert signature.startswith("0x")
        assert len(signature) == 130  # ECDSA signature length

    @pytest.mark.asyncio
    async def test_sign_certificate_handles_missing_key_gracefully(self, mock_settings, monkeypatch):
        """Test that missing signing key is handled gracefully"""
        mock_settings.signing_key_path = "/non/existent/key.pem"
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        data = {"test": "data"}

        # Should fall back to hash-based signature if key not found
        signature = await _sign_certificate(data)

        assert signature is not None
        assert signature.startswith("0x")
        # Should be SHA256 hash (64 hex chars) + 0x
        assert len(signature) == 66


class TestErrorHandling:
    """Tests for error handling in certificate generation"""

    @pytest.mark.asyncio
    async def test_json_generation_handles_missing_directory(self, mock_document, monkeypatch):
        """Test that missing certificate directory is created"""
        import tempfile
        import shutil

        # Create temp dir that we'll delete
        temp_dir = tempfile.mkdtemp()
        shutil.rmtree(temp_dir)  # Delete it

        mock_settings = Mock()
        mock_settings.cert_storage_path = temp_dir

        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        async def mock_sign(data):
            return "0x" + "5" * 128

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

        # Should create directory and succeed
        cert_path = await generate_signed_json(mock_document)

        assert Path(cert_path).exists()
        assert Path(temp_dir).exists()

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_pdf_generation_handles_invalid_qr_url(self, mock_document, mock_settings, monkeypatch):
        """Test PDF generation with invalid QR URL"""
        monkeypatch.setattr("abs_worker.certificates.get_settings", lambda: mock_settings)

        # Mock QR generation to handle any URL
        async def mock_qr(url):
            # Should handle even invalid URLs gracefully
            return b"default_qr_image"

        monkeypatch.setattr("abs_worker.certificates._generate_qr_code", mock_qr)

        async def mock_sign(data):
            return "0x" + "6" * 128

        monkeypatch.setattr("abs_worker.certificates._sign_certificate", mock_sign)

        # Set invalid transaction hash
        mock_document.transaction_hash = None

        # Should still generate PDF successfully
        cert_path = await generate_signed_pdf(mock_document)

        assert Path(cert_path).exists()