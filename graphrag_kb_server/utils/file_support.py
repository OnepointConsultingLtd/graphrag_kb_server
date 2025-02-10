from pathlib import Path
import base64


def write_uploaded_file(content: bytes, uploaded_file: Path) -> Path:
    if uploaded_file.exists():
        uploaded_file.unlink()
        uploaded_file.touch()
    with open(uploaded_file, "wb") as f:
        f.write(base64.b64decode(content))
    return uploaded_file