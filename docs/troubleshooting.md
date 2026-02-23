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
