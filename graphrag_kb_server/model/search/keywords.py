from enum import StrEnum
from pydantic import BaseModel


class KeywordType(StrEnum):
    HIGH_LEVEL = "high"
    LOW_LEVEL = "low"


class Keywords(BaseModel):
    keywords: list[str]
    keyword_type: KeywordType
    search_id: int
