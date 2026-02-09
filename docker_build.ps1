docker system prune -f

# Use this script to build the docker image
# You need to have uv and docker installed
# You need to have the .env file in the root of the project
# Run this script from the root of the project
.venv\Scripts\activate
uv sync
# Change name according to your name
docker build -t graphrag_kb_server .
