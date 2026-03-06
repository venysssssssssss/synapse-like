import logging
from dataclasses import dataclass
from typing import List, Optional

from synapse_like.gui.device_paths import detect_razer_devices, card_name, path_kind

logger = logging.getLogger(__name__)

@dataclass
class DeviceInfo:
    path: str
    name: str
    kind: str
    # Futuro: adicionar vid, pid, serial aqui

class DeviceManager:
    """
    Responsavel por detectar, enumerar e fornecer detalhes sobre
    dispositivos compativeis.
    
    Segue o principio SRP: A GUI nao precisa saber como listar arquivos em /dev/input.
    """
    
    def __init__(self):
        self._devices: List[DeviceInfo] = []

    def scan(self) -> List[DeviceInfo]:
        """Varre o sistema em busca de dispositivos Razer."""
        raw_paths = detect_razer_devices()
        self._devices = []
        
        for path in raw_paths:
            # Aqui futuramente entra a logica de agrupar interfaces pai/filho
            # e leitura de udev properties.
            info = DeviceInfo(
                path=path,
                name=card_name(path),
                kind=path_kind(path)
            )
            self._devices.append(info)
            
        return self._devices

    def get_primary_devices(self) -> List[DeviceInfo]:
        """Retorna apenas dispositivos que parecem ser interfaces principais (kbd/mouse)."""
        if not self._devices:
            self.scan()
            
        primary = []
        for dev in self._devices:
            if dev.path.endswith("-event-kbd") or dev.path.endswith("-event-mouse"):
                primary.append(dev)
        
        return primary if primary else self._devices[:4]

    def get_device_by_path(self, path: str) -> Optional[DeviceInfo]:
        for dev in self._devices:
            if dev.path == path:
                return dev
        return None

    def validate_path(self, path: str) -> bool:
        """Verifica se o path ainda e valido/existe."""
        # Implementar checagem de existencia de arquivo
        import os
        return os.path.exists(path)