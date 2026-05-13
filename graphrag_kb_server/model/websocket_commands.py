from enum import StrEnum

class Command(StrEnum):
    START_SESSION = "start_session"
    PROGRESS = "progress"
    RESPONSE = "response"
    BUILD_CONTEXT = "build_context"
    ERROR = "error"
    STREAM_START = "stream_start"
    STREAM_TOKEN = "stream_token"
    STREAM_END = "stream_end"
    EXTRACT_PROFILE_STREAM = "extract_profile_stream"
    EXTRACT_PROFILE_STREAM_END = "extract_profile_stream_end"
    EXTRACT_PROFILE_STREAM_ERROR = "extract_profile_stream_error"
    DOCUMENT_TRENDINESS = "document_trendiness"
    DOCUMENT_TRENDINESS_END = "document_trendiness_end"
    DOCUMENT_TRENDINESS_ERROR = "document_trendiness_error"