.venv\Scripts\activate
uv sync
# Build front end chat
cd .\front_end_chat\
copy src\lib\server_prod.ts src\lib\server.ts
yarn
yarn build
cd ..
# Run webapp
python ./graphrag_kb_server/main/webapp.py