#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: scripts/prepare_image_context.sh <image-context> [<image-context>...]

Copy shared runtime scripts from the image flavor directory into each Docker build context.
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
for context in "$@"; do
  CONTEXT_DIR="${context}"
  if [[ "${CONTEXT_DIR}" != /* ]]; then
    CONTEXT_DIR="${REPO_ROOT}/${CONTEXT_DIR}"
  fi

  if [[ ! -d "${CONTEXT_DIR}" ]]; then
    echo "error: image context directory not found: ${CONTEXT_DIR}" >&2
    exit 1
  fi

  SOURCE_DIR="$(dirname "${CONTEXT_DIR}")/scripts"
  if [[ ! -d "${SOURCE_DIR}" ]]; then
    continue
  fi

  TARGET_DIR="${CONTEXT_DIR}/scripts"
  if [[ "${TARGET_DIR}" == "${SOURCE_DIR}" ]]; then
    echo "error: refusing to overwrite shared scripts directory: ${SOURCE_DIR}" >&2
    exit 1
  fi

  rm -rf "${TARGET_DIR}"
  mkdir -p "${TARGET_DIR}"
  cp -a "${SOURCE_DIR}/." "${TARGET_DIR}/"
done
