import sys

from PyQt6.QtWidgets import (
    QKeySequenceEdit,
    QLineEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QKeySequence

from Utility import get_logger


logger = get_logger(__name__)

# Маппинг для отображения специальных клавиш
SPECIAL_KEY_DISPLAY = {
    "alt_l": "Alt (Left)",
    "alt_gr": "Alt_Gr",
    "alt_r": "Alt (Right)",
    "ctrl_l": "Ctrl (Left)",
    "ctrl_r": "Ctrl (Right)",
    "shift_l": "Shift (Left)",
    "shift_r": "Shift (Right)",
}


class HotkeyEdit(QKeySequenceEdit):
    """Виджет редактирования горячей клавиши"""
    
    def __init__(self, hotkey_str: str = "", parent=None):
        super().__init__(parent)
        self.exception_key = None
        if hotkey_str:
            self.setHotkeyFromString(hotkey_str)
    
    def _setDisplayText(self, text: str):
        """Установить текст отображения в внутреннем QLineEdit"""
        line_edit = self.findChild(QLineEdit)
        if line_edit:
            line_edit.setText(text)
    
    def setHotkeyFromString(self, hotkey_str: str):
        """Установить горячую клавишу из строки с поддержкой специальных клавиш"""
        if hotkey_str in SPECIAL_KEY_DISPLAY:
            self.exception_key = hotkey_str
            self._setDisplayText(SPECIAL_KEY_DISPLAY[hotkey_str])
        else:
            self.exception_key = None
            self.setKeySequence(QKeySequence(hotkey_str.replace("_", "+")))

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        
        extra_solo_keys = [Qt.Key.Key_Alt, Qt.Key.Key_Control, Qt.Key.Key_Shift]
        
        if key in extra_solo_keys:
            if sys.platform == 'win32':
                native_key = event.nativeScanCode()

                logger.debug(f"{key=}, {native_key=}")
                
                if native_key in [56, 57400]:
                    exception_key = None
                    # ALT
                    if native_key == 56:
                        exception_key = "alt_l"
                    elif native_key == 57400:
                        exception_key = "alt_gr"
                    self.exception_key = exception_key
                    self._setDisplayText(SPECIAL_KEY_DISPLAY[exception_key]) # type: ignore
                else:
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
