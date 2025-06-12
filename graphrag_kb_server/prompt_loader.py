from pathlib import Path
import yaml

prompts_file = Path(__file__).parent.parent / "prompts" / "prompts.yaml"
assert prompts_file.exists(), f"Prompts file {prompts_file} does not exist"


def _load_prompts() -> dict[str, dict[str, str]]:
    return yaml.safe_load(prompts_file.read_text(encoding="utf-8"))


prompts = _load_prompts()
