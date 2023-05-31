#!/bin/bash

# Set the image name and tag
IMAGE_NAME="bubba_ai"
IMAGE_TAG="latest"

# Build the Docker image
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" ./project

# Save the Docker image to a TAR file
docker save -o "zips/${IMAGE_NAME}-${IMAGE_TAG}.tar" "${IMAGE_NAME}:${IMAGE_TAG}"

echo "Docker image ${IMAGE_NAME}:${IMAGE_TAG} saved as zip/${IMAGE_NAME}-${IMAGE_TAG}.tar"
