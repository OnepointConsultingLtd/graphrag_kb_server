from pathlib import Path
import time
import pickle
from typing import TypeVar, Generic, Dict, Any

from graphrag.query.structured_search.local_search.search import LocalSearch

T = TypeVar("T")


class GenericProjectSimpleCache(Generic[T]):

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


local_search_mixed_context_cache = GenericProjectSimpleCache[LocalSearch]()


class PersistentSimpleCache(Generic[T]):

    def __init__(self, key: str):
        self.key = key

    def _get_cache_file(self, project_dir: Path) -> Path:
        cache_location = project_dir / "cache"
        if not cache_location.exists():
            cache_location.mkdir(parents=True, exist_ok=True)
        return cache_location / f"{self.key}.pkl"

    def get(self, project_dir: Path) -> T | None:
        cache_file = self._get_cache_file(project_dir)
        if cache_file.exists():
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        return None

    def set(self, project_dir: Path, value: T):
        cache_file = self._get_cache_file(project_dir)
        with open(cache_file, "wb") as f:
            pickle.dump(value, f)

    def clear(self, project_dir: Path):
        cache_file = self._get_cache_file(project_dir)
        if cache_file.exists():
            cache_file.unlink()
