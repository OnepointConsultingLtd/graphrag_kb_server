__all__ = ["clear_rag"]


def __getattr__(name: str):
    """Lazily expose ``clear_rag`` so importing a light submodule (e.g. the crypto helpers used by
    the CLI) does not load the whole RAG stack and the application configuration."""
    if name == "clear_rag":
        from .project import clear_rag

        return clear_rag
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
