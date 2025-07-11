import shutil
import re
import yaml
import json

from pathlib import Path
from datetime import datetime
from typing import Union, Final

from collections.abc import AsyncIterable
from graphrag.index.typing.pipeline_run_result import PipelineRunResult

from graphrag.cli.index import index_cli
from graphrag.cli.initialize import initialize_project_at
from graphrag.logger.factory import LoggerType

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.service.index_support import index
from graphrag_kb_server.model.project import (
    Project,
    ProjectListing,
    EngineProjectListing,
    GenerationStatus,
    IndexingStatus,
)
from graphrag_kb_server.model.engines import Engine


PROJECT_INFO_FILE: Final = "project.json"

ROOT_DIR: Final = Path(cfg.graphrag_root_dir)
DIR_VECTOR_DB: Final = ROOT_DIR / cfg.vector_db_dir
INPUT_DIR: Final = ROOT_DIR / "input"

create_folder_props = {"parents": True, "exist_ok": True}


async def run_pipeline(pipelines: AsyncIterable[PipelineRunResult]):
    async for p in pipelines:
        logger.info(p)


def clear_rag(rag_folder: Path) -> bool:
    deleted = False
    if rag_folder.exists():
        shutil.rmtree(rag_folder, ignore_errors=True)
        deleted = True
    return deleted


def list_projects(tennants_dir: Path) -> EngineProjectListing:
    if not tennants_dir.exists():
        return []
    graphrag_projects = _extract_graphrag_projects(tennants_dir)
    lightrag_projects = _extract_lightrag_projects(tennants_dir)
    cag_projects = _extract_cag_projects(tennants_dir)
    return EngineProjectListing(
        graphrag_projects=graphrag_projects,
        lightrag_projects=lightrag_projects,
        cag_projects=cag_projects,
    )


def _extract_project_listing(tennants_dir: Path, engine: Engine) -> ProjectListing:
    projects = []
    for f in (tennants_dir / engine.value).glob("*"):
        if f.is_dir() and (input_files_dir := f / "input").exists():
            add_input_files(f, input_files_dir, projects)
    return ProjectListing(projects=projects)


def _extract_lightrag_projects(tennants_dir: Path) -> ProjectListing:
    return _extract_project_listing(tennants_dir, Engine.LIGHTRAG)


def _extract_cag_projects(tennants_dir: Path) -> ProjectListing:
    return _extract_project_listing(tennants_dir, Engine.CAG)


def _extract_graphrag_projects(tennants_dir: Path) -> ProjectListing:
    projects = []
    for f in (tennants_dir / Engine.GRAPHRAG.value).glob("*"):
        if (
            f.is_dir()
            and (
                len(list(f.glob("settings.yaml"))) > 0
                or len(list(f.glob("project.json"))) > 0
            )
            and (input_files_dir := f / "input").exists()
        ):
            add_input_files(f, input_files_dir, projects)
    return ProjectListing(projects=projects)


def single_project_status(project_dir: Path) -> Project | None:
    projects: list[Project] = []
    if not project_dir.exists():
        return None
    input_files_dir = project_dir / "input"
    add_input_files(project_dir, input_files_dir, projects)
    return projects[0] if len(projects) > 0 else None


def add_input_files(project_dir: Path, input_files_dir: Path, projects: list[Project]):
    input_files = list([p.name for p in input_files_dir.rglob("**/*.txt")])
    project_file = project_dir / PROJECT_INFO_FILE
    if project_file.exists():
        try:
            project = Project.model_validate_json(project_file.read_text())
            projects.append(project)
            return
        except json.JSONDecodeError:
            logger.warning(f"Invalid project file: {project_file}")
    name = project_dir.name
    updated_timestamp = datetime.fromtimestamp(project_dir.stat().st_mtime)
    projects.append(
        Project(
            name=name,
            updated_timestamp=updated_timestamp,
            input_files=input_files,
            indexing_status=IndexingStatus.UNKNOWN,
        )
    )


def override_env(input_dir: Path):
    env = input_dir.parent / ".env"
    env_text = env.read_text()
    env_text = env_text.replace("<API_KEY>", cfg.openai_api_key)
    env.write_text(env_text)


def read_settings(root_dir):
    settings = root_dir / "settings.yaml"
    return settings, settings.read_text()


def override_settings(root_dir: Path):
    settings, orig_settings_text = read_settings(root_dir)
    # Add support for markdown file parsing.
    settings_text = re.sub(
        r"file_pattern: .+", 'file_pattern: ".*\\\\\.(txt|md)$"', orig_settings_text
    )
    settings_text = re.sub(
        r"(model: )text-embedding-3-small",
        r"\1" + cfg.openai_api_model_embedding,
        settings_text,
    )
    settings_text = re.sub(
        r"(model: )gpt-4-turbo-preview",
        r"\1" + cfg.openai_api_model,
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
    # TODO Consider exposing this parameter to the user.
    initialize_project_at(project_dir, force=True)
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
        "output_dir": root_dir / "output",
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


def write_project_file(project_dir: Path, status: IndexingStatus) -> Project:
    project_name = project_dir.name
    files = project_dir.rglob("input/**/*.txt")
    project = Project(
        name=project_name,
        updated_timestamp=datetime.now(),
        indexing_status=status,
        input_files=[f.as_posix() for f in files],
    )
    project_file = project_dir / PROJECT_INFO_FILE
    if not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
    project_file.write_text(project.model_dump_json())
    return project
