"""
Всплывающее окно при записи для EchoType
Минималистичное окно с визуализацией аудио и превью текста
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer

from GUIClient.Widgets import TimerLabel, AudioVisualizer
from GUIClient.utility import GuiUtility
from Utility import ConfigManager, get_logger


logger  = get_logger(__name__)


class PopupWindow(QWidget):
    """
    Всплывающее окно при записи.
    Показывает визуализацию аудио, таймер и превью распознанного текста.
    """
    
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._init_ui()
        self._init_animations()
        self.setStyleSheet(GuiUtility.read_style_file("popup_window"))
        self._init_position()
        
        # Флаги окна - всегда поверх других, без рамки
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Прозрачный фон
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.fade_out_delay_timer = QTimer(self)
        self.fade_out_delay_timer.setSingleShot(True)
        self.fade_out_delay_timer.timeout.connect(lambda: self._start_fade_out_animation(300))
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setFixedSize(280, 180)
        self.setObjectName("PopupWindow")
        
        # Главный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Заголовок
        header_layout = QHBoxLayout()
        
        self.status_label = QLabel("🎤 Запись...")
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
        line.setObjectName("line_separator")
        line.setFixedHeight(1)
        layout.addWidget(line)
        
        # Превью текста
        self.text_preview = QLabel("Текст появится здесь...")
        self.text_preview.setObjectName("text_preview")
        self.text_preview.setWordWrap(True)
        layout.addWidget(self.text_preview)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        layout.addLayout(buttons_layout)
    
    def _init_animations(self, fade_in_duration_ms: int = 300, fade_out_duration_ms: int = 300):
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(fade_in_duration_ms)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        self.fade_out_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_out_animation.setDuration(fade_out_duration_ms)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_out_animation.finished.connect(self._hide_after_animation)

    def _init_position(self):
        """Инициализация позиции окна"""
        self._center_on_screen()
        logger.debug(f"Popup position is set to {self.x()}, {self.y()}")
    
    def _center_on_screen(self):
        """Расположить окно по центру экрана"""
        logger.debug("Setting popup position to center")
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.geometry()
            x = (geometry.width() - self.width()) // 2
            y = (geometry.height() - self.height()) * 98 // 100
            self.move(x, y)
    
    # === Анимации ===
    
    def fade_in(self, duration_ms: int = 300):
        """Плавное появление окна"""
        self.setWindowOpacity(0.0)
        self.show()
        self.fade_in_animation.start()
    
    def fade_out(self, delay_ms: int = 2000):
        """Плавное сокрытие окна"""
        self.fade_out_delay_timer.start(delay_ms)
    
    def _start_fade_out_animation(self, duration_ms: int):
        """Запуск анимации сокрытия после задержки"""
        self.fade_out_animation.start()
    
    def _hide_after_animation(self):
        """Скрыть окно после завершения анимации"""
        self.hide()
        self.closed.emit()
    
    # === Публичные методы ===
    
    def start_recording(self):
        """Начать отображение записи"""
        logger.debug("Setting popup info")
        self.status_label.setText("🎤 Запись...")
        self.status_label.setProperty("class", "recording")
        self.timer_label.reset()
        self.timer_label.start()
        self.visualizer.clear()
        self.text_preview.setText("Текст появится здесь...")
        self.text_preview.setProperty("class", "")
        
        logger.debug("Showing popup window")
        self._init_position()
        self.fade_out_delay_timer.stop()
        self.fade_out_animation.stop()
        if not self.isVisible():
            self.fade_in()
        logger.debug("Popup window is shown")
    
    def stop_recording(self):
        """Остановить отображение записи"""
        self.timer_label.stop()
        self.status_label.setText("⏳ Обработка...")
        self.status_label.setProperty("class", "processing")
    
    def add_audio_level(self, level: float):
        """Добавить уровень аудио для визуализации"""
        self.visualizer.add_level(level)
    
    def set_result(self, text: str, language: str = ""):
        """Установить результат распознавания"""
        self.status_label.setText("✅ Готово")
        self.status_label.setProperty("class", "ready")
        
        if text:
            # Показываем превью текста
            preview = text[:100] + "..." if len(text) > 100 else text
            self.text_preview.setText(preview)
            self.text_preview.setProperty("class", "ready")
            self._current_text = text
        else:
            self.text_preview.setText("❌ Текст не распознан")
            self.text_preview.setProperty("class", "error")
    
    def set_error(self, error: str):
        """Установить ошибку"""
        self.status_label.setText("❌ Ошибка")
        self.status_label.setProperty("class", "error")
        self.text_preview.setText(error[:100])
        self.text_preview.setProperty("class", "error")
    
    # === Обработчики ===

    def mousePressEvent(self, event):
        """Закрытие по клику вне окна"""
        if event.button() == Qt.MouseButton.RightButton:
            self.fade_out()
    
    def keyPressEvent(self, event):
        """Закрытие по Escape"""
        if event.key() == Qt.Key.Key_Escape:
            self.fade_out()
