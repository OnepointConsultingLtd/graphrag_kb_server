import sys
from pathlib import Path
import base64


def get_creation_time(path: Path) -> float:
    """
    Returns the creation time of the file or directory:
    - On Windows: uses st_birthtime.
    - On Linux: falls back to st_ctime or earliest mtime within the directory.
    """
    stat = path.stat()

    # Windows: st_birthtime is available
    if hasattr(stat, "st_birthtime"):
        return stat.st_birthtime

    # Linux: Fallback options
    if sys.platform.startswith("linux"):
        # Option 1: Use st_ctime (metadata change time)
        # return stat.st_ctime

        # Option 2: Use the earliest mtime from files inside the directory
        mtimes = [f.stat().st_mtime for f in path.glob("**/*") if f.is_file()]
        return min(mtimes) if mtimes else stat.st_mtime

    # For other platforms, use st_ctime as a fallback
    return stat.st_ctime


def write_uploaded_file(content: bytes, uploaded_file: Path) -> Path:
    if uploaded_file.exists():
        uploaded_file.unlink()
        uploaded_file.touch()
    with open(uploaded_file, "wb") as f:
        f.write(base64.b64decode(content))
    return uploaded_file
