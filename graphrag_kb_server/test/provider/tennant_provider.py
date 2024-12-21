from typing import Tuple
import shutil

from graphrag_kb_server.model.jwt_token import JWTTokenData
from graphrag_kb_server.config import cfg


def regenerate_test_tennant() -> Tuple[str, JWTTokenData]:
    folder_name = "test"
    folder_path = cfg.graphrag_root_dir_path / folder_name
    if folder_path.exists():
        shutil.rmtree(folder_path)
    token_data = JWTTokenData(
        name=folder_name, email="test@test.com", time_delta_minutes=None
    )
    return folder_name, token_data
