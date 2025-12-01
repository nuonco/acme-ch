#!/bin/bash
set -e

# Script to build data-plane image locally
# Usage: ./scripts/build-data-plane.sh [tag]

IMAGE_NAME="nuonfred/acme-ch-data-plane-agent"
TAG="${1:-latest}"
DOCKERFILE="data-plane/Dockerfile"
CONTEXT="data-plane"

echo "Building data-plane agent image..."
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
