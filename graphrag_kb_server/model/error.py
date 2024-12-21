from enum import IntEnum
from pydantic import BaseModel, Field


class ErrorCode(IntEnum):
    INVALID_INPUT = 1
    TENNANT_EXISTS = 100
    PROJECT_EXISTS = 101
    TENNANT_DOES_NOT_EXIST = 102


class Error(BaseModel):
    error_code: ErrorCode = Field(description="The error code")
    error: str = Field(description="The error name")
    description: str = Field(description="The description of the error")
