# Instalacao Linux (detalhada)

Este projeto suporta instalacao local de usuario (sem root por padrao), com:

- launcher `synapse-like` em `~/.local/bin`
- atalho de menu `.desktop`
- icone instalado no tema local
- ambiente Python isolado em `~/.local/opt/synapse-like`

## 1) Requisitos

Minimo:

- Linux desktop (X11 ou Wayland)
- Python 3.12+
- `python3-venv`

Recomendado para hardware Razer:

- `openrazer-meta`
- `python3-openrazer`
- `libxcb-cursor0` (Qt/XCB)

## 2) Instalacao rapida (a partir do repo)

```bash
cd /home/kali/BIG/synapse-like
./scripts/install_linux.sh
```

Com dependencias de sistema via apt:

```bash
./scripts/install_linux.sh --with-system-deps
```

## 3) Instalacao a partir de release (download)

Opcao 1 (recomendada): arquivo executavel unico.

Depois de baixar `synapse-like-<versao>-linux-x86_64` da aba **Releases**:

```bash
chmod +x synapse-like-<versao>-linux-x86_64
./synapse-like-<versao>-linux-x86_64
```

Opcao 2: pacote fonte com instalador.

Depois de baixar `synapse-like-<versao>-linux.tar.gz`:

```bash
tar -xzf synapse-like-<versao>-linux.tar.gz
cd synapse-like-<versao>-linux
./scripts/install_linux.sh
```

## 4) Executar

Via menu do sistema:

- Abra o menu de aplicativos e procure por `Synapse-Like`.

Via terminal:

```bash
~/.local/bin/synapse-like
```

## 5) Remover instalacao

```bash
./scripts/uninstall_linux.sh
```

## 6) Permissoes para remap (uinput / input events)

Para evitar `Permission denied`, aplique ACL:

```bash
sudo setfacl -m u:$USER:rw /dev/input/by-id/*Razer*event* /dev/uinput
```

Se quiser persistencia completa, use regra `udev` (recomendado em producao).

## 7) Locais instalados

- Prefixo: `~/.local/opt/synapse-like`
- Launcher: `~/.local/bin/synapse-like`
- Desktop entry: `~/.local/share/applications/synapse-like.desktop`
- Icone: `~/.local/share/icons/hicolor/scalable/apps/synapse-like.svg`

## 8) Atualizacao de versao

Re-execute:

```bash
./scripts/install_linux.sh
```

O instalador sobrescreve a versao instalada no prefixo atual.
