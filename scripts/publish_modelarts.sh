#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: IMAGE_REPOSITORIES=<repo>[,<repo>...] [PLATFORMS=linux/amd64,linux/arm64] scripts/publish_modelarts.sh <modelarts-tag>

Build and push one ModelArts image with Docker Buildx.
Login to every target registry before running this script.

Example:
  docker login ghcr.io
  IMAGE_REPOSITORIES=ghcr.io/acme/modelarts-cann scripts/publish_modelarts.sh 9.0.0-910b-ubuntu22.04
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

if [[ -z "${IMAGE_REPOSITORIES:-}" ]]; then
  echo "error: IMAGE_REPOSITORIES is required" >&2
  usage
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELARTS_TAG="$1"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"

cd "${REPO_ROOT}"

IMAGE_PATH="$(python3 scripts/modelarts_metadata.py path --modelarts-tag "${MODELARTS_TAG}")"
BASE_IMAGE="$(python3 scripts/modelarts_metadata.py base-image --modelarts-tag "${MODELARTS_TAG}")"
scripts/prepare_modelarts_context.sh "${IMAGE_PATH}"

tag_args=()
while IFS= read -r image_tag; do
  tag_args+=("-t" "${image_tag}")
done < <(python3 scripts/modelarts_metadata.py tags \
  --modelarts-tag "${MODELARTS_TAG}" \
  --repositories "${IMAGE_REPOSITORIES}" \
  --format newline)

set -x
docker buildx build \
  --platform "${PLATFORMS}" \
  --provenance=false \
  --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
  --push \
  "${tag_args[@]}" \
  -f "${IMAGE_PATH}/Dockerfile" \
  "${IMAGE_PATH}"
