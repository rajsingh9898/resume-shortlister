import os
from cryptography.fernet import Fernet

try:
    from backend.config import settings
except ImportError:
    from config import settings

# Determine Fernet key from environment / settings
ENCRYPTION_KEY = settings.ENCRYPTION_KEY

if not ENCRYPTION_KEY:
    # Generate fallback Fernet key in memory if omitted in environment
    ENCRYPTION_KEY = Fernet.generate_key().decode('utf-8')

# Instantiate Fernet cipher suite
cipher_suite = Fernet(ENCRYPTION_KEY.encode('utf-8'))

def encrypt_data(data: bytes) -> bytes:
    """Encrypts bytes data using Fernet symmetric encryption."""
    if not data:
        return data
    return cipher_suite.encrypt(data)

def decrypt_data(encrypted_data: bytes) -> bytes:
    """Decrypts bytes data using Fernet symmetric encryption."""
    if not encrypted_data:
        return encrypted_data
    return cipher_suite.decrypt(encrypted_data)
