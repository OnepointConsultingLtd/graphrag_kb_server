import os
import yaml
import shutil
from pathlib import Path
import random

from dotenv import load_dotenv
from graphrag_kb_server.logger import logger
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.config.enums import ModelType

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
    logger.info(f"Using model {openai_api_model}")

    openai_api_model_embedding = os.getenv("OPENAI_API_MODEL_EMBEDDING")
    assert (
        openai_api_model_embedding is not None
    ), "Please specify the OPENAI_API_MODEL_EMBEDDING environment variable."

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    # This is optional, only used by LightRAG

    config_dir_str = os.getenv("CONFIG_DIR")
    assert config_dir_str is not None, "The configuration directory with Swagger files"
    config_dir = Path(config_dir_str)
    create_if_not_exists(config_dir)

    graphrag_root_dir = os.getenv("GRAPHRAG_ROOT_DIR")
    assert graphrag_root_dir is not None, "Please specify the Graphrag root directory."
    graphrag_root_dir_path = Path(graphrag_root_dir)
    create_if_not_exists(graphrag_root_dir_path)

    vector_db_dir = os.getenv("VECTOR_DB_DIR")
    assert vector_db_dir is not None, "Please specify the vector database directory."

    claim_extraction_prompt_file = os.getenv("CLAIM_EXTRACTION_PROMPT_FILE")

    llm_config = LanguageModelConfig(
        api_key=openai_api_key,
        model=openai_api_model,
        type=ModelType.OpenAIChat,
    )
    embedding_llm_config = LanguageModelConfig(
        api_key=openai_api_key,
        model=openai_api_model_embedding,
        type=ModelType.OpenAIEmbedding,
    )
    from graphrag.language_model.factory import ModelFactory

    llm = ModelFactory.create_chat_model(
        name="openai-model", model_type=ModelType.OpenAIChat, config=llm_config
    )
    embedding_llm = ModelFactory.create_embedding_model(
        name="openai-embedding-model",
        model_type=ModelType.OpenAIEmbedding,
        config=embedding_llm_config,
    )
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
    admins = cfg.config_dir / "administration.yaml"
    if not admins.exists():
        if (cfg.config_dir / "administration_local.yaml").exists():
            shutil.copyfile(cfg.config_dir / "administration_local.yaml", admins)
    if admins.exists():
        yaml_text = admins.read_text()
        content = yaml.safe_load(yaml_text)
        administrators = content["administrators"]
    else:
        administrators = []


class LightRAGConfig:
    lightrag_model = os.getenv("LIGHTRAG_MODEL")
    assert lightrag_model is not None, "Please specify the LightRAG model"
    lightrag_lite_model = os.getenv("LIGHTRAG_LITE_MODEL")
    assert lightrag_lite_model is not None, "Please specify the LightRAG quick model"


class LinkedInConfig:
    linkedin_credentials: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith("LINKEDIN_USER_"):
            cred_number = key[len("LINKEDIN_USER_") :]
            linkedin_credentials[os.getenv(f"{key}")] = os.getenv(
                f"LINKEDIN_PASSWORD_{cred_number}"
            )
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

admin_cfg = AdminConfig()

lightrag_cfg = LightRAGConfig()

linkedin_cfg = LinkedInConfig()

bright_data_cfg = BrightDataConfig()

db_cfg = DBConfig()
