from pathlib import Path
import shutil

import pytest

from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER


@pytest.mark.asyncio
async def test_initialize_rag():
    project_folder = Path("test_project")
    rag = await initialize_rag(project_folder)
    assert rag is not None
    assert rag.working_dir == project_folder / LIGHTRAG_FOLDER
    shutil.rmtree(project_folder)

