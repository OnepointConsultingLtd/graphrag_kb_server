from pathlib import Path
import click

from graphrag_kb_server.service.environment_service import override_environment_variable
from graphrag_kb_server.config import jwt_cfg, cfg


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--keys",
    "-k",
    is_flag=True,
    type=bool,
    help="Whether the keys are being copied or not",
    default=False,
)
def create_docker_config(keys: bool):
    cwd = Path(__file__).parent.parent.parent
    target_file = cwd / ".env_docker_changed"
    if keys:
        override_environment_variable("OPENAI_API_KEY", cfg.openai_api_key, target_file)
        override_environment_variable("GEMINI_API_KEY", cfg.gemini_api_key, target_file)
    override_environment_variable("JWT_SECRET", jwt_cfg.secret, target_file)


if __name__ == "__main__":
    cli()
