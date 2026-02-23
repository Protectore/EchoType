from typing import Optional, Callable, Tuple
from dataclasses import dataclass
from pynput import keyboard

from Client.HotkeyManager.hotkey_mode import HotkeyMode


@dataclass
class HotkeyAction:
    """Описание действия горячей клавиши"""
    name: str                              # Имя действия
    keys: Tuple[keyboard.Key | keyboard.KeyCode, ...]  # Комбинация клавиш
    callback: Callable[[], None]           # Функция при активации
    mode: HotkeyMode = HotkeyMode.TOGGLE   # Режим работы
    description: str = ""                  # Описание для UI
    on_release: Optional[Callable[[], None]] = None  # Для PTT - при отпускании
