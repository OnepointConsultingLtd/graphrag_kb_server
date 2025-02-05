from pathlib import Path
import subprocess
import os

def run():
    print("Building web server ...")

    front_end_path = Path(__file__)/"../../../front_end"
    assert front_end_path.exists(), "The front end path does not exist."
    print(f"Found {front_end_path}")
    params = {"cwd": front_end_path.as_posix(), "check": True, "shell": True}
    subprocess.run(["yarn", "install"], **params)
    subprocess.run(["yarn", "run", "build"], **params)


if __name__ == "__main__":
    run()
    