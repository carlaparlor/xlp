#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${REPO_ROOT}/.githooks"
DST_DIR="${REPO_ROOT}/.git/hooks"

if [[ ! -d "${DST_DIR}" ]]; then
  echo "Error: '${DST_DIR}' does not exist. Run inside a Git repository." >&2
  exit 1
fi

for hook in pre-commit commit-msg pre-push; do
  if [[ ! -f "${SRC_DIR}/${hook}" ]]; then
    echo "Error: missing versioned hook '${SRC_DIR}/${hook}'." >&2
    exit 1
  fi
  cp "${SRC_DIR}/${hook}" "${DST_DIR}/${hook}"
  chmod +x "${DST_DIR}/${hook}"
  echo "Installed .git/hooks/${hook}"
done

echo "XLP Git enforcement hooks installed successfully."
