#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"

if [[ -n "${RELEASE_VERSION:-}" ]]; then
    VERSION="${RELEASE_VERSION#v}"
else
    VERSION="$(python3 - <<'PY'
import pathlib
import tomllib

pyproject = pathlib.Path("pyproject.toml")
data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
print(data["tool"]["poetry"]["version"])
PY
)"
fi

PKG_NAME="synapse-like-${VERSION}-linux"
STAGE_ROOT="$(mktemp -d)"
STAGE_DIR="$STAGE_ROOT/$PKG_NAME"
ARCHIVE="$DIST_DIR/${PKG_NAME}.tar.gz"
CHECKSUM="$ARCHIVE.sha256"

mkdir -p "$DIST_DIR" "$STAGE_DIR"

tar \
    --exclude=".git" \
    --exclude=".venv" \
    --exclude="dist" \
    --exclude="__pycache__" \
    --exclude=".pytest_cache" \
    --exclude=".mypy_cache" \
    -cf - -C "$PROJECT_ROOT" . | tar -xf - -C "$STAGE_DIR"

(
    cd "$STAGE_ROOT"
    tar -czf "$ARCHIVE" "$PKG_NAME"
)

sha256sum "$ARCHIVE" > "$CHECKSUM"
rm -rf "$STAGE_ROOT"

echo "Release gerado:"
echo "- $ARCHIVE"
echo "- $CHECKSUM"
