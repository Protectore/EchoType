"""
GUI клиент для EchoType
Точка входа графического интерфейса
"""

import sys
import os
import threading
import numpy as np
import pyperclip
from typing import Optional, Dict, Any

import requests
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from Client.client import Client
from config_manager import ConfigManager
from Client.AudioRecorder import AudioData
from GUIClient.tray_app import TrayApp, TrayStatus
from GUIClient.popup_window import PopupWindow
from GUIClient.settings_window import SettingsWindow
from logger import get_logger


logger = get_logger(__name__)


class GUIClient(QObject):
    """
    Главный класс GUI клиента EchoType.
    Объединяет tray-апплет, popup окно и настройки.
    """
    
    # Сигналы для коммуникации между компонентами
    transcription_ready = pyqtSignal(str, str)  # text, language
    transcription_error = pyqtSignal(str)
    
    def __init__(self, config: ConfigManager):
        super().__init__()
        
        self.config = config

        self.client = Client(config)
        
        # Инициализация компонентов
        self._init_app()
        self._init_audio()
        self.client.init_hotkey_manager()
        self._init_ui()
        
        # Состояние
        self._current_text = ""
    
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
        self.tray = TrayApp(self.config)
        self.tray.settings_requested.connect(self._show_settings)
        self.tray.settings_requested.connect(self.client.hotkey_manager.stop)
        self.tray.quit_requested.connect(self._quit)
        
        # Popup окно
        self.popup = PopupWindow(self.config)
        self.popup.copy_requested.connect(self._copy_text)
        
        # Окно настроек (создаётся по требованию)
        self.settings_window: Optional[SettingsWindow] = None
    
    # === Callbacks ===
    
    def _on_recording_start(self):
        """При начале записи"""
        self.tray.set_status(TrayStatus.RECORDING)

        if self.config.show_popup():
            self.popup.start_recording()
    
    def _on_recording_stop(self, audio_data: AudioData):
        """При остановке записи"""
        self.tray.set_status(TrayStatus.PROCESSING)
        
        if self.config.show_popup():
            self.popup.stop_recording()
        
        # Обрабатываем в отдельном потоке
        threading.Thread(
            target=self._process_audio,
            args=(audio_data,),
            daemon=True
        ).start()
    
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
    
    # === Обработка аудио ===
    
    def _process_audio(self, audio_data: AudioData):
        """Обработка записанного аудио"""
        try:
            # Сохраняем во временный файл
            tmp_path = audio_data.save_to_temp_wav()
            if not tmp_path:
                self.transcription_error.emit("Ошибка создания временного файла")
                return
            
            # Отправляем на сервер
            result = self._send_to_server(tmp_path)
            
            # Удаляем временный файл
            os.unlink(tmp_path)
            
            if result:
                text = result.get('text', '').strip()
                language = result.get('language', 'unknown')
                self.transcription_ready.emit(text, language)
            else:
                self.transcription_error.emit("Ошибка распознавания")
        
        except Exception as e:
            self.transcription_error.emit(str(e))
    
    def _send_to_server(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """Отправка аудио на сервер"""
        try:
            with open(audio_path, 'rb') as audio_file:
                files = {'audio': ('recording.wav', audio_file, 'audio/wav')}
                response = requests.post(
                    f"{self.config.get_server_url()}/transcribe/",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                return response.json()
            return None
        
        except requests.exceptions.RequestException:
            return None
    
    # === Обработка результатов ===
    
    def _handle_transcription(self, text: str, language: str):
        """Обработка результата транскрипции"""
        if not text:
            self.tray.set_status(TrayStatus.READY)
            if self.config.show_popup():
                self.popup.set_result("", language)
            return
        
        self._current_text = text
        
        # Обновляем UI
        self.tray.set_status(TrayStatus.READY)
        self.tray.show_message("Распознано", text[:50] + "..." if len(text) > 50 else text)
        
        if self.config.show_popup():
            self.popup.set_result(text, language)
        
        # Выводим текст
        self._output_text(text)
    
    def _handle_error(self, error: str):
        """Обработка ошибки"""
        self.tray.set_status(TrayStatus.ERROR)
        self.tray.show_message("Ошибка", error)
        
        if self.config.show_popup():
            self.popup.set_error(error)
    
    def _output_text(self, text: str):
        """Вывод текста согласно настройкам"""
        output_mode = self.config.get_output_mode()
        
        # Добавляем пробел если нужно
        if self.config.get_add_space():
            text = " " + text
        
        if output_mode in ["clipboard", "both"]:
            pyperclip.copy(text)
        
        if output_mode in ["typein", "both"]:
            from pynput import keyboard
            controller = keyboard.Controller()
            controller.type(text)
            
            if self.config.get_auto_paste():
                controller.tap(keyboard.Key.enter)
    
    def _copy_text(self, text: str):
        """Копировать текст в буфер обмена"""
        pyperclip.copy(text)
        self.tray.show_message("Скопировано", "Текст скопирован в буфер обмена")
    
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
        self.client.stop()
        
        # Скрываем UI
        self.popup.hide()
        self.tray.hide()
        
        # Завершаем приложение
        self.app.quit() # type: ignore
    
    def run(self):
        """Запустить GUI клиент"""
        # Подключаем сигналы
        self.transcription_ready.connect(self._handle_transcription)
        self.transcription_error.connect(self._handle_error)
        
        # Запускаем горячие клавиши
        self.client.hotkey_manager.start()
        
        # Показываем tray
        self.tray.show()
        
        # Сообщение о запуске
        if not self.config.start_minimized():
            self.tray.show_message(
                "EchoType запущен",
                "Нажмите горячую клавишу для записи"
            )
        
        return self.app.exec() # type: ignore


def main():
    """Точка входа GUI клиента"""
    config = ConfigManager()
    client = GUIClient(config)
    sys.exit(client.run())


if __name__ == "__main__":
    main()
