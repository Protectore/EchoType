"""
Tray-апплет для EchoType

Модуль содержит системный трей с контекстным меню для управления приложением.
"""

from .tray_app import TrayApp
from .tray_status import TrayStatus

__all__ = ['TrayApp', 'TrayStatus']