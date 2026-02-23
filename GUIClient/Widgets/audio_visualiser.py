
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor, QPainter, QPen

from logger import get_logger


logger  = get_logger(__name__)


class AudioVisualizer(QWidget):
    """Виджет визуализации аудио в реальном времени"""
    
    def __init__(self, parent=None, width: int = 200, height: int = 40):
        super().__init__(parent)
        
        self._width = width
        self._height = height
        self._levels: list = []
        self._max_levels = 50  # Количество столбиков
        
        self.setFixedSize(width, height)
        self.setMinimumSize(width, height)
    
    def add_level(self, level: float):
        """Добавить уровень звука для визуализации"""
        # Нормализуем уровень (0.0 - 1.0)
        normalized = min(1.0, level * 10)  # Умножаем для лучшей видимости
        self._levels.append(normalized)
        
        # Ограничиваем количество уровней
        if len(self._levels) > self._max_levels:
            self._levels.pop(0)
        
        self.update()
    
    def clear(self):
        """Очистить визуализацию"""
        self._levels.clear()
        self.update()
    
    def paintEvent(self, event):
        """Отрисовка визуализации"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        if not self._levels:
            # Рисуем линию по центру если нет данных
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            y = self._height // 2
            painter.drawLine(0, y, self._width, y)
            return
        
        # Рисуем столбики
        bar_width = self._width / self._max_levels
        bar_spacing = 2
        
        for i, level in enumerate(self._levels):
            x = int(i * bar_width)
            
            # Высота столбика
            bar_height = int(level * (self._height - 4))
            
            # Цвет в зависимости от уровня
            if level < 0.3:
                color = QColor(76, 175, 80)  # Зелёный
            elif level < 0.7:
                color = QColor(255, 193, 7)  # Жёлтый
            else:
                color = QColor(244, 67, 54)  # Красный
            
            # Рисуем столбик по центру
            y_top = (self._height - bar_height) // 2
            painter.fillRect(
                x + bar_spacing // 2,
                y_top,
                int(bar_width) - bar_spacing,
                bar_height,
                color
            )
