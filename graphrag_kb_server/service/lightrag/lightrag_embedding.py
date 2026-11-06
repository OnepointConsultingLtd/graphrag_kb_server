"""Builds the LightRAG embedding function of a project from its configuration.

The embedding model decides the dimension of the stored vectors, so it must not change once a
project has been indexed. The dimension therefore has to be known up front: models missing from
EMBEDDING_DIMENSIONS are rejected instead of silently producing a dimension mismatch.
"""

from functools import partial
from pathlib import Path

from lightrag.llm.openai import openai_embed
from lightrag.utils import EmbeddingFunc

from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER
from graphrag_kb_server.service.project_config_service import ProjectConfig

# The model LightRAG's openai_embed uses when nothing else is configured.
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

EMBEDDING_MAX_TOKEN_SIZE = 8192

# Output dimension of the supported OpenAI embedding models.
EMBEDDING_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


def get_embedding_dimension(model: str) -> int:
    """Return the vector dimension of an embedding model, or raise ValueError if unsupported."""
    dimension = EMBEDDING_DIMENSIONS.get(model)
    if dimension is None:
        raise ValueError(
            f"Unsupported embedding model '{model}'. Supported models: "
            f"{', '.join(sorted(EMBEDDING_DIMENSIONS))}"
        )
    return dimension


def build_embedding_func(config: ProjectConfig) -> EmbeddingFunc:
    """Create the embedding function using the project's OpenAI key and embedding model."""
    model = config.openai_api_model_embedding or DEFAULT_EMBEDDING_MODEL
    return EmbeddingFunc(
        embedding_dim=get_embedding_dimension(model),
        # .func is the unwrapped function: wrapping the EmbeddingFunc again would double wrap it.
        func=partial(
            openai_embed.func,
            model=model,
            # An empty key means "not configured": let the SDK fall back to its own lookup.
            api_key=config.openai_api_key or None,
        ),
        max_token_size=EMBEDDING_MAX_TOKEN_SIZE,
        model_name=model,
    )


def project_has_vectors(project_dir: Path) -> bool:
    """Whether the LightRAG vector storage of the project already exists, which fixes the
    embedding model (and with it the vector dimension) of the project."""
    storage_folder = project_dir / LIGHTRAG_FOLDER
    return storage_folder.is_dir() and any(storage_folder.glob("vdb_*.json"))
