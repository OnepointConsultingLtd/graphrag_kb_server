import click
import asyncio
import shutil

from pathlib import Path
from graphrag_kb_server.model.jwt_token import JWTTokenData, JWTToken
from graphrag_kb_server.service.jwt_service import generate_token, save_token_file


def generate_token_main(name: str, email: str, token_file: str, docker: bool):
    admin_yaml_file = (
        "config/administration.yaml"
        if not docker
        else "config/administration_docker.yaml"
    )
    token = asyncio.run(generate_token(JWTTokenData(name=name, email=email), False))
    if isinstance(token, JWTToken):
        save_token_file(token, token_file, name, email)
        admin_yaml = f"""
administrators:
  - {email}
"""
        print("\nAdministration YAML:")
        print(admin_yaml)

        print(
            f"\nYour config/administration.yaml is going to be written with this email address: {email}"
        )
        with open(admin_yaml_file, "wt") as f:
            f.write(admin_yaml)

        if docker:
            docker_env = ".env_docker_changed"
            cwd = Path(__file__).parent.parent.parent
            source_file = cwd / ".env_docker"
            target_file = cwd / docker_env
            shutil.copy(source_file, target_file)

            env_docker = Path(docker_env)
            if not env_docker.exists():
                print(f"\nCannot find {docker_env} file.")
            else:
                with open(env_docker, "rt") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    if line.startswith("ADMIN_JWT="):
                        line = f"ADMIN_JWT={token.token}\n"
                        lines[i] = line
                env_docker.write_text("".join(lines), encoding="utf-8")

    else:
        print("Could not generate token.")


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--name",
    "-n",
    type=str,
    help="The name of the administrator or organisation",
    required=True,
)
@click.option(
    "--email",
    "-e",
    type=str,
    help="The email of the administrator or organisation",
    required=True,
)
@click.option(
    "--token_file",
    "-t",
    type=str,
    help="The file which will store the administration token",
)
@click.option(
    "--docker",
    "-d",
    is_flag=True,
    type=bool,
    help="Whether the token is being generated for a Docker container",
    default=False,
)
def generate_admin_token(name: str, email: str, token_file: str, docker: bool):
    generate_token_main(name, email, token_file, docker)
    click.echo("Token generated successfully.")


if __name__ == "__main__":
    cli()
