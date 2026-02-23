# Synapse-Like for Linux

Open-source alternativa ao Razer Synapse para Linux, com foco em remap de teclas/botoes, perfis locais e base para integracao OpenRazer.

## Status atual

- GUI de remap funcional (teclado + mouse)
- suporte a M-keys (M1/M2 confirmados como F13/F14 em BlackWidow Ultimate)
- perfis de mapping em JSON
- modo de baixa latencia para remap de scroll/botoes auxiliares
- detecao automatica de paths Razer em `/dev/input/by-id`

## Instalacao (Linux)

### Opcao A: instalacao local (recomendada)

```bash
./scripts/install_linux.sh
```

Com dependencias de sistema via apt:

```bash
./scripts/install_linux.sh --with-system-deps
```

Documentacao completa: `docs/install-linux.md`

### Opcao B: modo dev com Poetry

```bash
poetry install
poetry run synapse gui
```

## Execucao

Depois de instalado:

```bash
~/.local/bin/synapse-like
```

ou abra pelo menu do sistema: **Synapse-Like**

## Comandos CLI

```bash
poetry run synapse devices
poetry run synapse capabilities 0
poetry run synapse apply <profile>
poetry run synapse gui
```

## Permissoes (importante para remap)

Para ler `event*` e escrever em `uinput`:

```bash
sudo setfacl -m u:$USER:rw /dev/input/by-id/*Razer*event* /dev/uinput
```

## Estrutura principal

- `src/synapse_like/gui/` - interface e fluxo de remap
- `src/synapse_like/remap/` - engine uinput/evdev
- `src/synapse_like/adapters/openrazer/` - adapter OpenRazer
- `scripts/install_linux.sh` - instalador Linux
- `scripts/uninstall_linux.sh` - desinstalador
- `scripts/build_release.sh` - gera pacote para release

## Download no GitHub Releases

Este repo inclui workflow para publicar artefatos de download em tags `v*`.

- Workflow: `.github/workflows/release.yml`
- Guia de release: `docs/release-github.md`
- Arquivo executavel unico (Linux): `synapse-like-<versao>-linux-x86_64`
- Pacote fonte: `synapse-like-<versao>-linux.tar.gz`

## Troubleshooting

Veja `docs/troubleshooting.md`.
