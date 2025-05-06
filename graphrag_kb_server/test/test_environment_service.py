from pathlib import Path
from graphrag_kb_server.service.environment_service import override_environment_variable


def test_override_environment_variable():
    cwd = Path(__file__).parent.parent.parent
    target_file = cwd / ".env_docker_changed"
    override_environment_variable("JWT_SECRET", "test", target_file)
    assert Path(".env_docker_changed").exists()
    assert "JWT_SECRET=test" in target_file.read_text()
