from pathlib import Path
from graphrag_kb_server.utils.cache import local_search_mixed_context_cache
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag_kb_server.config import cfg


def test_cache():
    project_dir = Path("test_project")
    local_search = LocalSearch(model=cfg.llm, context_builder=None)
    local_search_mixed_context_cache.set(project_dir, local_search)
    assert local_search_mixed_context_cache.get(project_dir) == local_search
