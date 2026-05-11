from pydantic import BaseModel


class DocumentChunk(BaseModel):
    document_path: str
    chunk_content: str
    chunk_id: str
    project_id: int
