"""Utility to create the encryption key for per-project secrets and to encrypt values.

Deliberately does not import the application config so it can run before .env is complete.
"""

import asyncio
from pathlib import Path

import click
from dotenv import load_dotenv

from graphrag_kb_server.model.engines import Engine
from graphrag_kb_server.model.project_setting import SECRET_SETTINGS, ProjectSetting
from graphrag_kb_server.service.crypto.secret_cipher import (
    ENCRYPTION_KEY_ENV_VARIABLE,
    encrypt_secret,
    generate_encryption_key,
    mask_secret,
)
from graphrag_kb_server.service.environment_service import (
    override_environment_variable,
)


def write_key_to_env_file(key: str, env_file: Path) -> None:
    """Set PROJECT_KEYS_ENCRYPTION_KEY in the env file, appending it if not present yet."""
    if not env_file.exists():
        env_file.write_text("", encoding="utf-8")
    content = env_file.read_text(encoding="utf-8")
    if f"{ENCRYPTION_KEY_ENV_VARIABLE}=" in content:
        override_environment_variable(ENCRYPTION_KEY_ENV_VARIABLE, key, env_file)
    else:
        separator = "" if content == "" or content.endswith("\n") else "\n"
        env_file.write_text(
            f"{content}{separator}{ENCRYPTION_KEY_ENV_VARIABLE}={key}\n",
            encoding="utf-8",
        )


async def store_project_setting(
    schema_name: str,
    project_name: str,
    engine: Engine,
    setting: ProjectSetting,
    value: str | None,
) -> None:
    """Write (or reset, when value is None) one setting of a project in TB_PROJECT_KEYS.

    The application imports are local because they load the full application config, which the
    other commands of this utility deliberately avoid.
    """
    from graphrag_kb_server.model.project import SimpleProject
    from graphrag_kb_server.service.db.connection_pool import close_connection_pool
    from graphrag_kb_server.service.db.db_persistence_project_keys import (
        create_project_keys_table,
    )
    from graphrag_kb_server.service.project_config_service import (
        save_project_settings,
    )

    project = SimpleProject(
        schema_name=schema_name, engine=engine, project_name=project_name
    )
    try:
        await create_project_keys_table(schema_name)
        await save_project_settings(project, {setting: value})
    finally:
        await close_connection_pool()


def describe_value(setting: ProjectSetting, value: str | None) -> str:
    """Display-safe description of a stored value (secrets are masked)."""
    if value is None:
        return "reset to the .env value"
    return mask_secret(value) if setting in SECRET_SETTINGS else value


@click.group()
def cli():
    load_dotenv()


@cli.command("generate-key")
@click.option(
    "--write-env",
    is_flag=True,
    default=False,
    help=f"Write the key as {ENCRYPTION_KEY_ENV_VARIABLE} into the env file.",
)
@click.option(
    "--env-file",
    type=click.Path(path_type=Path),
    default=Path(".env"),
    show_default=True,
    help="The env file used with --write-env.",
)
def generate_key(write_env: bool, env_file: Path):
    """Generate a new Fernet encryption key."""
    key = generate_encryption_key()
    if write_env:
        write_key_to_env_file(key, env_file)
        click.echo(f"{ENCRYPTION_KEY_ENV_VARIABLE} written to {env_file}")
    else:
        click.echo(key)


@cli.command("encrypt")
@click.option(
    "--value",
    "-v",
    type=str,
    default=None,
    help="The value to encrypt. If omitted it is prompted for with hidden input.",
)
def encrypt(value: str | None):
    """Encrypt a value with the key in the PROJECT_KEYS_ENCRYPTION_KEY environment variable."""
    if value is None:
        value = click.prompt("Value to encrypt", hide_input=True)
    click.echo(encrypt_secret(value))


@cli.command("set")
@click.option("--schema", required=True, help="The tenant schema name.")
@click.option("--project", required=True, help="The project name.")
@click.option(
    "--engine",
    type=click.Choice([engine.value for engine in Engine]),
    default=Engine.LIGHTRAG.value,
    show_default=True,
    help="The engine of the project.",
)
@click.option(
    "--setting",
    required=True,
    type=click.Choice([setting.value for setting in ProjectSetting]),
    help="The setting to override for this project.",
)
@click.option(
    "--value",
    "-v",
    default=None,
    help="The value. If omitted it is prompted for (hidden input for secrets).",
)
@click.option(
    "--reset",
    is_flag=True,
    default=False,
    help="Remove the override so the project falls back to the .env value.",
)
def set_setting(
    schema: str, project: str, engine: str, setting: str, value: str | None, reset: bool
):
    """Set a per-project setting in TB_PROJECT_KEYS (secrets are stored encrypted)."""
    project_setting = ProjectSetting(setting)
    if reset:
        value = None
    elif value is None:
        value = click.prompt(
            f"Value for {setting}", hide_input=project_setting in SECRET_SETTINGS
        )
    try:
        asyncio.run(
            store_project_setting(
                schema, project, Engine(engine), project_setting, value
            )
        )
    except Exception as error:
        raise click.ClickException(str(error)) from error
    click.echo(
        f"{setting} for {schema}/{project} ({engine}): {describe_value(project_setting, value)}"
    )


if __name__ == "__main__":
    cli()
