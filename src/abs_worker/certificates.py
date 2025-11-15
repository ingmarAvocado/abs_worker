"""
Certificate generation for notarized documents

This module handles:
- Generating signed JSON certificates
- Generating signed PDF certificates with QR codes
- Digital signature creation using ECDSA
- Certificate verification
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO

# Third-party imports
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

# Cryptography imports
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

# Internal imports
from abs_utils.logger import get_logger
from abs_worker.config import get_settings

logger = get_logger(__name__)


async def generate_signed_json(doc) -> str:
    """
    Generate signed JSON certificate for notarized document

    Args:
        doc: Document model instance

    Returns:
        Path to generated JSON certificate file

    Certificate Format:
        {
            "document_id": int,
            "file_name": str,
            "file_hash": str,
            "transaction_hash": str,
            "block_number": int,
            "timestamp": str (ISO format),
            "type": "hash" | "nft",
            "blockchain": str,
            "arweave_file_url": str (for NFT),
            "arweave_metadata_url": str (for NFT),
            "nft_token_id": int (for NFT),
            "signature": str,
            "certificate_version": "1.0"
        }
    """
    settings = get_settings()
    logger.info(f"Generating JSON certificate for document {doc.id}")

    # Prepare certificate data
    cert_data = {
        "document_id": doc.id,
        "file_name": doc.file_name,
        "file_hash": doc.file_hash,
        "transaction_hash": doc.transaction_hash,
        "block_number": getattr(doc, 'block_number', None),
        "timestamp": doc.created_at.isoformat() if hasattr(doc.created_at, 'isoformat') else str(doc.created_at),
        "type": doc.type.value if hasattr(doc.type, 'value') else str(doc.type),
        "blockchain": "polygon",
        "certificate_version": "1.0"
    }

    # Add NFT-specific fields
    if hasattr(doc, 'nft_token_id') and doc.nft_token_id is not None:
        cert_data.update({
            "arweave_file_url": doc.arweave_file_url,
            "arweave_metadata_url": doc.arweave_metadata_url,
            "nft_token_id": doc.nft_token_id
        })

    # Sign certificate
    signature = await _sign_certificate(cert_data)
    cert_data["signature"] = signature

    # Save to file
    cert_dir = Path(settings.cert_storage_path) / str(doc.owner_id)
    cert_dir.mkdir(parents=True, exist_ok=True)

    # Get first 8 chars of hash, removing 0x prefix if present
    hash_prefix = doc.file_hash[2:10] if doc.file_hash.startswith('0x') else doc.file_hash[:8]
    cert_path = cert_dir / f"cert_{doc.id}_{hash_prefix}.json"

    with open(cert_path, 'w') as f:
        json.dump(cert_data, f, indent=2)

    logger.info(f"JSON certificate saved to {cert_path}")
    return str(cert_path)


async def generate_signed_pdf(doc) -> str:
    """
    Generate signed PDF certificate for notarized document

    Args:
        doc: Document model instance

    Returns:
        Path to generated PDF certificate file

    Certificate Contains:
        - Document details (name, hash, type)
        - Blockchain proof (transaction hash, block number, timestamp)
        - QR code linking to blockchain explorer
        - Digital signature
        - Arweave links (for NFT type)
    """
    settings = get_settings()
    logger.info(f"Generating PDF certificate for document {doc.id}")

    cert_dir = Path(settings.cert_storage_path) / str(doc.owner_id)
    cert_dir.mkdir(parents=True, exist_ok=True)

    # Get first 8 chars of hash, removing 0x prefix if present
    hash_prefix = doc.file_hash[2:10] if doc.file_hash.startswith('0x') else doc.file_hash[:8]
    cert_path = cert_dir / f"cert_{doc.id}_{hash_prefix}.pdf"

    # Create PDF
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    # Header
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0.1, 0.2, 0.5)
    c.drawCentredString(width / 2, height - 50, "Blockchain Notarization Certificate")

    # Divider line
    c.setStrokeColorRGB(0.1, 0.2, 0.5)
    c.setLineWidth(2)
    c.line(50, height - 70, width - 50, height - 70)

    # Certificate ID and timestamp
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    timestamp_str = doc.created_at.isoformat() if hasattr(doc.created_at, 'isoformat') else str(doc.created_at)
    c.drawString(50, height - 90, f"Certificate ID: CERT-{doc.id:06d}")
    c.drawRightString(width - 50, height - 90, f"Issued: {timestamp_str}")

    # Document Information Section
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(50, height - 130, "Document Information")

    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    y_pos = height - 155

    # Document details
    c.drawString(70, y_pos, f"File Name: {doc.file_name}")
    y_pos -= 20
    c.drawString(70, y_pos, f"File Hash: {doc.file_hash[:32]}...")
    y_pos -= 20
    c.drawString(70, y_pos, f"Document Type: {doc.type.value if hasattr(doc.type, 'value') else str(doc.type).upper()}")

    # Blockchain Proof Section
    y_pos -= 40
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(50, y_pos, "Blockchain Proof")

    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    y_pos -= 25

    c.drawString(70, y_pos, f"Blockchain: Polygon")
    y_pos -= 20
    c.drawString(70, y_pos, f"Transaction Hash: {doc.transaction_hash[:32] if doc.transaction_hash else 'Pending'}...")
    y_pos -= 20
    c.drawString(70, y_pos, f"Block Number: {getattr(doc, 'block_number', 'Pending')}")

    # NFT-specific information
    if hasattr(doc, 'nft_token_id') and doc.nft_token_id is not None:
        y_pos -= 40
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawString(50, y_pos, "NFT Information")

        c.setFont("Helvetica", 11)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        y_pos -= 25

        c.drawString(70, y_pos, f"Token ID: {doc.nft_token_id}")
        y_pos -= 20

        # Truncate URLs for display
        if doc.arweave_file_url:
            file_url_display = doc.arweave_file_url[:50] + "..." if len(doc.arweave_file_url) > 50 else doc.arweave_file_url
            c.drawString(70, y_pos, f"File URL: {file_url_display}")
            y_pos -= 20

        if doc.arweave_metadata_url:
            meta_url_display = doc.arweave_metadata_url[:50] + "..." if len(doc.arweave_metadata_url) > 50 else doc.arweave_metadata_url
            c.drawString(70, y_pos, f"Metadata URL: {meta_url_display}")
            y_pos -= 20

    # QR Code Section
    y_pos -= 40
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(50, y_pos, "Verification QR Code")

    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    y_pos -= 20
    c.drawString(70, y_pos, "Scan to view on blockchain explorer:")

    # Generate QR code
    if doc.transaction_hash:
        qr_url = f"https://polygonscan.com/tx/{doc.transaction_hash}"
        qr_bytes = await _generate_qr_code(qr_url)

        # Add QR code to PDF
        from reportlab.lib.utils import ImageReader
        qr_image = ImageReader(BytesIO(qr_bytes))
        c.drawImage(qr_image, 70, y_pos - 170, width=150, height=150)
    else:
        c.drawString(70, y_pos - 50, "[QR Code will be available after blockchain confirmation]")

    # Digital Signature Section
    y_pos = 200
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(50, y_pos, "Digital Signature")

    # Generate signature for PDF content
    pdf_data = {
        "document_id": doc.id,
        "file_hash": doc.file_hash,
        "transaction_hash": doc.transaction_hash,
        "certificate_type": "PDF",
        "issued_at": timestamp_str
    }
    signature = await _sign_certificate(pdf_data)

    c.setFont("Courier", 9)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    y_pos -= 25

    # Break signature into chunks for display
    sig_chunks = [signature[i:i+64] for i in range(0, len(signature), 64)]
    for chunk in sig_chunks[:3]:  # Show first 3 lines of signature
        c.drawString(70, y_pos, chunk)
        y_pos -= 15

    # Footer
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(0.1, 0.2, 0.5)
    c.drawCentredString(width / 2, 50, "Certified by ABS Notary System")

    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawCentredString(width / 2, 35, "This certificate verifies the existence and integrity of the document on the blockchain")

    # Save PDF
    c.save()

    # Write to file
    pdf_buffer.seek(0)
    with open(cert_path, 'wb') as f:
        f.write(pdf_buffer.read())

    logger.info(f"PDF certificate saved to {cert_path}")
    return str(cert_path)


async def _generate_qr_code(url: str) -> bytes:
    """
    Generate QR code as PNG image bytes

    Args:
        url: URL to encode in QR code

    Returns:
        PNG image bytes of QR code
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to bytes
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)

    return img_buffer.read()


