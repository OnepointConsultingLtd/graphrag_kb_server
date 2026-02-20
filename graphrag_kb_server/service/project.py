import shutil
import json

from pathlib import Path
from datetime import datetime
from typing import Final

from graphrag_kb_server.config import cfg
from graphrag_kb_server.logger import logger
from graphrag_kb_server.main.multi_tennant_server import local_list_tennants
from graphrag_kb_server.model.project import (
    FullProject,
    Project,
    ProjectListing,
    EngineProjectListing,
    IndexingStatus,
)
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.service.db.common_operations import extract_elements_from_path
from graphrag_kb_server.service.db.db_persistence_project import delete_project
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER
from graphrag_kb_server.service.lightrag.lightrag_init import (
    initialize_rag,
    lightrag_cache,
)
from graphrag_kb_server.service.link_extraction_service import save_links
from graphrag_kb_server.service.pdf_image_extraction import extract_images_from_pdfs


PROJECT_INFO_FILE: Final = "project.json"

ROOT_DIR: Final = Path(cfg.graphrag_root_dir)
DIR_VECTOR_DB: Final = ROOT_DIR / cfg.vector_db_dir
INPUT_DIR: Final = ROOT_DIR / "input"

create_folder_props = {"parents": True, "exist_ok": True}


async def clear_rag(rag_folder: Path) -> bool:
    deleted = False
    if rag_folder.exists():
        shutil.rmtree(rag_folder, ignore_errors=True)
        deleted = True
    # Delete also the project in the database
    simple_project = extract_elements_from_path(rag_folder)
    await delete_project(
        FullProject(
            id=None,
            schema_name=simple_project.schema_name,
            engine=simple_project.engine,
            project=Project(
                name=simple_project.project_name,
                updated_timestamp=datetime.now(),
                input_files=[],
                indexing_status=IndexingStatus.UNKNOWN,
            ),
        )
    )
    # Delete also the cache
    lightrag_cache.clear(rag_folder)
    return deleted


def list_projects(tennants_dir: Path) -> EngineProjectListing:
    if not tennants_dir.exists():
        return EngineProjectListing(
            lightrag_projects=ProjectListing(projects=[]),
            cag_projects=ProjectListing(projects=[]),
        )
    lightrag_projects = _extract_lightrag_projects(tennants_dir)
    cag_projects = _extract_cag_projects(tennants_dir)
    return EngineProjectListing(
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
    project_file.write_text(project.model_dump_json(), encoding="utf-8")
    return project


async def initialize_projects():
    # Load all LightRAG projects
    from graphrag_kb_server.service.project import list_projects as project_listing

    tennants = local_list_tennants()
    for tennant in tennants:
        try:
            projects = project_listing(cfg.graphrag_root_dir_path / tennant.folder_name)
            for project in projects.lightrag_projects.projects:
                project_folder = (
                    cfg.graphrag_root_dir_path
                    / tennant.folder_name
                    / LIGHTRAG_FOLDER
                    / project.name
                )
                await initialize_rag(project_folder)
                if cfg.extract_links_on_start:
                    await prepare_project_extras(project_folder)
        except Exception as e:
            logger.exception(
                f"Error initializing LightRAG project for tennant {tennant.folder_name}: {e}"
            )


async def prepare_project_extras(project_folder: Path):
    await save_links(project_folder, insert_if_not_exists=True)
    await extract_images_from_pdfs(project_folder)
