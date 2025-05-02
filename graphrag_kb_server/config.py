import os
import yaml
import shutil
from pathlib import Path

from dotenv import load_dotenv
from graphrag_kb_server.logger import logger
from graphrag.language_model.factory import ModelFactory
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.config.enums import ModelType

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

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    # This is optional, only used by LightRAG

    config_dir_str = os.getenv("CONFIG_DIR")
    assert config_dir_str is not None, "The configuration directory with Swagger files"
    config_dir = Path(config_dir_str)

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
    llm = ModelFactory.create_chat_model(
        name="openai-model", model_type=ModelType.OpenAIChat, config=llm_config
    )
    embedding_llm = ModelFactory.create_embedding_model(
        name="openai-embedding-model",
        model_type=ModelType.OpenAIEmbedding,
        config=embedding_llm_config,
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


class WebsocketConfig:
    websocket_server = os.getenv("SERVER")
    assert websocket_server is not None, "Please specify the websocket server"
    websocket_port_str = os.getenv("PORT")
    assert websocket_server is not None, "Please specify the websocket port"
    websocket_port = int(websocket_port_str)


class JWTConfig:
    secret = os.getenv("JWT_SECRET")
    assert secret is not None, "Cannot find JWT secret"
    algorithm = os.getenv("JWT_ALGORITHM")
    assert algorithm is not None, "Cannot find JWT algorithm. Please specify one"
    timedelta_minutes = os.getenv("JWT_TIME_DELTA_MINUTES")
    assert timedelta_minutes is not None, "No time delta in minutes available"
    timedelta_minutes = int(timedelta_minutes)
    admin_jwt = os.getenv("ADMIN_JWT")
    assert admin_jwt is not None, "Administration JWT is none."


cfg = Config()


class AdminConfig:
    admins = cfg.config_dir / "administration.yaml"
    if not admins.exists():
        shutil.copyfile(cfg.config_dir / "administration_local.yaml", admins)
    yaml_text = admins.read_text()
    content = yaml.safe_load(yaml_text)
    administrators = content["administrators"]


class LightRAGConfig:
    lightrag_model = os.getenv("LIGHTRAG_MODEL")
    assert lightrag_model is not None, "Please specify the LightRAG model"


websocket_cfg = WebsocketConfig()

jwt_cfg = JWTConfig()

admin_cfg = AdminConfig()

lightrag_cfg = LightRAGConfig()
if __name__ == "__main__":
    print(cfg.llm)
