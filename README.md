# Synapse-Like for Linux (Open Source)

**Target (verified via `lsusb`)**
- Keyboard: `1532:011a` — Razer BlackWidow Ultimate 2013
- Mouse: `1532:0016` — Razer DeathAdder 3.5G (RZ01-0015)

## 1) Objective
Build an open-source "Synapse-like" for Linux, reimplementing the experience (profiles, configs, lighting, DPI/polling) using **OpenRazer** as a base (driver + daemon), with a scalable and testable architecture.

## 2) Scope

### MVP (First Usable Delivery)
- Detect devices and display **capabilities**
- Apply basic configurations:
  - Lighting (when supported by device/driver)
  - DPI / polling rate (when exposed)
- **Local Profiles**: create/save/load/apply
- CLI for debug + simple automation
- Diagnostic bundle (IDs, capabilities, logs)

## 3) Architecture

1.  **Adapter (OpenRazer)**: Interface with hardware.
2.  **Core (Hardware Agnostic)**: Models for Device, Capabilities, Profile.
3.  **Service**: User-level daemon (M2).
4.  **UI**: CLI (M1), GUI (M2).

## 4) Stack
- **Language**: Python 3.12+
- **Dependency Management**: Poetry
- **CLI**: Typer
- **GUI**: PySide6 (planned for M2)
- **Driver Interface**: OpenRazer

## Quick start (MVP)
```bash
poetry install
poetry run synapse devices          # list connected devices
poetry run synapse capabilities 0   # show capabilities of first device
poetry run synapse apply <profile>  # apply saved profile (see docs)
poetry run synapse gui              # launch remap GUI (auto-detects Razer input paths)
```

More details in `docs/dev-setup.md` and `docs/troubleshooting.md`.

### Remap GUI (experimental)
- Needs access to `/dev/input/*` and `/dev/uinput` (run as root or add udev rules).
- Razer devices are auto-listed from `/dev/input/by-id/*Razer*`; pick keyboard or mouse from the dropdown or type a custom path.
- Click keys (including M1-M5 and numpad) or mouse buttons (LMB/MMB/RMB/M4/M5), set actions (keystroke, scroll, side buttons), save/load mappings, and click **Aplicar** to start the uinput remapper.
- `Mapear M-X (escutar)` calibrates `M5 -> M4 -> M3 -> M2 -> M1` quickly.
- `Mapear teclado completo (ID)` captures every key in sequence and stores exact event IDs (symbolic + numeric) per key slot for precise remap.
- Scroll remaps emit through a dedicated virtual pointer and matching supports both `EV_KEY` and `MSC_SCAN` IDs (example: `70068`, `70069`).

## Usage
(Instructions to be added)
# synapse-like
