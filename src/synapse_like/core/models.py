from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class DeviceType(str, Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    HEADSET = "headset"
    UNKNOWN = "unknown"

@dataclass
class LightingCapabilities:
    modes: List[str]
    brightness: bool

@dataclass
class MacroCapabilities:
    supported: bool
    notes: Optional[str] = None

@dataclass
class DeviceCapabilities:
    device_id: str
    type: DeviceType
    lighting: Optional[LightingCapabilities] = None
    dpi: Optional[bool] = None  # True if supported
    polling_rate: Optional[bool] = None # True if supported
    macros: Optional[MacroCapabilities] = None

@dataclass
class Device:
    name: str
    capabilities: DeviceCapabilities
    serial: Optional[str] = None
    # We might add current state here later or keep it separate

@dataclass
class ProfileSetting:
    lighting: Optional[Dict[str, Any]] = None
    dpi: Optional[int] = None
    polling_rate: Optional[int] = None

@dataclass
class Profile:
    schema_version: int
    name: str
    targets: List[str]  # List of device_ids this profile applies to
    settings: Dict[str, Dict[str, Any]]  # device_id -> settings dict
