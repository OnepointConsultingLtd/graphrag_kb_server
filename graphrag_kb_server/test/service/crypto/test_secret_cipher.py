import pytest
from cryptography.fernet import Fernet

from graphrag_kb_server.service.crypto.secret_cipher import (
    ENCRYPTION_KEY_ENV_VARIABLE,
    SecretCipherError,
    decrypt_secret,
    encrypt_secret,
    generate_encryption_key,
    mask_secret,
)


@pytest.fixture
def encryption_key(monkeypatch) -> str:
    key = generate_encryption_key()
    monkeypatch.setenv(ENCRYPTION_KEY_ENV_VARIABLE, key)
    return key


def test_generated_key_is_valid_fernet_key():
    Fernet(generate_encryption_key().encode("ascii"))


def test_round_trip(encryption_key):
    token = encrypt_secret("sk-secret-value")
    assert token != "sk-secret-value"
    assert decrypt_secret(token) == "sk-secret-value"


def test_encryption_is_not_deterministic(encryption_key):
    assert encrypt_secret("same") != encrypt_secret("same")


def test_decrypt_with_wrong_key_fails(encryption_key, monkeypatch):
    token = encrypt_secret("sk-secret-value")
    monkeypatch.setenv(ENCRYPTION_KEY_ENV_VARIABLE, generate_encryption_key())
    with pytest.raises(SecretCipherError):
        decrypt_secret(token)


def test_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv(ENCRYPTION_KEY_ENV_VARIABLE, raising=False)
    with pytest.raises(SecretCipherError, match=ENCRYPTION_KEY_ENV_VARIABLE):
        encrypt_secret("x")
    with pytest.raises(SecretCipherError, match=ENCRYPTION_KEY_ENV_VARIABLE):
        decrypt_secret("x")


def test_invalid_key_raises_clear_error(monkeypatch):
    monkeypatch.setenv(ENCRYPTION_KEY_ENV_VARIABLE, "not-a-fernet-key")
    with pytest.raises(SecretCipherError, match="valid Fernet key"):
        encrypt_secret("x")


def test_mask_secret_reveals_only_last_characters():
    assert mask_secret("sk-1234567890abcd") == "*" * 13 + "abcd"


def test_mask_short_secret_is_fully_hidden():
    assert mask_secret("short") == "*****"
    assert mask_secret("") == ""
