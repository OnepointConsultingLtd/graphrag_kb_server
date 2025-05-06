#!/bin/bash

cd "$(dirname "$0")"
uv sync
uv run ./graphrag_kb_server/main/webapp.py