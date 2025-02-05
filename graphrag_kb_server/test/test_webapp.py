from pathlib import Path

import subprocess
import time
import requests
import pytest

from graphrag_kb_server.config import websocket_cfg, jwt_cfg


base_server = f"http://127.0.0.1:{websocket_cfg.websocket_port}"

AUTH_HEADER = {
    "accept": "application/json",
    "Authorization": f"Bearer {jwt_cfg.admin_jwt}",
}


@pytest.fixture(scope="module")
def test_server():
    """Starts the server before tests and shuts it down after."""
    webserver_path = Path(__file__) / "../../main/webapp.py"
    assert webserver_path.exists(), "Server file does not exist."
    process = subprocess.Popen(["python", webserver_path])  # Adjust for your app
    sleep_time = 4
    time.sleep(sleep_time)  # Give it time to start
    tries = 3
    while tries > 0:
        tries -= 1
        try:
            response = requests.get(
                f"http://127.0.0.1:{websocket_cfg.websocket_port}/docs"
            )
            if response.status_code == 200:
                break
        except Exception:
            time.sleep(sleep_time)

    yield process  # Runs tests while the server is up

    process.terminate()  # Stop server after tests
    process.wait()


def test_docs(test_server: subprocess.Popen):
    """Example test case that makes a request to the running server."""
    response = requests.get(f"{base_server}/docs")
    assert response.status_code == 200


def test_list_tennants(test_server: subprocess.Popen):
    response = requests.get(
        f"{base_server}/protected/tennant/list_tennants", headers=AUTH_HEADER
    )
    assert response.status_code == 200


def test_create_delete_tennant(test_server: subprocess.Popen):
    response = requests.post(
        f"{base_server}/protected/tennant/create",
        headers=AUTH_HEADER,
        json={"email": "john.doe@test.com", "tennant_name": "john_doe"},
    )
    assert response.status_code == 200
    response = requests.delete(
        f"{base_server}/protected/tennant/delete_tennant",
        headers=AUTH_HEADER,
        json={"tennant_folder": "john_doe"},
    )
    assert response.status_code == 200
