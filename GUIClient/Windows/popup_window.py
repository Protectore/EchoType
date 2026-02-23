"""
Всплывающее окно при записи для EchoType
Минималистичное окно с визуализацией аудио и превью текста
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from GUIClient.Widgets import TimerLabel, AudioVisualizer
from config_manager import ConfigManager

from logger import get_logger


logger  = get_logger(__name__)


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

        # Попытка пофиксить баг: окно отказывается появляться при вызове show
        # self.show()
        # self.hide()
    
    def _init_position(self):
        """Инициализация позиции окна"""
        position = self.config.get_popup_position()
        
        if position == "center":
            self._center_on_screen()
        elif position == "cursor":
            self._position_at_cursor()
        else:  # corner
            self._position_at_corner()
        logger.debug(f"Popup position is set to {self.x()}, {self.y()}")
    
    def _center_on_screen(self):
        """Расположить окно по центру экрана"""
        logger.debug("Setting popup position to center")
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
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            x = geometry.right() - self.width() - 20
            y = geometry.bottom() - self.height() - 20
            self.move(x, y)
    
    # === Публичные методы ===

    def my_show(self):
        logger.debug("Showing popup window")
        self._init_position()
        self.show()
    
    def start_recording(self):
        """Начать отображение записи"""
        logger.debug("Setting popup info")
        self.status_label.setText("🎤 Запись...")
        self.status_label.setStyleSheet("color: #FF5252;")
        self.timer_label.reset()
        self.timer_label.start()
        self.visualizer.clear()
        self.text_preview.setText("Текст появится здесь...")
        self.text_preview.setStyleSheet("color: #AAA;")
        self.copy_btn.setEnabled(False)
        
        logger.debug("Showing popup window")
        self._init_position()
        self.show()
        logger.debug("Popup window is shown")
    
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
