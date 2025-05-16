$DOCKER_IMAGE = "gilf/graphrag_kb_server:v0.1.0"

docker login
docker tag graphrag_kb_server $DOCKER_IMAGE
docker push $DOCKER_IMAGE
