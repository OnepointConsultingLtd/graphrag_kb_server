from pathlib import Path
import tomli

prompts_file = Path(__file__).parent.parent / "prompts" / "prompts.toml"
assert prompts_file.exists(), f"Prompts file {prompts_file} does not exist"


def _load_prompts() -> dict:
    """Load a TOML file and return a dictionary"""
    with open(prompts_file, "rb") as f:
        return tomli.load(f)


prompts = _load_prompts()
