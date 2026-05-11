from graphrag_kb_server.model.document_chunk import DocumentChunk
from graphrag_kb_server.service.db.connection_pool import (
    execute_query,
    fetch_all,
    init_pool,
)


TB_DOCUMENT_CHUNKS = "TB_DOCUMENT_CHUNKS"


async def create_document_chunks_table(schema_name: str):
    await execute_query(
        f"""
CREATE TABLE IF NOT EXISTS {schema_name}.{TB_DOCUMENT_CHUNKS} (
    ID            SERIAL       NOT NULL,
    PROJECT_ID    INTEGER      NOT NULL,
    DOCUMENT_PATH TEXT         NOT NULL,
    CHUNK_CONTENT TEXT         NOT NULL,
    CHUNK_ID      VARCHAR(256) NOT NULL,
    CREATED_AT    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ID),
    UNIQUE (DOCUMENT_PATH, PROJECT_ID),
    CONSTRAINT PROJECT_ID_FK
        FOREIGN KEY (PROJECT_ID) REFERENCES {schema_name}.TB_PROJECTS (ID)
        MATCH SIMPLE ON UPDATE NO ACTION ON DELETE CASCADE
);
"""
    )


async def drop_document_chunks_table(schema_name: str):
    await execute_query(
        f"""
DROP TABLE IF EXISTS {schema_name}.{TB_DOCUMENT_CHUNKS};
"""
    )


async def insert_document_chunk(schema_name: str, chunk: DocumentChunk):
    """Insert a document chunk, silently ignoring duplicates on (DOCUMENT_PATH, PROJECT_ID)."""
    pool = await init_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f"""
INSERT INTO {schema_name}.{TB_DOCUMENT_CHUNKS} (DOCUMENT_PATH, CHUNK_CONTENT, CHUNK_ID, PROJECT_ID)
VALUES ($1, $2, $3, $4)
ON CONFLICT (DOCUMENT_PATH, PROJECT_ID) DO NOTHING;
""",
            chunk.document_path,
            chunk.chunk_content,
            chunk.chunk_id,
            chunk.project_id,
        )


async def get_document_chunks_by_path(
    schema_name: str, document_path: str, project_id: int
) -> list[DocumentChunk]:
    """Return all stored chunks for a given document path and project."""
    rows = await fetch_all(
        f"""
SELECT DOCUMENT_PATH, CHUNK_CONTENT, CHUNK_ID, PROJECT_ID
FROM {schema_name}.{TB_DOCUMENT_CHUNKS}
WHERE DOCUMENT_PATH = $1 AND PROJECT_ID = $2;
""",
        document_path,
        project_id,
    )
    return [
        DocumentChunk(
            document_path=row["document_path"],
            chunk_content=row["chunk_content"],
            chunk_id=row["chunk_id"],
            project_id=row["project_id"],
        )
        for row in rows
    ]


async def get_stored_document_paths(schema_name: str, project_id: int) -> set[str]:
    """Return the set of document paths that already have a stored chunk for this project."""
    rows = await fetch_all(
        f"""
SELECT DOCUMENT_PATH
FROM {schema_name}.{TB_DOCUMENT_CHUNKS}
WHERE PROJECT_ID = $1;
""",
        project_id,
    )
    return {row["document_path"] for row in rows}
