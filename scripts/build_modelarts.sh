#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: IMAGE_REPOSITORY=<repository> [PLATFORM=<platform>] scripts/build_modelarts.sh <modelarts-tag>

Build one ModelArts image locally without pushing it.

Examples:
  IMAGE_REPOSITORY=modelarts-cann scripts/build_modelarts.sh 9.0.0-910b-ubuntu22.04
  IMAGE_REPOSITORY=ghcr.io/acme/modelarts-cann PLATFORM=linux/arm64 scripts/build_modelarts.sh 9.0.0-910b-ubuntu22.04
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODELARTS_TAG="$1"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-modelarts-cann}"
PLATFORM="${PLATFORM:-}"

cd "${REPO_ROOT}"

IMAGE_PATH="$(python3 scripts/modelarts_metadata.py path --modelarts-tag "${MODELARTS_TAG}")"
BASE_IMAGE="$(python3 scripts/modelarts_metadata.py base-image --modelarts-tag "${MODELARTS_TAG}")"
scripts/prepare_modelarts_context.sh "${IMAGE_PATH}"

tag_args=()
while IFS= read -r image_tag; do
  tag_args+=("-t" "${image_tag}")
done < <(python3 scripts/modelarts_metadata.py tags \
  --modelarts-tag "${MODELARTS_TAG}" \
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
