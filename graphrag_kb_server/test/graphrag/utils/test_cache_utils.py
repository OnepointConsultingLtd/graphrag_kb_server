from pathlib import Path
from graphrag_kb_server.utils.cache import GenericSimpleCache, PersistentSimpleCache


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


def test_generic_simple_cache_invalidate_removes_only_that_key():
    cache: GenericSimpleCache[str, str] = GenericSimpleCache(timeout=60)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.invalidate("a")
    assert cache.get("a") is None
    assert cache.get("b") == "2"


def test_generic_simple_cache_invalidate_unknown_key_is_noop():
    cache: GenericSimpleCache[str, str] = GenericSimpleCache(timeout=60)
    cache.invalidate("missing")
    assert cache.get("missing") is None


def test_generic_simple_cache_clear_removes_everything():
    cache: GenericSimpleCache[str, str] = GenericSimpleCache(timeout=60)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None
