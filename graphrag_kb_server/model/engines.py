from enum import StrEnum
from aiohttp.web import Request
from graphrag_kb_server.model.web_format import Format


class Engine(StrEnum):
    GRAPHRAG = "graphrag"
    LIGHTRAG = "lightrag"


def find_engine(engine: str) -> Engine:
    if engine == Engine.GRAPHRAG:
        return Engine.GRAPHRAG
    elif engine == Engine.LIGHTRAG:
        return Engine.LIGHTRAG
    else:
        raise ValueError(f"Invalid engine: {engine}")
    

def find_engine_from_query(request: Request) -> Engine:
    engine_str = request.rel_url.query.get("engine", Format.JSON.value)
    return find_engine(engine_str)