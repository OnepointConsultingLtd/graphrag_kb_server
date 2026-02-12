from enum import StrEnum
import os
from pathlib import Path
import random

from dotenv import load_dotenv
from graphrag_kb_server.logger import logger

load_dotenv()


def create_if_not_exists(path: Path):
    if not Path(path).exists():
        path.mkdir(parents=True)


class Config:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key is None:
        logger.warning("OPENAI_API_KEY is not set, using empty string.")
        openai_api_key = ""

    openai_api_model = os.getenv("OPENAI_API_MODEL")
    assert (
        openai_api_model is not None
    ), "Please specify the OPENAI_API_MODEL environment variable."

    openai_api_model_embedding = os.getenv("OPENAI_API_MODEL_EMBEDDING")
    assert (
        openai_api_model_embedding is not None
    ), "Please specify the OPENAI_API_MODEL_EMBEDDING environment variable."

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    # This is optional, only used by LightRAG
    assert (
        gemini_api_key is not None
    ), "Please specify the GEMINI_API_KEY environment variable."

    togetherai_api_key = os.getenv("TOGETHERAI_API_KEY")
    assert (
        togetherai_api_key is not None
    ), "Please specify the TOGETHERAI_API_KEY environment variable."
    togetherai_model = os.getenv("TOGETHERAI_MODEL")
    assert (
        togetherai_model is not None
    ), "Please specify the TOGETHERAI_MODEL environment variable."

    config_dir = Path(__file__).parent.parent / "config"
    assert config_dir.exists(), "The configuration directory with Swagger files does not exist"

    graphrag_root_dir = os.getenv("GRAPHRAG_ROOT_DIR")
    assert graphrag_root_dir is not None, "Please specify the Graphrag root directory."
    graphrag_root_dir_path = Path(graphrag_root_dir)
    create_if_not_exists(graphrag_root_dir_path)

    vector_db_dir = os.getenv("VECTOR_DB_DIR")
    assert vector_db_dir is not None, "Please specify the vector database directory."

    claim_extraction_prompt_file = os.getenv("CLAIM_EXTRACTION_PROMPT_FILE")

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

    server_base_url = os.getenv("SERVER_BASE_URL")
    assert server_base_url is not None, "Please specify the server base URL"

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    assert openrouter_api_key is not None, "Please specify the OpenRouter API key"
    openrouter_model = os.getenv("OPENROUTER_MODEL")
    assert openrouter_model is not None, "Please specify the OpenRouter model"
    openrouter_model_embedding = os.getenv("OPENROUTER_MODEL_EMBEDDING")
    assert openrouter_model_embedding is not None, "Please specify the OpenRouter model embedding"
    openrouter_provider = os.getenv("OPENROUTER_PROVIDER")  # Optional: specify provider (e.g., "openai", "anthropic", "mistral")


class WebsocketConfig:
    websocket_server = os.getenv("SERVER")
    assert websocket_server is not None, "Please specify the websocket server"
    websocket_port_str = os.getenv("PORT")
    assert websocket_server is not None, "Please specify the websocket port"
    websocket_port = int(websocket_port_str)
    websocket_cors_allowed_origins = os.getenv("WEBSOCKET_CORS_ALLOWED_ORIGINS", "*")


class JWTConfig:
    secret = os.getenv("JWT_SECRET")
    assert secret is not None, "Cannot find JWT secret"
    algorithm = os.getenv("JWT_ALGORITHM")
    assert algorithm is not None, "Cannot find JWT algorithm. Please specify one"
    timedelta_minutes = os.getenv("JWT_TIME_DELTA_MINUTES")
    assert timedelta_minutes is not None, "No time delta in minutes available"
    timedelta_minutes = int(timedelta_minutes)
    admin_jwt: str = ""
    admin_token_name = os.getenv("ADMIN_TOKEN_NAME")
    assert admin_token_name is not None, "Cannot find admin token name"
    admin_token_email = os.getenv("ADMIN_TOKEN_EMAIL")
    assert admin_token_email is not None, "Cannot find admin token email"
    admin_token_password = os.getenv("ADMIN_TOKEN_PASSWORD")
    assert admin_token_password is not None, "Cannot find admin token password"


cfg = Config()


class AdminConfig:

    def __init__(self) -> None:
        self._administrators = []
        self._loading = False

    async def get_administrators(self) -> list[str]:
        from graphrag_kb_server.service.db.db_persistence_admin_user import select_admin_emails
        
        return await select_admin_emails()


class LightRAGModelType(StrEnum):
    GOOGLE = "google"
    OPENAI = "openai"
    TOGETHERAI = "togetherai"
    OPENROUTER = "openrouter"


class LightRAGConfig:
    lightrag_model = os.getenv("LIGHTRAG_MODEL")
    assert lightrag_model is not None, "Please specify the LightRAG model"
    lightrag_lite_model = os.getenv("LIGHTRAG_LITE_MODEL")
    assert lightrag_lite_model is not None, "Please specify the LightRAG quick model"
    lightrag_model_type = os.getenv("LIGHTRAG_MODEL_TYPE", "google")
    assert lightrag_model_type is not None, "Please specify the LightRAG model type"
    assert lightrag_model_type in [m.value for m in LightRAGModelType], "Invalid LightRAG model type"


class LinkedInConfig:
    linkedin_credentials: dict[str, str] = {}
    linkedin_searches: list[str] = []
    for key, value in os.environ.items():
        if key.startswith("LINKEDIN_USER_"):
            cred_number = key[len("LINKEDIN_USER_") :]
            linkedin_credentials[os.getenv(f"{key}")] = os.getenv(
                f"LINKEDIN_PASSWORD_{cred_number}"
            )
        if key.startswith("LINKEDIN_SEARCH_"):
            linkedin_searches.append(os.getenv(key))
    linkedin_credentials_list = list(linkedin_credentials.items())

    def get_random_credential(self) -> tuple[str, str]:
        cred_index = random.randint(0, len(linkedin_cfg.linkedin_credentials_list) - 1)
        user, password = linkedin_cfg.linkedin_credentials_list[cred_index]
        return user, password


class BrightDataConfig:
    bright_data_api_key = os.getenv("BRIGHT_DATA_API_KEY")
    assert bright_data_api_key is not None, "Please specify the Bright Data API key"


class DBConfig:
    postgres_connection_string = os.getenv("POSTGRES_CONNECTION_STRING")
    assert (
        postgres_connection_string is not None
    ), "Please specify the PostgreSQL connection string"
    postgres_connection_pool_min_size = int(
        os.getenv("POSTGRES_CONNECTION_POOL_MIN_SIZE", "1")
    )
    assert (
        postgres_connection_pool_min_size is not None
    ), "Please specify the PostgreSQL connection pool minimum size"
    postgres_connection_pool_max_size = int(
        os.getenv("POSTGRES_CONNECTION_POOL_MAX_SIZE", "10")
    )
    assert (
        postgres_connection_pool_max_size is not None
    ), "Please specify the PostgreSQL connection pool maximum size"


websocket_cfg = WebsocketConfig()

jwt_cfg = JWTConfig()

lightrag_cfg = LightRAGConfig()

linkedin_cfg = LinkedInConfig()

bright_data_cfg = BrightDataConfig()

db_cfg = DBConfig()

admin_cfg = AdminConfig()
