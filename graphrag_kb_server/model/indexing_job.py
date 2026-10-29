from datetime import datetime

from pydantic import BaseModel, Field, field_serializer

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project import IndexingStatus


FINISHED_INDEXING_STATUSES = frozenset(
    {IndexingStatus.COMPLETED, IndexingStatus.FAILED}
)


class IndexingJob(BaseModel):
    job_id: str = Field(..., description="The unique identifier of the indexing job")
    tennant: str = Field(
        ..., description="The tennant which submitted the job", exclude=True
    )
    project: str = Field(..., description="The name of the project being indexed")
    engine: Engine = Field(..., description="The engine used to index the files")
    file_names: list[str] = Field(..., description="The names of the uploaded files")
    status: IndexingStatus = Field(
        default=IndexingStatus.NOT_STARTED, description="The status of the indexing job"
    )
    message: str | None = Field(
        default=None, description="A human readable description of the job progress"
    )
    error: str | None = Field(
        default=None, description="The error message if the indexing job failed"
    )
    created_at: datetime = Field(..., description="When the job was submitted")
    updated_at: datetime = Field(..., description="When the job status last changed")

    @property
    def is_finished(self) -> bool:
        """Whether the job reached a final status and will not change anymore."""
        return self.status in FINISHED_INDEXING_STATUSES

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, dt: datetime, _info):
        return dt.isoformat()


class IndexFilesResponse(BaseModel):
    status: str = Field(..., description="Either success or error")
    message: str = Field(..., description="A human readable description of the result")
    job_id: str | None = Field(
        default=None,
        description="The id of the indexing job for asynchronous requests, otherwise null",
    )
