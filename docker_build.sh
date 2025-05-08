#!/bin/bash

# Use this script to build the docker image
# You need to have uv and docker installed
# You need to have the .env file in the root of the project
# Run this script from the root of the project

# Activate virtual environment
source .venv/bin/activate

# Sync dependencies
uv sync

# Build and run docker container
docker build -t graphrag_kb_server .