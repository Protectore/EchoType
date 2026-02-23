from typing import Optional, Set
from dataclasses import dataclass, field
from pynput import keyboard
from logger import get_logger


logger = get_logger(__name__)


@dataclass
class HotkeyState:
    """Состояние отслеживания клавиш. Хранит в себе текущие нажатые клавиши"""
    pressed_keys: Set[keyboard.Key | keyboard.KeyCode] = field(default_factory=set)
    active_action_name: Optional[str] = None

    def add_key(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Добавить клавишу к текущим нажатым клавишам"""
        logger.debug(f"Добавлена клавиша {key} ({type(key)}), текущее состояние: {self.pressed_keys}")
        if isinstance(key, keyboard.KeyCode) and key.char:
            # Скипаем управляющие символы (Ctrl+A и т.д.)
            if not key.char.isalnum() or key.char.isupper():
                logger.debug(f"Skipped {key.char=}")
                return

        self.pressed_keys.add(key)
    
    def discard_key(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """Убрать клавишу из нажатых"""
        logger.debug(f"Удалена клавиша {key}, текущее состояние: {self.pressed_keys}")
        self.pressed_keys.discard(key)

    def clear(self) -> None:
        """Очистить нажатые клавиши"""
        self.pressed_keys.clear()
