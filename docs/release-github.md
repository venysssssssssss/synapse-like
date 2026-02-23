# Publicacao no GitHub (Releases com download)

Este fluxo deixa o download disponivel direto no repositorio.

## 1) O que ja esta configurado

- Workflow: `.github/workflows/release.yml`
- Build de pacote Linux: `scripts/build_release.sh`
- Build de executavel unico: `scripts/build_executable.sh`
- Assets publicados automaticamente:
  - `dist/synapse-like-<versao>-linux-x86_64`
  - `dist/synapse-like-<versao>-linux-x86_64.sha256`
  - `dist/synapse-like-<versao>-linux.tar.gz`
  - `dist/synapse-like-<versao>-linux.tar.gz.sha256`

## 2) Processo de release

1. Ajuste versao no `pyproject.toml` (`tool.poetry.version`).
2. Commit das alteracoes.
3. Crie tag semantica iniciando com `v`.

Exemplo:

```bash
git add .
git commit -m "release: v0.2.0"
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

## 3) Resultado esperado

Quando a tag `v*` for enviada:

- GitHub Actions executa o workflow `release`
- gera o tarball Linux e o executavel usando a versao da tag
- cria/atualiza a release no GitHub
- anexa os arquivos para download

## 4) Verificacao de integridade

Depois de baixar os arquivos:

```bash
sha256sum -c synapse-like-<versao>-linux-x86_64.sha256
sha256sum -c synapse-like-<versao>-linux.tar.gz.sha256
```

Deve retornar `OK`.

## 5) Build local manual (sem GitHub Actions)

```bash
./scripts/build_release.sh
./scripts/build_executable.sh
```

Arquivos serao gerados em `dist/`.
