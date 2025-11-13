import re
import bcrypt

BCRYPT_ROUNDS = 12


def validate_email(email: str) -> bool:
    # Basic email regex pattern
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(email_regex, email) is not None


def generate_hash(password_plain: str) -> str:
    """
    Generates and sets the password_hash field based on password_plain.
    """
    password_bytes: bytes = password_plain.encode("utf-8")
    hashed_bytes: bytes = bcrypt.hashpw(
        password_bytes, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    )
    password_hash = hashed_bytes.decode("utf-8")
    return password_hash


def check_password(password_plain: str, password_hash: str) -> bool:
    """
    Verifies a plain-text password against the stored hash.
    """
    if not password_hash:
        return False

    password_bytes: bytes = password_plain.encode("utf-8")
    hash_bytes: bytes = password_hash.encode("utf-8")

    # bcrypt.checkpw automatically extracts the salt and cost from the hash
    return bcrypt.checkpw(password_bytes, hash_bytes)
