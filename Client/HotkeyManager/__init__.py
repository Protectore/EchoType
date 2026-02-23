"""
Менеджер горячих клавиш для голосового клиента

Этот пакет предоставляет функциональность для управления горячими клавишами:
- Регистрация и удаление горячих клавиш
- Поддержка Toggle и Push-to-Talk режимов
- Обнаружение конфликтов клавиш
- Обработка комбинаций клавиш
"""

from .hotkey_manager import HotkeyManager
from .hotkey_action import HotkeyAction
from .hotkey_mode import HotkeyMode
from .hotkey_state import HotkeyState

__all__ = [
    'HotkeyManager',
    'HotkeyAction', 
    'HotkeyMode',
    'HotkeyState'
]