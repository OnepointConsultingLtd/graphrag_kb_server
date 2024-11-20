from pathlib import Path
from pydantic import BaseModel, Field


class ContextParameters(BaseModel):
    query: str = Field(description="The query fpr which the context is retrieved.")
    project_dir: Path = Field(description="The path of the project.")
    context_size: int = Field(description="The context size in tokens.")
