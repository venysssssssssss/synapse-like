# Troubleshooting

## No devices listed
- Check USB IDs: `lsusb | grep -i razer`
- Daemon status: `systemctl --user status openrazer-daemon`
- Reload udev: `sudo udevadm control --reload-rules && sudo udevadm trigger`
- Unplug/plug the device after installing OpenRazer.

## Permission denied
- Ensure user is in `plugdev`: `groups | grep plugdev`
- If not, `sudo gpasswd -a $USER plugdev` and re-login.

## Python bindings missing
- Package name is typically `python3-openrazer` (Debian/Ubuntu).
- If still missing, CLI will run in mock mode (no devices shown). Install system package to control hardware.

## Applying settings does nothing
- Confirm the capability exists via `synapse capabilities 0`.
- Not all devices expose DPI/polling; lighting modes vary. OpenRazer may require specific effect names per device.
- Check logs: run CLI with `RUST_LOG=debug` (if you add logging) or watch `journalctl --user -u openrazer-daemon`.

## GUI abre com erro Qt xcb plugin
- Instale dependencias Qt/XCB:
  - Debian/Ubuntu/Kali: `sudo apt install libxcb-cursor0`

## Permission denied em /dev/input/by-id ou /dev/uinput
- Aplique ACL temporaria:
  - `sudo setfacl -m u:$USER:rw /dev/input/by-id/*Razer*event* /dev/uinput`
- Para persistencia, configure regra `udev`.

## Icone nao aparece no dock/menu
- Reinstale desktop entry e icone:
  - `./scripts/install_linux.sh`
- Reinicie shell do desktop ou logout/login.
- Em GNOME, limpe cache de apps se necessario:
  - `update-desktop-database ~/.local/share/applications`

## Launcher nao encontrado
- Confirme `~/.local/bin` no PATH:
  - `echo $PATH`
- Se faltar, adicione no `~/.bashrc`:
  - `export PATH="$HOME/.local/bin:$PATH"`
