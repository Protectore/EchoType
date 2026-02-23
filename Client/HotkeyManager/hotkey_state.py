from typing import Optional, Set
from dataclasses import dataclass, field
from pynput import keyboard
from logger import get_logger


logger = get_logger(__name__)


@dataclass
class HotkeyState:
    """Состояние отслеживания клавиш"""
    pressed_keys: Set[ keyboard.Key | keyboard.KeyCode] = field(default_factory=set)
    active_hotkey: Optional[str] = None

    def add_key(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        logger.info(type(key))
        if isinstance(key, keyboard.KeyCode) and key.char:
            # Скипаем управляющие символы (Ctrl+A и т.д.)
            if not key.char.isalnum() or key.char.isupper():
                logger.debug(f"Skipped {key.char=}")
                return

        self.pressed_keys.add(key)
    
    def discard_key(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        self.pressed_keys.discard(key)

    def clear(self) -> None:
        self.pressed_keys.clear()
