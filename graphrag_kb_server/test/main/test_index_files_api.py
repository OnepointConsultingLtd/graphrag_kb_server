import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from aiohttp import FormData, web
from aiohttp_swagger3 import SwaggerDocs, SwaggerInfo

from graphrag_kb_server.config import cfg
from graphrag_kb_server.main.multi_tennant_server import TOKEN_DATA
from graphrag_kb_server.main.multipart_support import multipart_form
from graphrag_kb_server.main.project_server import routes
from graphrag_kb_server.model.project import IndexingStatus
from graphrag_kb_server.service.indexing_job_registry import IndexingJobRegistry

SERVER_MODULE = "graphrag_kb_server.main.project_server"
TENNANT = "tennant_a"
PROJECT = "my_project"
AUTH_HEADERS = {"Authorization": "Bearer test"}


def create_app(tennant: str) -> web.Application:
    """Creates an app with the project routes, swagger validation and a fake authentication."""

    @web.middleware
    async def fake_auth_middleware(request: web.Request, handler):
        request[TOKEN_DATA] = {"sub": tennant}
        return await handler(request)

    app = web.Application(middlewares=[fake_auth_middleware])
    swagger = SwaggerDocs(
        app,
        info=SwaggerInfo(title="test", version="1.0.0"),
        security=cfg.config_dir / "security.yaml",
    )
    swagger.register_media_type_handler(
        media_type="multipart/form-data", handler=multipart_form
    )
    swagger.add_routes(routes)
    return app


def index_files_form(
    file_names: list[str], engine: str = "lightrag", asynchronous: bool = False
) -> FormData:
    data = FormData()
    for file_name in file_names:
        data.add_field("files", b"content", filename=file_name)
    data.add_field("project", PROJECT)
    data.add_field("engine", engine)
    data.add_field("asynchronous", "true" if asynchronous else "false")
    return data


@pytest.fixture
def root_dir(tmp_path: Path):
    (tmp_path / TENNANT / "lightrag" / PROJECT).mkdir(parents=True)
    (tmp_path / "tennant_b").mkdir()
    with patch.object(cfg, "graphrag_root_dir_path", tmp_path):
        yield tmp_path


@pytest.fixture
def registry():
    job_registry = IndexingJobRegistry()
    with patch(f"{SERVER_MODULE}.indexing_job_registry", job_registry):
        yield job_registry


@pytest_asyncio.fixture
async def client(aiohttp_client, root_dir, registry):
    return await aiohttp_client(create_app(TENNANT))


@pytest.mark.asyncio
async def test_synchronous_indexing_returns_result(client, root_dir):
    replace = AsyncMock(return_value=2)
    with patch(f"{SERVER_MODULE}.replace_files_in_index", replace):
        response = await client.post(
            "/protected/project/index_files",
            data=index_files_form(["a.txt", "b.pdf"]),
            headers=AUTH_HEADERS,
        )

    assert response.status == 200
    assert await response.json() == {
        "status": "success",
        "message": f"2 file(s) indexed successfully in index {PROJECT}",
        "job_id": None,
    }
    project_folder, uploaded_files = replace.await_args.args
    assert project_folder == root_dir / TENNANT / "lightrag" / PROJECT
    assert [uploaded.file_name for uploaded in uploaded_files] == ["a.txt", "b.pdf"]


@pytest.mark.asyncio
async def test_synchronous_indexing_failure_returns_error(client):
    replace = AsyncMock(side_effect=RuntimeError("conversion failed"))
    with patch(f"{SERVER_MODULE}.replace_files_in_index", replace):
        response = await client.post(
            "/protected/project/index_files",
            data=index_files_form(["a.txt"]),
            headers=AUTH_HEADERS,
        )

    assert response.status == 500
    assert await response.json() == {
        "status": "error",
        "message": "conversion failed",
        "job_id": None,
    }


@pytest.mark.asyncio
async def test_asynchronous_indexing_returns_job_which_can_be_queried(client, registry):
    indexing_started = asyncio.Event()
    release_indexing = asyncio.Event()

    async def run_job(job_id, _project_folder, _uploaded_files):
        registry.update_status(job_id, IndexingStatus.IN_PROGRESS, "Indexing")
        indexing_started.set()
        await release_indexing.wait()
        registry.update_status(job_id, IndexingStatus.COMPLETED, "done")

    with patch(f"{SERVER_MODULE}.run_indexing_job", run_job):
        response = await client.post(
            "/protected/project/index_files",
            data=index_files_form(["a.txt", "b.md"], asynchronous=True),
            headers=AUTH_HEADERS,
        )
        assert response.status == 202
        body = await response.json()
        assert body["status"] == "success"
        assert body["message"] == f"2 file(s) submitted for indexing in index {PROJECT}"
        job_id = body["job_id"]
        assert job_id

        await indexing_started.wait()
        status_response = await client.get(
            f"/protected/project/index_files/{job_id}", headers=AUTH_HEADERS
        )
        assert status_response.status == 200
        job = await status_response.json()
        assert job["status"] == "in_progress"
        assert job["project"] == PROJECT
        assert job["file_names"] == ["a.txt", "b.md"]
        assert "tennant" not in job

        release_indexing.set()
        await asyncio.gather(*registry._tasks)

    status_response = await client.get(
        f"/protected/project/index_files/{job_id}", headers=AUTH_HEADERS
    )
    assert (await status_response.json())["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize("file_names", [["a.docx"], [f"{i}.txt" for i in range(6)]])
async def test_invalid_files_are_rejected(client, file_names):
    response = await client.post(
        "/protected/project/index_files",
        data=index_files_form(file_names),
        headers=AUTH_HEADERS,
    )
    assert response.status == 400
    assert (await response.json())["error"] == "Invalid files"


@pytest.mark.asyncio
async def test_engines_other_than_lightrag_are_rejected(client):
    replace = AsyncMock()
    with patch(f"{SERVER_MODULE}.replace_files_in_index", replace):
        response = await client.post(
            "/protected/project/index_files",
            data=index_files_form(["a.txt"], engine="cag"),
            headers=AUTH_HEADERS,
        )
    assert response.status == 400
    assert "engine" in await response.text()
    replace.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_project_is_not_found(client, root_dir):
    data = FormData()
    data.add_field("files", b"content", filename="a.txt")
    data.add_field("project", "missing_project")
    data.add_field("engine", "lightrag")

    response = await client.post(
        "/protected/project/index_files", data=data, headers=AUTH_HEADERS
    )

    assert response.status == 404
    assert (await response.json())["error"] == "Project not found"
    assert not (root_dir / TENNANT / "lightrag" / "missing_project").exists()


@pytest.mark.asyncio
async def test_unknown_job_is_not_found(client):
    response = await client.get(
        "/protected/project/index_files/unknown", headers=AUTH_HEADERS
    )
    assert response.status == 404


@pytest.mark.asyncio
async def test_job_of_other_tennant_is_not_found(aiohttp_client, root_dir, registry):
    job = registry.create_job(TENNANT, PROJECT, ["a.txt"])
    other_tennant_client = await aiohttp_client(create_app("tennant_b"))

    response = await other_tennant_client.get(
        f"/protected/project/index_files/{job.job_id}", headers=AUTH_HEADERS
    )

    assert response.status == 404
