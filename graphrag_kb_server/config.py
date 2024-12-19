import os
from pathlib import Path

from dotenv import load_dotenv
from graphrag_kb_server.logger import logger
from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.typing import OpenaiApiType

load_dotenv()


class Config:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    assert (
        openai_api_key is not None
    ), "Please specify the OPENAI_API_KEY environment variable."

    openai_api_model = os.getenv("OPENAI_API_MODEL")
    assert (
        openai_api_model is not None
    ), "Please specify the OPENAI_API_MODEL environment variable."
    logger.info(f"Using model {openai_api_model}")

    openai_api_model_embedding = os.getenv("OPENAI_API_MODEL_EMBEDDING")
    assert (
        openai_api_model_embedding is not None
    ), "Please specify the OPENAI_API_MODEL_EMBEDDING environment variable."

    docs_dir = os.getenv("DOCS_DIR")
    assert (
        docs_dir is not None
    ), "The document directory is not available. Please specify it using the DOCS_DIR environment variable."
    docs_dir_path = Path(docs_dir)
    assert docs_dir_path.exists(), "The path with the documents does not exist."

    graphrag_root_dir = os.getenv("GRAPHRAG_ROOT_DIR")
    assert graphrag_root_dir is not None, "Please specify the Graphrag root directory."
    graphrag_root_dir_path = Path(graphrag_root_dir)
    if not Path(graphrag_root_dir_path).exists():
        graphrag_root_dir_path.mkdir(parents=True)

    storage_base_dir = os.getenv("STORAGE_BASE_DIR")
    assert storage_base_dir is not None, "Please specify the storage base directory."

    vector_db_dir = os.getenv("VECTOR_DB_DIR")
    assert vector_db_dir is not None, "Please specify the vector database directory."

    claim_extraction_prompt_file = os.getenv("CLAIM_EXTRACTION_PROMPT_FILE")

    llm = ChatOpenAI(
        api_key=openai_api_key,
        model=openai_api_model,
        api_type=OpenaiApiType.OpenAI,  # OpenaiApiType.OpenAI or OpenaiApiType.AzureOpenAI
        max_retries=20,
    )

    graphrag_exe = os.getenv("GRAPHRAG_EXE")
    index_verbose = os.getenv("INDEX_VERBOSE") == "true"

    claims_enabled = os.getenv("CLAIMS_ENABLED") == "true"

    local_context_max_tokens_str = os.getenv("LOCAL_CONTEXT_MAX_TOKENS", "20000")
    local_context_max_tokens = int(local_context_max_tokens_str)

    global_context_max_tokens_str = os.getenv("GLOBAL_CONTEXT_MAX_TOKENS", "20000")
    global_context_max_tokens = int(global_context_max_tokens_str)

    upload_dir_str = os.getenv("UPLOAD_DIR")
    assert upload_dir_str is not None
    upload_dir = Path(upload_dir_str)
    if not upload_dir.exists():
        upload_dir.mkdir(parents=True)

    upload_secret = os.getenv("UPLOAD_SECRET")
    assert upload_secret is not None, "Please specify the upload secret."


class WebsocketConfig:
    websocket_server = os.getenv("SERVER")
    assert websocket_server is not None, "Please specify the websocket server"
    websocket_port_str = os.getenv("PORT")
    assert websocket_server is not None, "Please specify the websocket port"
    websocket_port = int(websocket_port_str)


class JWTConfig():
    secret = os.getenv("JWT_SECRET")
    assert secret is not None, "Cannot find JWT secret"
    algorithm = os.getenv("JWT_ALGORITHM")
    assert algorithm is not None, "Cannot find JWT algorithm. Please specify one"
    timedelta_minutes = os.getenv("JWT_TIME_DELTA_MINUTES")
    assert timedelta_minutes is not None, "No time delta in minutes available"
    timedelta_minutes = int(timedelta_minutes)


cfg = Config()

websocket_cfg = WebsocketConfig()

jwt_cfg = JWTConfig()
