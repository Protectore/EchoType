import time
from typing import Optional

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from logger import get_logger


logger  = get_logger(__name__)


class TimerLabel(QLabel):
    """Виджет таймера записи"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._start_time: Optional[float] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_timer)
        
        self.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        self.setStyleSheet("color: #FF5252;")
        self.setText("00:00")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def start(self):
        """Запустить таймер"""
        self._start_time = time.time()
        self._timer.start(100)  # Обновление каждые 100мс
    
    def stop(self):
        """Остановить таймер"""
        self._timer.stop()
    
    def reset(self):
        """Сбросить таймер"""
        self.stop()
        self._start_time = None
        self.setText("00:00")
    
    def _update_timer(self):
        """Обновить отображение таймера"""
        if self._start_time is None:
            return
        
        elapsed = time.time() - self._start_time
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)
        self.setText(f"{minutes:02d}:{seconds:02d}")
