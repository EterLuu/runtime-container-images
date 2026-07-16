#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: IMAGE_REPOSITORIES=<repo>[,<repo>...] [IMAGE_KEY=<images/...>] [PLATFORMS=linux/amd64,linux/arm64] [RELEASE_TIMESTAMP=YYMMDD.HHMMSS] scripts/publish_image.sh <image-tag>

Build and push one runtime image with Docker Buildx.
Login to every target registry before running this script.

Example:
  docker login ghcr.io
  IMAGE_REPOSITORIES=ghcr.io/acme/modelarts-cann scripts/publish_image.sh 9.0.0-910b-ubuntu22.04
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
IMAGE_TAG="$1"
IMAGE_KEY="${IMAGE_KEY:-}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
RELEASE_TIMESTAMP="${RELEASE_TIMESTAMP:-$(TZ=Asia/Shanghai date +%y%m%d.%H%M%S)}"

if [[ ! "${RELEASE_TIMESTAMP}" =~ ^[0-9]{6}\.[0-9]{6}$ ]]; then
  echo "error: RELEASE_TIMESTAMP must use YYMMDD.HHMMSS format" >&2
  exit 2
fi

cd "${REPO_ROOT}"

IMAGE_PATH="$(python3 scripts/image_metadata.py path --image-tag "${IMAGE_TAG}" --image-key "${IMAGE_KEY}")"
BASE_IMAGE="$(python3 scripts/image_metadata.py base-image --image-tag "${IMAGE_TAG}" --image-key "${IMAGE_KEY}")"
scripts/prepare_image_context.sh "${IMAGE_PATH}"

tag_args=()
while IFS= read -r image_tag; do
  tag_args+=("-t" "${image_tag}")
done < <(python3 scripts/image_metadata.py tags \
  --image-tag "${IMAGE_TAG}" \
  --image-key "${IMAGE_KEY}" \
  --repositories "${IMAGE_REPOSITORIES}" \
  --tag-suffix="-r${RELEASE_TIMESTAMP}" \
  --include-base-tags \
  --include-latest \
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
