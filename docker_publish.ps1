$DOCKER_IMAGE = "gilf/graphrag_kb_server:v0.2.0"

.\docker_build.ps1

docker login
docker tag graphrag_kb_server $DOCKER_IMAGE
docker push $DOCKER_IMAGE
