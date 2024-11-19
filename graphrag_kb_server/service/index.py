import shutil
import subprocess
import re

from pathlib import Path
from enum import StrEnum

from collections.abc import AsyncIterable
from graphrag.index.typing import PipelineRunResult

from graphrag.cli.index import index_cli
from graphrag.cli.initialize import initialize_project_at
from graphrag.logging import ReporterType
from graphrag.index.emit.types import TableEmitterType

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger


ROOT_DIR = Path(cfg.graphrag_root_dir)
DIR_VECTOR_DB = ROOT_DIR / cfg.vector_db_dir
INPUT_DIR = ROOT_DIR / "input"

create_folder_props = {"parents": True, "exist_ok": True}


class GenerationStatus(StrEnum):
    EXISTS = "exists"
    CREATED = "created"


def copy_files_to_root_dir() -> Path:
    kb_path = cfg.docs_dir_path
    input_path: Path = INPUT_DIR
    if not input_path.exists():
        input_path.mkdir(**create_folder_props)
    for f in kb_path.rglob("**/*.txt"):
        shutil.copy(f, input_path)
    return input_path


async def run_pipeline(pipelines: AsyncIterable[PipelineRunResult]):
    async for p in pipelines:
        logger.info(p)


def clear_rag():
    if cfg.graphrag_root_dir_path.exists():
        shutil.rmtree(cfg.graphrag_root_dir_path)
    if DIR_VECTOR_DB.exists():
        shutil.rmtree(DIR_VECTOR_DB)


def override_env(input_dir: Path):
    env = input_dir.parent / ".env"
    env_text = env.read_text()
    env_text = env_text.replace("<API_KEY>", cfg.openai_api_key)
    env.write_text(env_text)


def override_settings(root_dir: Path):
    settings = root_dir / "settings.yaml"
    settings_text = settings.read_text()
    settings_text = re.sub(
        r"(model: )text-embedding-3-small",
        r"\1" + cfg.openai_api_model_embedding,
        settings_text,
    )
    settings.write_text(settings_text)


def create_graph_rag(create_if_not_exists: bool = True) -> GenerationStatus:
    if create_if_not_exists:
        if ROOT_DIR.exists() and (ROOT_DIR / "settings.yaml").exists():
            return GenerationStatus.EXISTS
    input_dir = copy_files_to_root_dir()
    initialize_project_at(input_dir.parent)
    override_env(input_dir)
    override_settings(input_dir.parent)
    index_cli(
        root_dir=input_dir.parent,
        verbose=cfg.index_verbose,
        resume=None,
        memprofile=False,
        cache=True,
        reporter=ReporterType.RICH,
        config_filepath=None,
        emit=[TableEmitterType.Parquet, TableEmitterType.CSV],
        dry_run=False,
        skip_validation=False,
        output_dir=None,
    )
    return GenerationStatus.CREATED


def create_graph_rag_cmd() -> GenerationStatus:
    input_dir = copy_files_to_root_dir()
    executable = cfg.graphrag_exe
    subprocess.call(
        ["python", executable, "init", "--root", input_dir.parent.as_posix()]
    )

    override_env(input_dir)
    subprocess.call(
        ["python", executable, "index", "--root", input_dir.parent.as_posix()]
    )
    return GenerationStatus.CREATED
