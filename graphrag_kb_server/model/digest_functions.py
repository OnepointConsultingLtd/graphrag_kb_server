import hashlib
from pathlib import Path
from binascii import unhexlify


def content_sha256_combined(user_profile: str, project_dir: Path) -> tuple[str, bytes]:
    content = f"{user_profile}\n{project_dir.as_posix()}"
    return content_sha256(content)


def content_sha256(user_profile: str) -> tuple[str, bytes]:
    """Return a (hex_digest, bytes_digest) tuple hashed from the user_profile string."""
    digest = hashlib.sha256(user_profile.encode("utf-8")).hexdigest()
    return digest, unhexlify(digest)
