#!/bin/bash

# Build script for Truputi server
set -e

VERSION="${1:-latest}"
REGISTRY="${DOCKER_REGISTRY:-localhost}"
IMAGE_NAME="truputi-server"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${VERSION}"

echo "Building Truputi server..."
echo "Image: ${FULL_IMAGE}"
echo ""

# Build the Docker image
docker build -t "${IMAGE_NAME}:${VERSION}" -t "${IMAGE_NAME}:latest" .

echo ""
echo "Build complete: ${IMAGE_NAME}:${VERSION}"
echo ""

# Tag for registry if not localhost
if [ "${REGISTRY}" != "localhost" ]; then
    echo "Tagging for registry: ${FULL_IMAGE}"
    docker tag "${IMAGE_NAME}:${VERSION}" "${FULL_IMAGE}"

    read -p "Push to registry ${REGISTRY}? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Pushing to registry..."
        docker push "${FULL_IMAGE}"
        echo "Push complete!"
    fi
else
    echo "Skipping registry push (REGISTRY=localhost)"
fi

echo ""
echo "To run locally:"
echo "  docker run -d -p 32201:32201 -e TRUPUTI_PSK='your-secret' ${IMAGE_NAME}:${VERSION}"
echo ""
echo "To test:"
echo "  ./client.py --server localhost --psk your-secret"
