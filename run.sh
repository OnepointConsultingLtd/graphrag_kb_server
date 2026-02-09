#!/bin/bash

cd /home/ubuntu/projects/graphrag_kb_server_chat_ui

source .venv/bin/activate
/home/ubuntu/.local/bin/uv sync

# Build GraphRAG front end
cd front_end
cp server_prod.js server.ts
yarn
yarn build
cd ..

# Build front end chat
nvm use v22.12.0
cd front_end_chat
cp src/lib/server_prod.ts src/lib/server.ts
yarn
yarn build
VERSION=1.0.1
sed -i "s/index-fixed\.css?v=[0-9]\+/index-fixed.css/g" ./front_end_chat/dist/index.html
sed -i "s/index-fixed.css/index-fixed.css?v=$VERSION/g" ./front_end_chat/dist/index.html
sed -i "s/index-fixed\.js?v=[0-9]\+/index-fixed.js/g" ./front_end_chat/dist/index.html
sed -i "s/index-fixed.js/index-fixed.js?v=$VERSION/g" ./front_end_chat/dist/index.html
cd ..

cd "$(dirname "$0")"
/home/ubuntu/.local/bin/uv sync
/home/ubuntu/.local/bin/uv run ./graphrag_kb_server/main/webapp.py