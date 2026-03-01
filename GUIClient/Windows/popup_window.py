"""
Всплывающее окно при записи для EchoType
Минималистичное окно с визуализацией аудио и превью текста
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QApplication, QScrollArea
)
from PyQt6.QtCore import QAbstractAnimation, Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, QRect

from GUIClient.Widgets import TimerLabel, AudioVisualizer
from GUIClient.utility import GuiUtility
from Utility import get_logger


logger  = get_logger(__name__)


class PopupWindow(QWidget):
    """
    Всплывающее окно при записи.
    Показывает визуализацию аудио, таймер и превью распознанного текста.
    """
    
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
        self.setMinimumSize(300, 150)
        self.setMaximumSize(300, 400)
        self.setObjectName("PopupWindow")
        
        # Главный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Заголовок
        self.header_layout = QHBoxLayout()
        
        self.status_label = QLabel("🎤 Запись...")
        self.header_layout.addWidget(self.status_label)
        
        self.header_layout.addStretch()
        
        self.timer_label = TimerLabel()
        self.header_layout.addWidget(self.timer_label)
        
        layout.addLayout(self.header_layout)
        
        # Визуализатор аудио
        self.visualizer = AudioVisualizer(width=self.width() - layout.contentsMargins().left() * 2, height=50)
        layout.addWidget(self.visualizer)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("line_separator")
        line.setFixedHeight(1)
        layout.addWidget(line)
        
        # Превью текста в ScrollArea
        self.text_scroll = QScrollArea()
        self.text_scroll.setObjectName("text_scroll")
        self.text_scroll.setWidgetResizable(True)
        self.text_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_scroll.setFrameShape(QFrame.Shape.NoFrame)  # Без рамки
        
        # Внутренний QLabel для текста
        self.text_preview = QLabel("Текст появится здесь...")
        self.text_preview.setObjectName("text_preview")
        self.text_preview.setWordWrap(True)
        self.text_preview.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Устанавливаем QLabel в ScrollArea
        self.text_scroll.setWidget(self.text_preview)
        layout.addWidget(self.text_scroll)
    
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

        self.size_animation = QPropertyAnimation(self, b"geometry")
        self.size_animation.setDuration(200)
        self.size_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def _init_position(self):
        """Инициализация позиции окна"""
        self._center_on_screen()
        logger.debug(f"Popup position is set to {self.x()}, {self.y()}")
    
    def _center_on_screen(self):
        """Расположить окно снизу по центру экрана"""
        logger.debug("Setting popup position to center")
        screen = self.screen()
        if screen:
            geometry = screen.geometry()
            x = (geometry.width() - self.width()) // 2
            y = geometry.height() - self.height() - 20
            self.move(x, y)
    
    def _calculate_text_height(self, text: str) -> int:
        """Рассчитать необходимую высоту для отображения текста"""
        font_metrics = self.text_preview.fontMetrics()
        available_width = self.width() - self.layout().contentsMargins().left() * 2 - 10  # type: ignore

        text_rect = font_metrics.boundingRect(
            0, 0, available_width, 0,
            Qt.TextFlag.TextWordWrap,
            text
        )

        return text_rect.height() + self.layout().contentsMargins().bottom() # type: ignore
    
    def _calculate_window_height(self, text_height: int) -> int:
        """Рассчитать высоту окна на основе высоты текста"""
        base_height = self.geometry().height() - self.text_scroll.geometry().height()
        max_text_height = self.maximumHeight() - base_height
        actual_text_height = min(text_height, max_text_height)
        window_height = base_height + actual_text_height

        result = max(self.minimumHeight(), min(self.maximumHeight(), window_height))

        return result
    
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
    
    def _animate_resize(self):
        """Плавное изменение размера окна"""
        text_height = self._calculate_text_height(self.text_preview.text())
        target_height = self._calculate_window_height(text_height)

        current_geometry = self.geometry()
        screen_geometry = self.screen().geometry() # type: ignore

        target_geometry = QRect(
            current_geometry.x(),
            screen_geometry.height() - target_height - 20,
            current_geometry.width(),
            target_height
        )
        
        self.size_animation.setStartValue(current_geometry)
        self.size_animation.setEndValue(target_geometry)
        logger.info(f"Changing geometry from {current_geometry} to {target_geometry}")
        self.size_animation.start()
    
    def _hide_after_animation(self):
        """Скрыть окно после завершения анимации"""
        self.hide()
    
    # === Публичные методы ===
    
    def start_recording(self):
        """Начать отображение записи"""
        logger.debug("Setting popup info")
        self.status_label.setText("🎤 Запись...")
        self.status_label.setProperty("class", "recording")
        self.timer_label.reset()
        self.timer_label.start()
        self.visualizer.clear()
        self.set_preview_text("Текст появится здесь...")
        self.text_preview.setProperty("class", "")

        logger.debug("Showing popup window")
        self._init_position()
        self.fade_out_delay_timer.stop()
        if self.fade_out_animation.state() == QAbstractAnimation.State.Running:
            self.fade_out_animation.stop()
            self.setWindowOpacity(1.0)
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
    
    def set_preview_text(self, text: str):
        """Set text and animate resize"""
        if text:
            self.text_preview.setText(text)
            self._animate_resize()

    def set_result(self, text: str, language: str = ""):
        """Установить результат распознавания"""
        self.status_label.setText("✅ Готово")
        self.status_label.setProperty("class", "ready")
        
        if text:
            self.set_preview_text(text)
            self.text_preview.setProperty("class", "ready")
        else:
            self.set_preview_text("❌ Текст не распознан")
            self.text_preview.setProperty("class", "error")
    
    def set_error(self, error: str):
        """Установить ошибку"""
        self.status_label.setText("❌ Ошибка")
        self.status_label.setProperty("class", "error")
        self.set_preview_text(error[:100])
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
