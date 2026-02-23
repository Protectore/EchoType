"""
Tray-апплет для EchoType
Иконка в системном трее с контекстным меню
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu
)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import QObject, pyqtSignal

from GUIClient.TrayApp.tray_status import TrayStatus


class TrayApp(QObject):
    """
    Tray-апплет для EchoType.
    Управляет иконкой в системном трее и контекстным меню.
    """
    
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._status = TrayStatus.READY
        
        self._init_tray()
        self._init_menu()
    
    def _init_tray(self):
        """Инициализация tray-иконки"""
        self.tray = QSystemTrayIcon()
        self.tray.setToolTip("EchoType - Готов к записи")
        self._update_icon()
        self.tray.activated.connect(self._on_activated)
    
    def _init_menu(self):
        """Инициализация контекстного меню"""
        self.menu = QMenu()
        
        # Настройки
        self.settings_action = QAction("⚙️ Настройки", self.menu)
        self.settings_action.triggered.connect(self._on_settings)
        self.menu.addAction(self.settings_action)
        
        self.menu.addSeparator()
        
        # Выход
        self.quit_action = QAction("❌ Выход", self.menu)
        self.quit_action.triggered.connect(self._on_quit)
        self.menu.addAction(self.quit_action)
        
        self.tray.setContextMenu(self.menu)
    
    def _create_icon(self, status: TrayStatus) -> QIcon:
        """Создать иконку для статуса"""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # Прозрачный фон
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Цвета для разных статусов
        colors = {
            TrayStatus.READY: QColor(76, 175, 80),      # Зелёный
            TrayStatus.RECORDING: QColor(244, 67, 54),  # Красный
            TrayStatus.PROCESSING: QColor(255, 193, 7), # Жёлтый
            TrayStatus.ERROR: QColor(158, 158, 158)     # Серый
        }
        
        color = colors.get(status, colors[TrayStatus.READY])
        
        # Рисуем круг
        painter.setBrush(color)
        painter.setPen(QColor(255, 255, 255))
        painter.drawEllipse(4, 4, size - 8, size - 8)
        
        # Рисуем символ микрофона
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), 0x0084, "🎤")  # AlignCenter
        
        painter.end()
        
        return QIcon(pixmap)
    
    def _update_icon(self):
        """Обновить иконку в соответствии со статусом"""
        icon = self._create_icon(self._status)
        self.tray.setIcon(icon)
    
    # === Обработчики событий ===
    
    def _on_activated(self, reason):
        """Обработка активации tray-иконки"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Одинарный клик - показать настройки
            self._on_settings()
    
    def _on_settings(self):
        """Обработка нажатия настроек"""
        self.settings_requested.emit()
    
    def _on_quit(self):
        """Обработка выхода"""
        self.quit_requested.emit()
    
    # === Публичные методы ===
    
    def set_status(self, status: TrayStatus, text: Optional[str] = None):
        """
        Установить статус tray-иконки.
        
        Args:
            status: Новый статус
            text: Опциональный текст для tooltip
        """
        self._status = status
        
        tooltips = {
            TrayStatus.READY: "EchoType - Готов к записи",
            TrayStatus.RECORDING: "EchoType - Запись...",
            TrayStatus.PROCESSING: "EchoType - Обработка...",
            TrayStatus.ERROR: "EchoType - Ошибка"
        }
        
        tooltip = text if text else tooltips.get(status, "EchoType")
        self.tray.setToolTip(tooltip)
        self._update_icon()
        
    def show_message(self, title: str, message: str, 
                     icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
                     duration: int = 3000):
        """
        Показать всплывающее сообщение.
        
        Args:
            title: Заголовок
            message: Текст сообщения
            icon: Иконка сообщения
            duration: Длительность показа в мс
        """
        self.tray.showMessage(title, message, icon, duration)
    
    def show(self):
        """Показать tray-иконку"""
        self.tray.show()
    
    def hide(self):
        """Скрыть tray-иконку"""
        self.tray.hide()
    
    @property
    def status(self) -> TrayStatus:
        """Текущий статус"""
        return self._status
