"""
GUI клиент для EchoType
"""

import sys
import numpy as np
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from Client import Client
from Client.AudioRecorder import AudioData
from GUIClient.TrayApp import TrayApp, TrayStatus
from GUIClient.Windows import PopupWindow, SettingsWindow

from config_manager import ConfigManager
from logger import get_logger


logger = get_logger(__name__)


class GUIClient(QObject):
    """
    Главный класс GUI клиента EchoType.
    Объединяет tray-апплет, popup окно и настройки.
    """

    recording_start = pyqtSignal()
    
    def __init__(self, config: ConfigManager):
        super().__init__()
        
        self.config = config

        self.client = Client(config)
        
        # Инициализация компонентов
        self._init_app()
        self._init_audio()
        self.client.init_hotkey_manager()
        self._init_ui()
        
    def _init_app(self):
        """Инициализация QApplication"""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        self.app.setQuitOnLastWindowClosed(False) # type: ignore
        self.app.setApplicationName("EchoType")
        self.app.setApplicationDisplayName("EchoType") # type: ignore
    
    def _init_audio(self):
        """Инициализация аудио рекордера"""
        # Callbacks
        self.client.audio_recorder.on_recording_start(self._on_recording_start)
        self.client.audio_recorder.on_recording_stop(self._on_recording_stop)
        self.client.audio_recorder.on_error(self._on_recording_error)
        self.client.audio_recorder.on_audio_update(self._on_audio_update)
    
    def _init_ui(self):
        """Инициализация UI компонентов"""
        # Tray-апплет
        self.tray = TrayApp()
        self.tray.settings_requested.connect(self._show_settings)
        self.tray.settings_requested.connect(self.client.hotkey_manager.stop)
        self.tray.quit_requested.connect(self._quit)
        
        # Popup окно
        self.popup = PopupWindow(self.config)
        
        # Окно настроек (создаётся по требованию)
        self.settings_window: Optional[SettingsWindow] = None

        self.recording_start.connect(self._process_on_recording_start)

    # === Callbacks ===
    
    def _on_recording_start(self):
        self.recording_start.emit()

    def _process_on_recording_start(self):
        """При начале записи"""
        self.tray.set_status(TrayStatus.RECORDING)

        if self.config.show_popup():
            self.popup.start_recording()
            self.popup.show()
    
    def _on_recording_stop(self, audio_data: AudioData):
        """При остановке записи"""
        self.tray.set_status(TrayStatus.PROCESSING)
        
        if self.config.show_popup():
            self.popup.stop_recording()
        
        self.processing_thread = QThread()

        def thread_func():
            text = self.client.process_recording(audio_data)
            if text:
                self.popup.set_result(text)
            self.tray.set_status(TrayStatus.READY)
            self.processing_thread.quit()
        
        self.processing_thread.run = thread_func
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)
        self.processing_thread.finished.connect(self.popup.fade_out)

        self.processing_thread.start()

    def _on_recording_error(self, error: str):
        """При ошибке записи"""
        self.tray.set_status(TrayStatus.ERROR, f"Ошибка: {error}")
        self.tray.show_message("Ошибка записи", error)
        
        if self.config.show_popup():
            self.popup.set_error(error)
    
    def _on_audio_update(self, indata: np.ndarray, audio_data: AudioData):
        """При обновлении аудио"""
        if self.config.show_popup() and self.config.show_visualizer():
            level = float(np.abs(indata).mean())
            self.popup.add_audio_level(level)
    
    # === Настройки ===
    
    def _show_settings(self):
        """Показать окно настроек"""
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.config)
            self.settings_window.settings_saved.connect(self._on_settings_saved)
            self.settings_window.finished.connect(self.client.hotkey_manager.start)
        
        self.settings_window.show()
        self.settings_window.activateWindow()
    
    def _on_settings_saved(self):
        """При сохранении настроек"""
        logger.info("🔥 SETTINGS SAVED EVENT: перезагрузка горячих клавиш")
        
        # Перезагружаем горячие клавиши
        self.client.hotkey_manager.stop()
        self.client.hotkey_manager.clear()
        self.client.init_hotkey_manager()
        self.client.hotkey_manager.start()
        
        # Обновляем параметры аудио
        self.client.audio_recorder.sample_rate = self.config.get_audio_sample_rate()
        self.client.audio_recorder.channels = self.config.get_audio_channels()
        self.client.audio_recorder.device = self.config.get_audio_device()
        
        self.tray.show_message("Настройки", "Настройки сохранены")
    
    # === Выход ===
    
    def _quit(self):
        """Завершить работу"""
        self.popup.hide()
        self.tray.hide()
        self.client.clean_up()
        self.app.quit() # type: ignore
    
    def run(self):
        """Запустить GUI клиент"""
        self.client.hotkey_manager.start()
        self.tray.show()
        
        if not self.config.start_minimized():
            self.tray.show_message(
                "EchoType запущен",
                "Нажмите горячую клавишу для записи"
            )
        
        return self.app.exec() # type: ignore
