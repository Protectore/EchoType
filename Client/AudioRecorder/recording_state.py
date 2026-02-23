from enum import Enum


class RecordingState(Enum):
    """Состояния записи"""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
