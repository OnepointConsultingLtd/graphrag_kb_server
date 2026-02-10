docker system prune -f

$IMAGE_NAME = "graphrag_kb_server"
$TAG = "v0.4.0"

# Use this script to build the docker image
# You need to have uv and docker installed
# You need to have the .env file in the root of the project
# Run this script from the root of the project
.venv\Scripts\activate
uv sync
# Change name according to your name
docker build -t ${IMAGE_NAME}:${TAG} -f Dockerfile .

$AWS_REGION = "eu-west-2"
$REPO_NAME="knowledge_server/${IMAGE_NAME}"
$ECR_REGISTRY="303872128380.dkr.ecr.eu-west-2.amazonaws.com"
$ECR_IMAGE="${ECR_REGISTRY}/${REPO_NAME}:${TAG}"

aws ecr get-login-password --region $AWS_REGION --profile onepoint | docker login --username AWS --password-stdin $ECR_REGISTRY
docker tag ${IMAGE_NAME}:${TAG} $ECR_IMAGE
docker push $ECR_IMAGE

