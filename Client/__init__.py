"""
VoiceClient - модуль записи и обработки голоса
"""

from .hotkey_manager import HotkeyManager, HotkeyMode, HotkeyAction
from .client import Client

__all__ = [
    'HotkeyManager',
    'HotkeyMode',
    'HotkeyAction',
    'Client'
]
