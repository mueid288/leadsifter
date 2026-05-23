from cryptography.fernet import Fernet
from app.config import settings
import structlog

log = structlog.get_logger()

def get_fernet() -> Fernet:
    # Fernet requires a 32-byte URL-safe base64 key
    key = settings.ENCRYPTION_KEY.encode()
    return Fernet(key)

def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return get_fernet().encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception as e:
        log.error("crypto.decrypt_failed", error=str(e))
        # Graceful fallback for mock data during early local testing
        if settings.DEBUG:
            return ciphertext
        raise
