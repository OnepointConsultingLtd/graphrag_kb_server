$DOCKER_IMAGE = "gilf/graphrag_kb_server:latest"

docker login
docker tag graphrag_kb_server $DOCKER_IMAGE
docker push $DOCKER_IMAGE
