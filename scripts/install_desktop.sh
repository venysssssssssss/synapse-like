#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_DIR/applications"
ICON_DIR="$DATA_DIR/icons/hicolor/scalable/apps"
DESKTOP_FILE="$APP_DIR/synapse-like.desktop"
ICON_FILE="$ICON_DIR/synapse-like.svg"

mkdir -p "$APP_DIR" "$ICON_DIR"
cp "$PROJECT_ROOT/assets/icons/synapse-like.svg" "$ICON_FILE"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Synapse-Like
Comment=Open-source Synapse-like for Linux
Exec=bash -lc "cd '$PROJECT_ROOT' && poetry run synapse gui"
Path=$PROJECT_ROOT
Icon=synapse-like
Terminal=false
Categories=Settings;Utility;
Keywords=Razer;Synapse;Keyboard;Mouse;Remap;
StartupNotify=true
StartupWMClass=Synapse-Like
EOF

chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

echo "Desktop entry instalado em: $DESKTOP_FILE"
echo "Icone instalado em: $ICON_FILE"
