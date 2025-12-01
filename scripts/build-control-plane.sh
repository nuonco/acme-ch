#!/bin/bash
set -e

# Script to build control-plane image locally
# Usage: ./scripts/build-control-plane.sh [tag]

IMAGE_NAME="nuonfred/acme-ch-control-plane"
TAG="${1:-latest}"
DOCKERFILE="control-plane/Dockerfile.prod"
CONTEXT="control-plane"

echo "Building control-plane image..."
echo "Image: ${IMAGE_NAME}:${TAG}"
echo "Dockerfile: ${DOCKERFILE}"
echo "Context: ${CONTEXT}"
echo ""

# Build the image
docker build \
  -f "${DOCKERFILE}" \
  -t "${IMAGE_NAME}:${TAG}" \
  "${CONTEXT}"

echo ""
echo "Build complete!"
echo "Image: ${IMAGE_NAME}:${TAG}"
echo ""
echo "To push the image, run:"
echo "  docker push ${IMAGE_NAME}:${TAG}"
