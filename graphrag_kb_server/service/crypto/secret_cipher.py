"""Symmetric encryption of secrets (API keys) stored in the database.

The master key is a Fernet key read lazily from the ``PROJECT_KEYS_ENCRYPTION_KEY``
environment variable, so the application can start without it. An error is only raised
when a secret actually has to be encrypted or decrypted.
"""

import os

from cryptography.fernet import Fernet, InvalidToken

ENCRYPTION_KEY_ENV_VARIABLE = "PROJECT_KEYS_ENCRYPTION_KEY"
_MASK_VISIBLE_CHARACTERS = 4


class SecretCipherError(Exception):
    """Raised when a secret cannot be encrypted or decrypted."""


def generate_encryption_key() -> str:
    """Generate a new Fernet key (url-safe base64, 44 characters)."""
    return Fernet.generate_key().decode("ascii")


def _get_fernet() -> Fernet:
    """Build a Fernet instance from the environment, failing with a clear message."""
    key = os.getenv(ENCRYPTION_KEY_ENV_VARIABLE)
    if not key:
        raise SecretCipherError(
            f"{ENCRYPTION_KEY_ENV_VARIABLE} is not set. Generate one with "
            "'python graphrag_kb_server/cli/project_keys_main.py generate-key'."
        )
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError) as error:
        raise SecretCipherError(
            f"{ENCRYPTION_KEY_ENV_VARIABLE} is not a valid Fernet key."
        ) from error


def encrypt_secret(plain_text: str) -> str:
    """Encrypt a secret and return the ciphertext as a string."""
    return _get_fernet().encrypt(plain_text.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str) -> str:
    """Decrypt ciphertext produced by :func:`encrypt_secret`."""
    try:
        return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as error:
        raise SecretCipherError(
            "Cannot decrypt the secret: wrong encryption key or corrupted data."
        ) from error


def mask_secret(plain_text: str) -> str:
    """Return a display-safe version of a secret that only reveals its last characters."""
    if len(plain_text) <= _MASK_VISIBLE_CHARACTERS * 2:
        return "*" * len(plain_text)
    hidden_length = len(plain_text) - _MASK_VISIBLE_CHARACTERS
    return "*" * hidden_length + plain_text[-_MASK_VISIBLE_CHARACTERS:]
