import pytest
from click.testing import CliRunner

from graphrag_kb_server.cli import project_keys_main
from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project_setting import ProjectSetting


@pytest.fixture
def stored_calls(monkeypatch) -> list[tuple]:
    """Replaces the database call and records its arguments."""
    calls: list[tuple] = []

    async def fake_store(schema_name, project_name, engine, setting, value):
        calls.append((schema_name, project_name, engine, setting, value))

    monkeypatch.setattr(project_keys_main, "store_project_setting", fake_store)
    return calls


def _run(arguments: list[str], user_input: str | None = None):
    return CliRunner().invoke(project_keys_main.cli, arguments, input=user_input)


def test_set_secret_is_prompted_and_masked_in_output(stored_calls):
    result = _run(
        ["set", "--schema", "t1", "--project", "p1", "--setting", "OPENAI_API_KEY"],
        user_input="sk-1234567890abcd\n",
    )
    assert result.exit_code == 0
    assert stored_calls == [
        ("t1", "p1", Engine.LIGHTRAG, ProjectSetting.OPENAI_API_KEY, "sk-1234567890abcd")
    ]
    assert "sk-1234567890abcd" not in result.output
    assert "abcd" in result.output


def test_set_non_secret_with_value_option_and_engine(stored_calls):
    result = _run(
        [
            "set", "--schema", "t1", "--project", "p1", "--engine", "cag",
            "--setting", "CAG_MODEL", "--value", "gemini-flash",
        ]
    )
    assert result.exit_code == 0
    assert stored_calls == [
        ("t1", "p1", Engine.CAG, ProjectSetting.CAG_MODEL, "gemini-flash")
    ]
    assert "gemini-flash" in result.output


def test_reset_stores_none_without_prompting(stored_calls):
    result = _run(
        ["set", "--schema", "t1", "--project", "p1", "--setting", "CAG_MODEL", "--reset"]
    )
    assert result.exit_code == 0
    assert stored_calls[0][4] is None
    assert ".env" in result.output


def test_unknown_setting_is_rejected(stored_calls):
    result = _run(["set", "--schema", "t1", "--project", "p1", "--setting", "NOPE"])
    assert result.exit_code != 0
    assert stored_calls == []


def test_failure_is_reported_as_cli_error(monkeypatch):
    async def failing_store(*args):
        raise ValueError("Project p1 with engine lightrag not found")

    monkeypatch.setattr(project_keys_main, "store_project_setting", failing_store)
    result = _run(
        ["set", "--schema", "t1", "--project", "p1", "--setting", "CAG_MODEL", "-v", "x"]
    )
    assert result.exit_code != 0
    assert "not found" in result.output
