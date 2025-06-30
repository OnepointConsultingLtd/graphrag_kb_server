from pathlib import Path
from graphrag_kb_server.utils.cache import PersistentSimpleCache


def test_persistent_simple_cache():
    cache = PersistentSimpleCache("test")
    data = {"test": "test"}
    project_dir = Path(".")
    cache.set(project_dir, data)
    assert data == cache.get(project_dir)
    cache.clear(project_dir)
    cache_path = Path("./cache")
    if cache_path.exists():
        cache_path.rmdir()