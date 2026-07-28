import os
from cryptography.fernet import Fernet

# Resolve secret key file location in the backend folder
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(CURRENT_DIR, "secret.key")

try:
    from backend.config import settings
except ImportError:
    from config import settings

# Determine Fernet key
ENCRYPTION_KEY = settings.ENCRYPTION_KEY

if not ENCRYPTION_KEY:
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as kf:
            ENCRYPTION_KEY = kf.read().decode('utf-8')
    else:
        # Generate new Fernet key
        new_key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as kf:
            kf.write(new_key)
        ENCRYPTION_KEY = new_key.decode('utf-8')

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
