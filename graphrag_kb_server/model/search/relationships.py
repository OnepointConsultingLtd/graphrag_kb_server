from pydantic import BaseModel

class RelationshipsJSON(BaseModel):
    relationships: str
    search_id: int