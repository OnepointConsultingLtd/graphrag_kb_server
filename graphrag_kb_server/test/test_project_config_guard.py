"""Guards the per-project configuration against regressions.

Models and API keys must come from the ProjectConfig of the project. A call site which reads the
global configuration (cfg / lightrag_cfg / cag_cfg), the environment or builds an API client
without an explicit key would silently use the .env values for every project, so the usage would
not be billed to the key of the project. These tests fail when such code is added.
"""

import re
from pathlib import Path

import pytest

from graphrag_kb_server.model.project_setting import ProjectSetting

APPLICATION_DIR = Path(__file__).parent.parent

# Files which are allowed to read the global configuration of the settings.
ALLOWED_FILES = {
    # Defines the global configuration.
    "config.py",
    # The single place which maps each setting to its .env fallback.
    "service/project_config_service.py",
    # Copies the .env values into the docker environment file on purpose.
    "cli/docker_config_main.py",
}

SETTING_ATTRIBUTES = (
    "openai_api_key",
    "openai_api_model",
    "openai_api_model_embedding",
    "audio_model",
    "gemini_api_key",
    "openrouter_api_key",
    "openrouter_model",
    "openrouter_provider",
    "togetherai_api_key",
)

SETTING_NAMES = "|".join(setting.value for setting in ProjectSetting)

# (description, pattern)
FORBIDDEN_PATTERNS = [
    (
        "reads a project setting of the global cfg",
        re.compile(rf"\bcfg\.({'|'.join(SETTING_ATTRIBUTES)})\b"),
    ),
    (
        "uses lightrag_cfg or cag_cfg",
        re.compile(r"\b(lightrag_cfg|cag_cfg)\b"),
    ),
    (
        "reads a project setting from the environment",
        re.compile(rf"""os\.(getenv\(|environ(\.get\(|\[))\s*["']({SETTING_NAMES})["']"""),
    ),
    (
        "creates an API client without an explicit key",
        re.compile(r"\b(AsyncOpenAI|OpenAI|OpenRouter|AsyncTogether|genai\.Client)\(\s*\)"),
    ),
]

# Calls which must always receive the key explicitly.
CLIENT_CALL = re.compile(r"\b(AsyncOpenAI|OpenAI|OpenRouter|AsyncTogether|genai\.Client)\(([^)]*)\)")


def strip_comments_and_docstrings(source: str) -> str:
    """Removes comments and triple quoted strings so that explanations do not trigger the guard."""
    without_docstrings = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'', "", source, flags=re.DOTALL)
    return "\n".join(line.split("#", 1)[0] for line in without_docstrings.splitlines())


def find_violations(source: str) -> list[str]:
    """Describes every way in which the source bypasses the project configuration."""
    code = strip_comments_and_docstrings(source)
    violations = [
        description
        for description, pattern in FORBIDDEN_PATTERNS
        if pattern.search(code)
    ]
    for match in CLIENT_CALL.finditer(code):
        if "api_key" not in match.group(2) and match.group(2).strip():
            violations.append(f"creates {match.group(1)} without api_key")
    return sorted(set(violations))


def application_files() -> list[Path]:
    """The application sources, without the tests."""
    return [
        path
        for path in APPLICATION_DIR.rglob("*.py")
        if "test" not in path.relative_to(APPLICATION_DIR).parts
        and ".venv" not in path.parts
    ]


def relative_name(path: Path) -> str:
    return path.relative_to(APPLICATION_DIR).as_posix()


def test_application_code_does_not_bypass_the_project_configuration():
    problems = {}
    for path in application_files():
        name = relative_name(path)
        if name in ALLOWED_FILES:
            continue
        violations = find_violations(path.read_text(encoding="utf-8"))
        if violations:
            problems[name] = violations
    assert problems == {}, (
        "These files bypass the per-project configuration. Use get_project_config_for_dir(), "
        "get_project_config() or ProjectConfig.from_env() (code without a project) instead:\n"
        + "\n".join(f"  {name}: {', '.join(found)}" for name, found in problems.items())
    )


def test_the_allowed_files_exist():
    """A renamed file must not silently stay on the allow-list."""
    for name in ALLOWED_FILES:
        assert (APPLICATION_DIR / name).exists(), name


def test_every_project_setting_has_a_global_fallback_attribute():
    """The attribute list of this guard stays in sync with the settings of the project."""
    from graphrag_kb_server.config import cfg
    from graphrag_kb_server.service.project_config_service import _ENV_FALLBACK_SOURCES

    attributes_of_cfg = {
        attribute
        for source, attribute in _ENV_FALLBACK_SOURCES.values()
        if source is cfg
    }
    assert attributes_of_cfg == set(SETTING_ATTRIBUTES)


# --- the guard itself must detect violations ----------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "key = cfg.openai_api_key",
        "model = cfg.openrouter_model",
        "from graphrag_kb_server.config import lightrag_cfg",
        "model = lightrag_cfg.lightrag_model",
        "model = cag_cfg.cag_model",
        'key = os.getenv("GEMINI_API_KEY")',
        "key = os.environ['OPENAI_API_KEY']",
        'key = os.environ.get("TOGETHERAI_API_KEY")',
        "client = AsyncOpenAI()",
        "client = genai.Client()",
        "client = OpenRouter(timeout=5)",
    ],
)
def test_the_guard_detects_bypasses(source):
    assert find_violations(source) != []


@pytest.mark.parametrize(
    "source",
    [
        "client = AsyncOpenAI(api_key=config.openai_api_key or None)",
        "client = genai.Client(api_key=config.gemini_api_key)",
        "client = OpenRouter(api_key=key)",
        "root = cfg.graphrag_root_dir_path",
        "limit = cfg.expand_max_entities",
        'port = os.getenv("PORT")',
        "# key = cfg.openai_api_key",
        '"""Falls back to cfg.openai_api_key."""',
    ],
)
def test_the_guard_accepts_allowed_code(source):
    assert find_violations(source) == []
