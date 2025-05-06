import os
from pathlib import Path

# Not in use, but could be used to override environment variables for local development
def override_environment_variable(key: str, value: str):
    cwd = Path(os.getcwd())
    env_file = cwd / ".env"
    with open(env_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith(key) or f"{key}=" in line or f"{key} =" in line:
            lines[line] = f"{key}={value}\n"
    env_file.write_text("\n".join(lines))