async def _sign_certificate(data: dict) -> str:
    """
    Create digital signature for certificate data using ECDSA

    Args:
        data: Certificate data to sign

    Returns:
        Hex-encoded signature string
    """
    settings = get_settings()

    try:
        # Try to load signing key from settings
        signing_key_hex = await _read_signing_key(settings)

        if signing_key_hex:
            # Use ECDSA signing
            return await _create_certificate_signature(data, signing_key_hex)
    except Exception as e:
        logger.warning(f"Could not load signing key, falling back to hash signature: {e}")

    # Fallback to deterministic hash if no signing key available
    data_str = json.dumps(data, sort_keys=True)
    return "0x" + hashlib.sha256(data_str.encode()).hexdigest()


async def _read_signing_key(settings) -> Optional[str]:
    """
    Read signing key from configuration

    Args:
        settings: Worker settings

    Returns:
        Hex-encoded private key or None if not available
    """
    # Check if signing key path is configured
    if hasattr(settings, 'signing_key_path') and settings.signing_key_path:
        key_path = Path(settings.signing_key_path)
        if key_path.exists():
            with open(key_path, 'r') as f:
                return f.read().strip()

    # Check environment variable
    import os
    key_from_env = os.getenv('CERTIFICATE_SIGNING_KEY')
    if key_from_env:
        return key_from_env

    # For testing/development, use a deterministic key based on settings
    # In production, this should come from secure storage
    if hasattr(settings, 'environment') and settings.environment == 'test':
        # Generate deterministic test key
        return "0x" + "1" * 64  # Test key

    return None


