#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PREFIX="${PREFIX:-$HOME/.local/opt/synapse-like}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA_DIR/applications"
ICON_DIR="$DATA_DIR/icons/hicolor/scalable/apps"
VENV_DIR="$PREFIX/.venv"
SRC_DIR="$PREFIX/src"
LAUNCHER="$BIN_DIR/synapse-like"
DESKTOP_FILE="$APP_DIR/synapse-like.desktop"
ICON_FILE="$ICON_DIR/synapse-like.svg"

WITH_SYSTEM_DEPS=0

usage() {
    cat <<EOF
Usage: $(basename "$0") [options]

Instala o Synapse-Like no Linux em modo user-local (sem root por padrao).

Options:
  --prefix <path>         Prefixo da instalacao (default: $PREFIX)
  --with-system-deps      Instala dependencias de sistema via apt (requer sudo)
  -h, --help              Mostra esta ajuda
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            PREFIX="$2"
            shift 2
            ;;
        --with-system-deps)
            WITH_SYSTEM_DEPS=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Opcao invalida: $1"
            usage
            exit 1
            ;;
    esac
done

VENV_DIR="$PREFIX/.venv"
SRC_DIR="$PREFIX/src"

if [[ $WITH_SYSTEM_DEPS -eq 1 ]]; then
    if command -v apt-get >/dev/null 2>&1; then
        echo "[1/6] Instalando dependencias de sistema (apt)..."
        sudo apt-get update
        sudo apt-get install -y \
            python3 \
            python3-venv \
            python3-pip \
            libxcb-cursor0 \
            openrazer-meta \
            python3-openrazer
    else
        echo "apt-get nao encontrado. Instale dependencias manualmente."
        exit 1
    fi
fi

echo "[2/6] Preparando diretorios..."
mkdir -p "$PREFIX" "$BIN_DIR" "$APP_DIR" "$ICON_DIR"

echo "[3/6] Copiando codigo para $SRC_DIR..."
rm -rf "$SRC_DIR"
mkdir -p "$SRC_DIR"
tar \
    --exclude=".git" \
    --exclude=".venv" \
    --exclude="dist" \
    --exclude="__pycache__" \
    --exclude=".pytest_cache" \
    --exclude=".mypy_cache" \
    -cf - -C "$PROJECT_ROOT" . | tar -xf - -C "$SRC_DIR"

echo "[4/6] Criando virtualenv e instalando pacote..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel >/dev/null
"$VENV_DIR/bin/pip" install "$SRC_DIR" >/dev/null

echo "[5/6] Criando launcher..."
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$VENV_DIR/bin/synapse" gui "\$@"
EOF
chmod +x "$LAUNCHER"

echo "[6/6] Instalando icone e launcher desktop..."
cp "$SRC_DIR/assets/icons/synapse-like.svg" "$ICON_FILE"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Synapse-Like
Comment=Open-source Synapse-like for Linux
Exec=$LAUNCHER
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

echo
echo "Instalacao concluida."
echo "- Executavel: $LAUNCHER"
echo "- Desktop:    $DESKTOP_FILE"
echo "- Prefixo:    $PREFIX"
echo
echo "Permissoes recomendadas para remap:"
echo "  sudo setfacl -m u:\$USER:rw /dev/input/by-id/*Razer*event* /dev/uinput"
