from enum import Enum


class TrayStatus(Enum):
    """Статусы tray-иконки"""
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"
