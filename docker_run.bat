@echo off
docker run --rm -it ^
  --env-file .env.docker.secrets ^
  -v C:/var/graphrag:/var/graphrag ^
  -p 9999:9999 ^
  graphrag_kb_server:latest
