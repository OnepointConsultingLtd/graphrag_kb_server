from enum import StrEnum


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
