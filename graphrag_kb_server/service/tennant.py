import json
from typing import Tuple
from pathlib import Path
import shutil

from graphrag_kb_server.config import cfg, websocket_cfg
from graphrag_kb_server.model.jwt_token import JWTToken
from graphrag_kb_server.model.error import Error, ErrorCode
from graphrag_kb_server.model.tennant import Tennant
from graphrag_kb_server.utils.file_support import get_creation_time
from graphrag_kb_server.model.engines import Engine

TENNANT_JSON = "tennant.json"


def get_folder(jwt_token: JWTToken) -> Tuple[Path, str]:
    folder_name = jwt_token.folder_name
    return cfg.graphrag_root_dir_path / folder_name, folder_name


def create_tennant_folder(jwt_token: JWTToken) -> str | Error:
    folder_path, folder_name = get_folder(jwt_token)
    if not folder_path.exists():
        folder_path.mkdir()
        descriptor = folder_path / TENNANT_JSON
        descriptor.write_text(jwt_token.model_dump_json(), encoding="utf-8")
    else:
        return Error(
            error_code=ErrorCode.PROJECT_EXISTS,
            error="Folder exists",
            description=f"Folder {folder_name} already exists. Choose another one.",
        )
    return folder_name


def delete_tennant_folder(jwt_token: JWTToken) -> str | None:
    _, folder_name = get_folder(jwt_token)
    delete_tennant_folder_by_folder(folder_name)


def delete_tennant_folder_by_folder(folder_name: str) -> str | None:
    folder_path: Path = cfg.graphrag_root_dir_path / folder_name
    if folder_path.exists():
        shutil.rmtree(folder_path)
        return folder_name
    return None


def list_tennants() -> list[Tennant]:
    tennants = []
    for d in cfg.graphrag_root_dir_path.glob("*"):
        if d.is_dir():
            tennant_jsons = list(d.glob(TENNANT_JSON))
            if len(tennant_jsons) > 0:
                tennant_json: Path = tennant_jsons[0]
                tennant_json_content = tennant_json.read_text(encoding="utf-8")
                tennant_json_dict = json.loads(tennant_json_content)
                token = tennant_json_dict["token"]
                tennants.append(
                    Tennant(
                        folder_name=d.name,
                        creation_timestamp=get_creation_time(d),
                        token=token,
                        visualization_url=f"//{websocket_cfg.websocket_server}:{websocket_cfg.websocket_port}/graphrag.html?token={token}",
                        chat_url=f"//{websocket_cfg.websocket_server}:{websocket_cfg.websocket_port}/chat.html?token={token}",
                    )
                )
    return tennants


def find_project_folder(tennant_folder: Path, engine: Engine, project: str) -> Path:
    folder = tennant_folder / engine.value / project
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
    return folder
