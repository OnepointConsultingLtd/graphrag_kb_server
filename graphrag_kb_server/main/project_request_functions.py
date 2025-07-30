from pathlib import Path
from aiohttp import web
from aiohttp.web import Response

from graphrag_kb_server.config import cfg
from graphrag_kb_server.main.error_handler import invalid_response
from graphrag_kb_server.model.engines import find_engine_from_query
from graphrag_kb_server.service.tennant import find_project_folder
from graphrag_kb_server.model.engines import Engine


def extract_tennant_folder(request: web.Request) -> Path | Response:
    token_data = request["token_data"]
    if token_data is None:
        return invalid_response(
            "No tennant information", "No tennant information available in request"
        )
    tennant_folder = cfg.graphrag_root_dir_path / token_data["sub"]
    if not tennant_folder.exists():
        return invalid_response("No tennant folder", "Tennant folder was deleted.")
    return tennant_folder


def handle_project_folder(
    request: web.Request, tennant_folder: Path
) -> Path | Response:
    engine = find_engine_from_query(request)
    project = request.rel_url.query.get("project")
    if not project:
        return invalid_response(
            "No project",
            "Please specify the project name",
        )
    project_dir: Path = find_project_folder(tennant_folder, engine, project)
    if not project_dir.exists():
        return invalid_response(
            "No project folder found",
            f"There is no project folder {project}",
        )
    return project_dir


def extract_engine_limit(
    request: web.Request, limit_name: str = "limit"
) -> tuple[Engine, int]:
    engine = find_engine_from_query(request)
    limit = request.rel_url.query.get(limit_name, 8)
    return engine, limit
