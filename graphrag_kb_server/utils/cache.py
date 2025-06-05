from pathlib import Path
import time
from typing import TypeVar, Generic, Dict, Any

from graphrag.query.structured_search.local_search.search import LocalSearch

T = TypeVar("T")


class GenericSimpleCache(Generic[T]):

    def __init__(self, timeout: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.timeout = timeout

    def get(self, project_dir: Path) -> T | None:
        posix_path = project_dir.as_posix()
        if posix_path in self.cache:
            entry = self.cache[posix_path]
            if time.time() - entry["timestamp"] < self.timeout:
                return entry["value"]
            else:
                # Delete entry if it has expired
                del self.cache[posix_path]
        return None

    def set(self, project_dir: Path, value: T):
        self.cache[project_dir.as_posix()] = {
            "value": value,
            "timestamp": time.time(),
        }


local_search_mixed_context_cache = GenericSimpleCache[LocalSearch]()
