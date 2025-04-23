from pathlib import Path
import time

from graphrag.query.structured_search.local_search.search import LocalSearch

class LocalSearchMixedContextCache():

    def __init__(self, timeout: int = 3600):
        self.cache = {}
        self.timeout = timeout

    def get(self, project_dir: Path) -> LocalSearch:
        posix_path = project_dir.as_posix()
        if posix_path in self.cache:
            entry = self.cache[posix_path]
            if time.time() - entry["timestamp"] < self.timeout:
                return entry["local_search"]
            else:
                del self.cache[posix_path]
        return None
    
    def set(self, project_dir: Path, local_search: LocalSearch):
        self.cache[project_dir.as_posix()] = {"local_search": local_search, "timestamp": time.time()}


local_search_mixed_context_cache = LocalSearchMixedContextCache()