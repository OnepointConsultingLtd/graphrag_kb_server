from pathlib import Path

# Not in use, but could be used to override environment variables for local development
def override_environment_variable(key: str, value: str, target_file: Path):
    with open(target_file) as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith(key) or f"{key}=" in line or f"{key} =" in line:
            lines[i] = f"{key}={value}\n"
    target_file.write_text("".join(lines))