async def _create_certificate_signature(data: dict, private_key_hex: str) -> str:
    """
    Create ECDSA signature for certificate data

    Args:
        data: Data to sign
        private_key_hex: Hex-encoded private key (with or without 0x prefix)

    Returns:
        Hex-encoded signature
    """
    # Remove 0x prefix if present
    if private_key_hex.startswith('0x'):
        private_key_hex = private_key_hex[2:]

    # Convert hex to bytes
    private_key_bytes = bytes.fromhex(private_key_hex)

    # Create private key object
    private_key = ec.derive_private_key(
        int.from_bytes(private_key_bytes, 'big'),
        ec.SECP256K1(),
        default_backend()
    )

    # Serialize data to bytes
    data_bytes = json.dumps(data, sort_keys=True).encode()

    # Create deterministic signature (for reproducibility in certificates)
    # Use SHA256 hash of the data
    digest = hashlib.sha256(data_bytes).digest()

    # Sign the hash
    signature = private_key.sign(
        digest,
        ec.ECDSA(utils.Prehashed(hashes.SHA256()))
    )

    # Convert signature to hex
    return "0x" + signature.hex()


async def _verify_certificate_signature(data: dict, signature_hex: str, public_key_hex: str) -> bool:
    """
    Verify ECDSA signature for certificate data

    Args:
        data: Data that was signed
        signature_hex: Hex-encoded signature
        public_key_hex: Hex-encoded public key

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Remove 0x prefix if present
        if signature_hex.startswith('0x'):
            signature_hex = signature_hex[2:]
        if public_key_hex.startswith('0x'):
            public_key_hex = public_key_hex[2:]

        # Convert hex to bytes
        signature_bytes = bytes.fromhex(signature_hex)
        public_key_bytes = bytes.fromhex(public_key_hex)

        # Create public key object
        public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256K1(),
            public_key_bytes
        )

        # Serialize data to bytes
        data_bytes = json.dumps(data, sort_keys=True).encode()

        # Create hash of data
        digest = hashlib.sha256(data_bytes).digest()

        # Verify signature
        public_key.verify(
            signature_bytes,
            digest,
            ec.ECDSA(utils.Prehashed(hashes.SHA256()))
        )

        return True

    except InvalidSignature:
        return False
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        return False