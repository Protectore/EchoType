"""
VoiceClient - модуль записи и обработки голоса
"""

from Client.audio_recorder import AudioRecorder, AudioData, RecordingState
from Client.hotkey_manager import HotkeyManager, HotkeyMode, HotkeyAction
from Client.client import Client

__all__ = [
    'AudioRecorder',
    'AudioData',
    'RecordingState',
    'HotkeyManager',
    'HotkeyMode',
    'HotkeyAction',
    'Client'
]
