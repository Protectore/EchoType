import sys

from PyQt6.QtWidgets import (
    QKeySequenceEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QKeySequence

from logger import get_logger


logger = get_logger(__name__)


class HotkeyEdit(QKeySequenceEdit):
    """Виджет редактирования горячей клавиши"""
    
    def __init__(self, hotkey_str: str = "", parent=None):
        super().__init__(parent)
        self.exception_key = None
        if hotkey_str:
            self.setKeySequence(QKeySequence(hotkey_str.replace("_", "+")))

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        
        extra_solo_keys = [Qt.Key.Key_Alt, Qt.Key.Key_Control, Qt.Key.Key_Shift]
        
        if key in extra_solo_keys:
            if sys.platform == 'win32':
                native_key = event.nativeScanCode()

                logger.debug(f"{key=}, {native_key=}")
                
                # ALT
                if native_key == 56:
                    self.exception_key = "alt_l"
                elif native_key == 57400:
                    self.exception_key = "alt_gr"
                self.setKeySequence(QKeySequence(key))
            else:
                # Для Linux/Mac вероятно, будут другие коды
                self.setKeySequence(QKeySequence(key))
            
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def get_hotkey_string(self) -> str:
        """Получить строковое представление горячей клавиши"""
        seq = self.keySequence()
        if seq.isEmpty():
            return ""
        # Если были нажаты левые/правые альты и т.д., которые pyqt нативно не различает
        if seq.count() == 1 and self.exception_key:
            return self.exception_key
        # Конвертируем в формат для pynput
        return seq.toString().lower().replace("+", "_")
