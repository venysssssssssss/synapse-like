import typer
from rich.console import Console
from rich.table import Table

from synapse_like.core.profiles import load_profile
from synapse_like.gui import launch as launch_gui

app = typer.Typer()
console = Console()
adapter = None


def get_adapter():
    global adapter
    if adapter is None:
        from synapse_like.adapters.openrazer import OpenRazerAdapter

        adapter = OpenRazerAdapter()
    return adapter


@app.command()
def devices():
    """List connected Razer devices."""
    devices = get_adapter().list_devices()
    if not devices:
        console.print("No Razer devices found (or OpenRazer bindings missing).", style="yellow")
        return

    table = Table(title="Connected Devices")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Serial", style="green")
    table.add_column("Capabilities", style="yellow")

    for dev in devices:
        caps = []
        if dev.capabilities.lighting:
            caps.append("Lighting")
        if dev.capabilities.dpi:
            caps.append("DPI")
        if dev.capabilities.polling_rate:
            caps.append("Polling")
        if dev.capabilities.macros and dev.capabilities.macros.supported:
            caps.append("Macros")

        table.add_row(dev.name, dev.capabilities.type.value, dev.serial, ", ".join(caps))

    console.print(table)


@app.command()
def capabilities(device_index: int):
    """Show detailed capabilities for a device by index (from 'devices' list)."""
    devices = get_adapter().list_devices()
    if not devices:
        console.print("No devices found.", style="red")
        return

    if device_index < 0 or device_index >= len(devices):
        console.print(f"Invalid device index: {device_index}", style="red")
        return

    dev = devices[device_index]
    console.print(f"[bold]Capabilities for {dev.name}:[/bold]")
    console.print(dev.capabilities)

@app.command()
def apply(profile_name: str):
    """Apply a profile to connected devices."""
    profile = load_profile(profile_name)
    if not profile:
        console.print(f"Profile '{profile_name}' not found.", style="red")
        return

    console.print(f"Applying profile '{profile_name}'...")
    get_adapter().apply_profile(profile)
    console.print("Profile applied.", style="green")


@app.command()
def gui():
    """Launch GUI remapper (PySide6)."""
    launch_gui()


if __name__ == "__main__":
    app()
