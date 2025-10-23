import json
import hashlib
from typing import Any

from pydantic import BaseModel

def _normalize(value: Any) -> Any:
    """
    Return a structure that is deterministic for hashing:
    - Recurses into dicts/lists/tuples/sets
    - Sorts dict keys
    - Converts sets to sorted lists
    """
    if isinstance(value, dict):
        return {k: _normalize(value[k]) for k in sorted(value)}
    elif isinstance(value, (list, tuple)):
        # If order shouldn't matter, use: sorted(...). If order *does* matter, just recurse without sorting.
        return [_normalize(v) for v in value]  # keep order
    elif isinstance(value, set):
        return sorted(_normalize(v) for v in value)
    else:
        return value


def content_sha256(model: BaseModel) -> str:
    # Dump to plain Python types
    payload = model.model_dump(mode="json", exclude_none=True)
    # Optional: normalize nested structures
    payload = _normalize(payload)
    # Deterministic, compact JSON bytes
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()