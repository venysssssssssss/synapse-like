#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
ENTRY_FILE="$PROJECT_ROOT/scripts/gui_entry.py"

if [[ -n "${RELEASE_VERSION:-}" ]]; then
    VERSION="${RELEASE_VERSION#v}"
else
    VERSION="$(python3 - <<'PY'
import pathlib
import tomllib

data = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))
print(data["tool"]["poetry"]["version"])
PY
)"
fi

BIN_NAME="synapse-like"
OUTPUT_NAME="synapse-like-${VERSION}-linux-x86_64"
OUTPUT_BIN="$DIST_DIR/$OUTPUT_NAME"
CHECKSUM_FILE="$OUTPUT_BIN.sha256"

mkdir -p "$DIST_DIR"
rm -f "$OUTPUT_BIN" "$CHECKSUM_FILE"
rm -rf "$BUILD_DIR"

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "pyinstaller nao encontrado. Instale com: python3 -m pip install pyinstaller"
    exit 1
fi

pyinstaller \
    --noconfirm \
    --clean \
    --onefile \
    --windowed \
    --name "$BIN_NAME" \
    --paths "$PROJECT_ROOT/src" \
    --collect-all PySide6 \
    "$ENTRY_FILE"

mv "$DIST_DIR/$BIN_NAME" "$OUTPUT_BIN"
chmod +x "$OUTPUT_BIN"
sha256sum "$OUTPUT_BIN" > "$CHECKSUM_FILE"

echo "Executavel gerado:"
echo "- $OUTPUT_BIN"
echo "- $CHECKSUM_FILE"
