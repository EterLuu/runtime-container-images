#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: IMAGE_REPOSITORY=<repository> [IMAGE_KEY=<images/...>] [PLATFORM=<platform>] scripts/build_image.sh <image-tag>

Build one runtime image locally without pushing it.

Examples:
  IMAGE_REPOSITORY=modelarts-cann scripts/build_image.sh 9.0.0-910b-ubuntu22.04
  IMAGE_REPOSITORY=ghcr.io/acme/modelarts-cuda scripts/build_image.sh 12.6.1-v100-ubuntu24.04
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
IMAGE_TAG="$1"
IMAGE_KEY="${IMAGE_KEY:-}"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-runtime-image}"
PLATFORM="${PLATFORM:-}"

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
  --repositories "${IMAGE_REPOSITORY}" \
  --format newline)

build_args=()
if [[ -n "${PLATFORM}" ]]; then
  build_args+=("--platform" "${PLATFORM}")
fi

set -x
docker build \
  "${build_args[@]}" \
  --build-arg "BASE_IMAGE=${BASE_IMAGE}" \
  "${tag_args[@]}" \
  -f "${IMAGE_PATH}/Dockerfile" \
  "${IMAGE_PATH}"
