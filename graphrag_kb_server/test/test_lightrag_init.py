from pathlib import Path
import shutil
import os

import pytest

from graphrag_kb_server.service.lightrag.lightrag_init import initialize_rag
from graphrag_kb_server.service.lightrag.lightrag_constants import LIGHTRAG_FOLDER

@pytest.mark.asyncio
async def test_initialize_rag_openai():
    os.environ["LIGHTRAG_MODEL"] = "gpt-4o-mini"
    await create_test_project("test_project_openai")


@pytest.mark.asyncio
async def test_initialize_rag_gemini():
    # Setting the model does not really work
    os.environ["LIGHTRAG_MODEL"] = "gemini-2.0-flash"

    await create_test_project("test_project_gemini")


async def create_test_project(project_name: str):
    project_folder = Path(project_name)
    rag = await initialize_rag(project_folder)
    assert rag is not None
    assert rag.working_dir == project_folder / LIGHTRAG_FOLDER
    shutil.rmtree(project_folder)
