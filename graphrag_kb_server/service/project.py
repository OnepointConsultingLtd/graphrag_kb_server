import shutil
import subprocess
import re
import yaml

from pathlib import Path
from datetime import datetime
from enum import StrEnum
from typing import Union

from collections.abc import AsyncIterable
from graphrag.index.typing import PipelineRunResult

from graphrag.cli.index import index_cli
from graphrag.cli.initialize import initialize_project_at
from graphrag.logger.factory import LoggerType

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.index_support import index
from graphrag_kb_server.model.project import Project, ProjectListing


ROOT_DIR = Path(cfg.graphrag_root_dir)
DIR_VECTOR_DB = ROOT_DIR / cfg.vector_db_dir
INPUT_DIR = ROOT_DIR / "input"

create_folder_props = {"parents": True, "exist_ok": True}


class GenerationStatus(StrEnum):
    EXISTS = "exists"
    CREATED = "created"


def copy_files_to_root_dir(kb_path: Union[Path, None]) -> Path:
    kb_path = cfg.docs_dir_path if kb_path is None else kb_path
    input_path: Path = INPUT_DIR
    if not input_path.exists():
        input_path.mkdir(**create_folder_props)
    for f in kb_path.rglob("**/*.txt"):
        shutil.copy(f, input_path)
    return input_path


async def run_pipeline(pipelines: AsyncIterable[PipelineRunResult]):
    async for p in pipelines:
        logger.info(p)


def clear_rag(rag_folder: Path) -> bool:
    deleted = False
    if rag_folder.exists():
        shutil.rmtree(rag_folder, ignore_errors=True)
        deleted = True
    return deleted


def list_projects(projects_dir: Path) -> ProjectListing:
    if not projects_dir.exists():
        return []
    projects = []
    for f in projects_dir.glob("*"):
        if (
            f.is_dir()
            and len(list(f.glob("settings.yaml"))) > 0
            and (input_files_dir := f / "input").exists()
        ):
            input_files = list([p.name for p in input_files_dir.glob("*")])
            name = f.name
            updated_timestamp = datetime.fromtimestamp(f.stat().st_mtime)
            projects.append(
                Project(
                    name=name,
                    updated_timestamp=updated_timestamp,
                    input_files=input_files,
                )
            )
    return ProjectListing(projects=projects)


def override_env(input_dir: Path):
    env = input_dir.parent / ".env"
    env_text = env.read_text()
    env_text = env_text.replace("<API_KEY>", cfg.openai_api_key)
    env.write_text(env_text)


def read_settings(root_dir):
    settings = root_dir / "settings.yaml"
    return settings, settings.read_text()


def override_settings(root_dir: Path):
    settings, settings_text = read_settings(root_dir)
    settings_text = re.sub(
        r"(model: )text-embedding-3-small",
        r"\1" + cfg.openai_api_model_embedding,
        settings_text,
    )
    settings.write_text(settings_text)


def activate_claims(project_dir: Path, enabled: bool):
    if enabled:
        settings_file, settings_text = read_settings(project_dir)
        settings = yaml.safe_load(settings_text)
        settings["claim_extraction"]["enabled"] = enabled
        with open(settings_file, "w") as f:
            yaml.safe_dump(settings, f)


def _prepare_graph_rag(kb_path: Union[Path, None]) -> Path:
    project_dir = kb_path
    input_dir = kb_path / "input"
    initialize_project_at(project_dir)
    override_env(input_dir)
    override_settings(project_dir)
    activate_claims(project_dir, cfg.claims_enabled)
    return input_dir


def prepare_index_args(root_dir: Path):
    return {
        "root_dir": root_dir,
        "verbose": cfg.index_verbose,
        "resume": None,
        "memprofile": False,
        "cache": True,
        "logger": LoggerType.RICH,
        "config_filepath": None,
        "dry_run": False,
        "skip_validation": False,
        "output_dir": None,
    }


def create_graph_rag(
    create_if_not_exists: bool = True, kb_path: Union[Path, None] = None
) -> GenerationStatus:
    if create_if_not_exists:
        if ROOT_DIR.exists() and (ROOT_DIR / "settings.yaml").exists():
            return GenerationStatus.EXISTS
    input_dir = _prepare_graph_rag(kb_path)
    index_cli(**prepare_index_args(input_dir.parent))
    return GenerationStatus.CREATED


async def acreate_graph_rag(
    create_if_not_exists: bool = True, kb_path: Union[Path, None] = None
) -> GenerationStatus:
    if not create_if_not_exists:
        if kb_path.exists() and (kb_path / "settings.yaml").exists():
            return GenerationStatus.EXISTS
    input_dir = _prepare_graph_rag(kb_path)
    await index(**prepare_index_args(input_dir.parent))
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