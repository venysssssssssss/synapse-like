import os
import sys

# Ensure we can import the src/ package when running from repo root
sys.path.append(os.path.join(os.getcwd(), "src"))

from synapse_like.adapters.openrazer import OpenRazerAdapter
from synapse_like.core.models import Device

def main():
    print("Initializing Adapter...")
    adapter = OpenRazerAdapter()
    
    print("Listing Devices...")
    devices = adapter.list_devices()
    
    if not devices:
        print("No devices found (or OpenRazer bindings missing/mock mode active without devices).")
    else:
        for dev in devices:
            print(f"Device: {dev.name} ({dev.serial})")
            print(f"  Type: {dev.capabilities.type.value}")
            if dev.capabilities.lighting:
                print(f"  Lighting: {dev.capabilities.lighting.modes}")
            if dev.capabilities.dpi:
                print(f"  DPI: Supported")

if __name__ == "__main__":
    main()
