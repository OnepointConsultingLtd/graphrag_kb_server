import base64

import pytest
from aiohttp import FormData, web

from graphrag_kb_server.main.multipart_support import multipart_form


async def echo_form(request: web.Request) -> web.Response:
    """Returns the parsed form with the binary content decoded for the assertions."""
    form, raw = await multipart_form(request)
    decoded = {
        key: (
            [base64.b64decode(item).decode() for item in value]
            if key == "files"
            else base64.b64decode(value).decode() if key == "file" else value
        )
        for key, value in form.items()
    }
    return web.json_response({"form": decoded, "raw": raw})


@pytest.fixture
def echo_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/echo", echo_form)
    return app


@pytest.mark.asyncio
async def test_multipart_form_collects_repeated_files(echo_app, aiohttp_client):
    client = await aiohttp_client(echo_app)
    data = FormData()
    data.add_field("files", b"first", filename="a.txt")
    data.add_field("files", b"second", filename="b.md")
    data.add_field("project", "my_project")

    response = await client.post("/echo", data=data)

    body = await response.json()
    assert body["raw"] is True
    assert body["form"] == {
        "files": ["first", "second"],
        "files_names": ["a.txt", "b.md"],
        "project": "my_project",
    }


@pytest.mark.asyncio
async def test_multipart_form_keeps_single_file_format(echo_app, aiohttp_client):
    client = await aiohttp_client(echo_app)
    data = FormData()
    data.add_field("file", b"zip content", filename="index.zip")
    data.add_field("incremental", "true")

    response = await client.post("/echo", data=data)

    assert (await response.json())["form"] == {
        "file": "zip content",
        "file_name": "index.zip",
        "incremental": "true",
    }
