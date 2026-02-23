#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local/opt/synapse-like}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_DIR/applications"
ICON_DIR="$DATA_DIR/icons/hicolor/scalable/apps"

LAUNCHER="$BIN_DIR/synapse-like"
DESKTOP_FILE="$APP_DIR/synapse-like.desktop"
ICON_FILE="$ICON_DIR/synapse-like.svg"

echo "Removendo instalacao do Synapse-Like..."
rm -f "$LAUNCHER"
rm -f "$DESKTOP_FILE"
rm -f "$ICON_FILE"
rm -rf "$PREFIX"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

echo "Remocao concluida."
