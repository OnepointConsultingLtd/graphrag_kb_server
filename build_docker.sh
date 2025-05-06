#!/bin/bash

# Use this script to build the docker image
# You need to have uv and docker installed
# You need to have the .env file in the root of the project
# Run this script from the root of the project

# Activate virtual environment
source .venv/bin/activate

# Sync dependencies
uv sync

# Generate admin token
uv run python graphrag_kb_server/cli/jwt_main.py generate-admin-token \
    --name "Gil Fernandes" \
    --email "gil.fernandes@onepointltd.com" \
    --token_file "admin_token_docker.md" \
    --docker

# Create docker config
uv run python graphrag_kb_server/cli/docker_config_main.py create-docker-config

# Build and run docker container
docker-compose up --build 