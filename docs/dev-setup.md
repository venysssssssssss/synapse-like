# Dev Setup (Kali/Ubuntu-like)

## Prereqs
- Python 3.12+
- Poetry (`pip install poetry`)
- OpenRazer driver + daemon (system package)
  - On Debian/Ubuntu/Kali: `sudo apt install openrazer-meta`
  - Add user to `plugdev`: `sudo gpasswd -a $USER plugdev` then re-log

## Install project deps
```bash
poetry install
```

## Run checks
```bash
poetry run synapse devices
```
Should list the Razer devices detected by OpenRazer. If none appear, verify the daemon and udev rules (see troubleshooting).

## Structure (MVP)
- `src/synapse_like/core`: models, profile storage
- `src/synapse_like/adapters/openrazer`: hardware adapter
- `src/synapse_like/cli`: Typer CLI entry (`synapse`)
- `scripts/demo.py`: quick manual test without Typer

## Useful services
- Start daemon: `systemctl --user start openrazer-daemon`
- Enable on login: `systemctl --user enable openrazer-daemon`
