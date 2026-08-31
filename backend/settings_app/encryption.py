"""
API Key encryption using Fernet (symmetric encryption).
"""
from __future__ import annotations
import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_fernet_key() -> bytes:
    """Derive a 32-byte Fernet key from Django SECRET_KEY."""
    from django.conf import settings
    secret = settings.SECRET_KEY.encode("utf-8")
    digest = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(digest)


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_derive_fernet_key())
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string. Returns plaintext."""
    if not ciphertext:
        return ciphertext
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def is_encrypted(value: str) -> bool:
    """Check if a value looks like a Fernet token."""
    if not value:
        return False
    return value.startswith("gAAAAA")
