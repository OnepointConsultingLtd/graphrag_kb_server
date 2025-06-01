from pathlib import Path
import subprocess
import re


def install_build(path: Path):
    params = {"cwd": path.as_posix(), "check": True, "shell": True}
    subprocess.run(["yarn", "install"], **params)
    subprocess.run(["yarn", "run", "build"], **params)


def _create_path(path: str) -> Path:
    front_end_path = (Path(__file__) / f"../../../{path}").resolve()
    assert (
        front_end_path.exists()
    ), f"The front end path '{front_end_path}' does not exist."
    print(f"Found {front_end_path}")
    return front_end_path


def process_graphrag():
    print("Building graphrag web server ...")
    front_end_path = _create_path("front_end")
    server_path = front_end_path / "server.js"
    assert server_path.exists(), f"{server_path} does not exist"
    server_path_text = server_path.read_text()
    # Change the file with the server path
    new_server_path_text = re.sub(r"\"[^\"]+\"", '""', server_path_text)
    server_path.write_text(new_server_path_text, encoding="utf-8")

    install_build(front_end_path)
    # Resetting the file with the server path
    server_path.write_text(server_path_text, encoding="utf-8")


def process_chat():
    front_end_path = _create_path("front_end_chat")
    install_build(front_end_path)


def run():
    process_graphrag()
    process_chat()


if __name__ == "__main__":
    run()
