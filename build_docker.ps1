.venv\Scripts\activate
uv sync
uv run python graphrag_kb_server\cli\jwt_main.py generate-admin-token --name "Gil Fernandes" --email "gil.fernandes@onepointltd.com" --token_file "admin_token_docker.md" --docker
# docker build -t graphrag-kb-server .
docker-compose up --build
