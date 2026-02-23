from enum import Enum


class HotkeyMode(Enum):
    """Режимы работы горячей клавиши"""
    TOGGLE = "toggle"          # Нажатие включает/выключает
    PUSH_TO_TALK = "ptt"       # Удержание для записи
