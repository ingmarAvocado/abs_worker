"""
abs_worker - Background task processor for blockchain operations in abs_notary

This package handles asynchronous blockchain operations including:
- File hash notarization
- NFT minting with Arweave storage
- Transaction monitoring and confirmation
- Certificate generation
- Error handling with retry logic
"""

from .config import Settings, get_settings
from .notarization import process_hash_notarization, process_nft_notarization
from .monitoring import monitor_transaction, check_transaction_status
from .error_handler import handle_failed_transaction, is_retryable_error
from .certificates import generate_signed_json, generate_signed_pdf, verify_certificate

__version__ = "0.1.0"

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    # Core notarization
    "process_hash_notarization",
    "process_nft_notarization",
    # Monitoring
    "monitor_transaction",
    "check_transaction_status",
    # Error handling
    "handle_failed_transaction",
    "is_retryable_error",
    # Certificates
    "generate_signed_json",
    "generate_signed_pdf",
    "verify_certificate",
]
