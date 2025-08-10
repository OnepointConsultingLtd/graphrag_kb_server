#!/bin/bash

cd /home/ubuntu/projects/graphrag_kb_server_chat_ui

source .venv/bin/activate
/home/ubuntu/.local/bin/uv sync

# Build GraphRAG front end
# cd front_end
# cp server_prod.js server.ts
# yarn
# yarn build
# cd ..

# Build front end chat
# nvm use v22.12.0
# cd front_end_chat
# cp src/lib/server_prod.ts src/lib/server.ts
# yarn
# yarn build
# cd ..

cd "$(dirname "$0")"
/home/ubuntu/.local/bin/uv sync
/home/ubuntu/.local/bin/uv run ./graphrag_kb_server/main/webapp.py