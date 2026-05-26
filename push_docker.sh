#!/bin/bash

# Exit on error
set -e

# Use provided image name or fallback to interactive input
IMAGE_NAME="${1:-<YOUR_DOCKER_HUB_IMAGE>}"
TAG="${2:-latest}"

if [ "$IMAGE_NAME" = "<YOUR_DOCKER_HUB_IMAGE>" ]; then
    echo "Usage: ./push_docker.sh [image_name] [tag]"
    echo "Example: ./push_docker.sh username/server-odb latest"
    echo ""
    read -p "Enter target Docker Hub image name (e.g., username/server-odb): " INPUT_IMAGE
    if [ -z "$INPUT_IMAGE" ]; then
        echo "Error: Image name is required to push."
        exit 1
    fi
    IMAGE_NAME="$INPUT_IMAGE"
fi

echo "Building Docker image ${IMAGE_NAME}:${TAG}..."
docker build -t "${IMAGE_NAME}:${TAG}" .

echo "Logging in to Docker Hub..."
docker login

echo "Pushing Docker image ${IMAGE_NAME}:${TAG}..."
docker push "${IMAGE_NAME}:${TAG}"

echo "Done!"
