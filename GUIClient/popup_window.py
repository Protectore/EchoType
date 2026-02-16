"""
Всплывающее окно при записи для EchoType
Минималистичное окно с визуализацией аудио и превью текста
"""

import time
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QPainter, QPen

import numpy as np

from config_manager import ConfigManager


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


class PopupWindow(QWidget):
    """
    Всплывающее окно при записи.
    Показывает визуализацию аудио, таймер и превью распознанного текста.
    """
    
    # Сигналы
    copy_requested = pyqtSignal(str)
    repeat_requested = pyqtSignal()
    closed = pyqtSignal()
    
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        
        self.config = config
        
        self._init_ui()
        self._init_position()
        
        # Флаги окна - всегда поверх других, без рамки
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Прозрачный фон
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setFixedSize(280, 180)
        
        # Главный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Заголовок
        header_layout = QHBoxLayout()
        
        self.status_label = QLabel("🎤 Запись...")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #FFFFFF;")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        self.timer_label = TimerLabel()
        header_layout.addWidget(self.timer_label)
        
        layout.addLayout(header_layout)
        
        # Визуализатор аудио
        self.visualizer = AudioVisualizer(width=256, height=50)
        layout.addWidget(self.visualizer)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #444;")
        line.setFixedHeight(1)
        layout.addWidget(line)
        
        # Превью текста
        self.text_preview = QLabel("Текст появится здесь...")
        self.text_preview.setFont(QFont("Segoe UI", 10))
        self.text_preview.setStyleSheet("color: #AAA;")
        self.text_preview.setWordWrap(True)
        self.text_preview.setMaximumHeight(40)
        layout.addWidget(self.text_preview)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.copy_btn = QPushButton("📋 Копировать")
        self.copy_btn.setFixedHeight(28)
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._on_copy)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        buttons_layout.addWidget(self.copy_btn)
        
        self.repeat_btn = QPushButton("🔄 Повторить")
        self.repeat_btn.setFixedHeight(28)
        self.repeat_btn.clicked.connect(self._on_repeat)
        self.repeat_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        buttons_layout.addWidget(self.repeat_btn)
        
        layout.addLayout(buttons_layout)
        
        # Стиль окна
        self.setStyleSheet("""
            QWidget {
                background-color: #2D2D2D;
                border-radius: 8px;
            }
        """)
    
    def _init_position(self):
        """Инициализация позиции окна"""
        position = self.config.get_popup_position()
        
        if position == "center":
            self._center_on_screen()
        elif position == "cursor":
            self._position_at_cursor()
        else:  # corner
            self._position_at_corner()
    
    def _center_on_screen(self):
        """Расположить окно по центру экрана"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            x = (geometry.width() - self.width()) // 2
            y = (geometry.height() - self.height()) // 2
            self.move(x, y)
    
    def _position_at_cursor(self):
        """Расположить окно рядом с курсором"""
        from PyQt6.QtGui import QCursor
        cursor_pos = QCursor.pos()
        
        # Смещение чтобы не перекрывать курсор
        x = cursor_pos.x() + 20
        y = cursor_pos.y() + 20
        
        # Проверяем границы экрана
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            if x + self.width() > geometry.right():
                x = cursor_pos.x() - self.width() - 20
            if y + self.height() > geometry.bottom():
                y = cursor_pos.y() - self.height() - 20
        
        self.move(x, y)
    
    def _position_at_corner(self):
        """Расположить окно в углу экрана"""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            x = geometry.right() - self.width() - 20
            y = geometry.bottom() - self.height() - 20
            self.move(x, y)
    
    # === Публичные методы ===
    
    def start_recording(self):
        """Начать отображение записи"""
        self.status_label.setText("🎤 Запись...")
        self.status_label.setStyleSheet("color: #FF5252;")
        self.timer_label.reset()
        self.timer_label.start()
        self.visualizer.clear()
        self.text_preview.setText("Текст появится здесь...")
        self.text_preview.setStyleSheet("color: #AAA;")
        self.copy_btn.setEnabled(False)
        
        self._init_position()
        self.show()
    
    def stop_recording(self):
        """Остановить отображение записи"""
        self.timer_label.stop()
        self.status_label.setText("⏳ Обработка...")
        self.status_label.setStyleSheet("color: #FFC107;")
    
    def add_audio_level(self, level: float):
        """Добавить уровень аудио для визуализации"""
        self.visualizer.add_level(level)
    
    def set_result(self, text: str, language: str = ""):
        """Установить результат распознавания"""
        self.status_label.setText("✅ Готово")
        self.status_label.setStyleSheet("color: #4CAF50;")
        
        if text:
            # Показываем превью текста
            preview = text[:100] + "..." if len(text) > 100 else text
            self.text_preview.setText(preview)
            self.text_preview.setStyleSheet("color: #FFF;")
            self.copy_btn.setEnabled(True)
            self._current_text = text
        else:
            self.text_preview.setText("❌ Текст не распознан")
            self.text_preview.setStyleSheet("color: #FF5252;")
    
    def set_error(self, error: str):
        """Установить ошибку"""
        self.status_label.setText("❌ Ошибка")
        self.status_label.setStyleSheet("color: #FF5252;")
        self.text_preview.setText(error[:100])
        self.text_preview.setStyleSheet("color: #FF5252;")
    
    # === Обработчики ===
    
    def _on_copy(self):
        """Обработка нажатия копирования"""
        if hasattr(self, '_current_text'):
            self.copy_requested.emit(self._current_text)
    
    def _on_repeat(self):
        """Обработка нажатия повторить"""
        self.repeat_requested.emit()
    
    def mousePressEvent(self, event):
        """Закрытие по клику вне окна"""
        if event.button() == Qt.MouseButton.RightButton:
            self.hide()
            self.closed.emit()
    
    def keyPressEvent(self, event):
        """Закрытие по Escape"""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.closed.emit()
