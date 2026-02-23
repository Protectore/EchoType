"""
Клиент EchoType. Предоставляет интерфейс для управления менеджером горячих клавиш, аудио-рекордером и взаимодействия с сервером
"""

import os
import pyperclip
from typing import Optional, Dict, Any
import requests
from pynput import keyboard

from config_manager import ConfigManager
from Client.AudioRecorder import AudioRecorder, AudioData
from Client.HotkeyManager import HotkeyManager, HotkeyMode

from logger import get_logger


logger = get_logger(__name__)


class Client:
    """
    Клиент для записи голоса по нажатию горячей клавиши.
    Использует выделенные модули AudioRecorder и HotkeyManager.
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        
        # Настройки из конфигурации
        self.server_url = config.get_server_url()
        self.output_mode = config.get_output_mode()
        self.auto_paste = config.get_auto_paste()
        self.add_space = config.get_add_space()
        
        # Инициализируем компоненты
        self._init_audio_recorder()
        self.init_hotkey_manager()
        
        # Контроллер для ввода текста
        self.keyboard = keyboard.Controller()
    
    def _init_audio_recorder(self):
        """Инициализация аудио рекордера"""
        self.audio_recorder = AudioRecorder(
            sample_rate=self.config.get_audio_sample_rate(),
            channels=self.config.get_audio_channels(),
            device=self.config.get_audio_device()
        )
        
    def init_hotkey_manager(self):
        """Инициализация менеджера горячих клавиш"""
        self.hotkey_manager = HotkeyManager()
        
        record_keys = self.config.get_hotkey_keys('record')
        record_mode = self.config.get_hotkey_mode('record')

        mode = HotkeyMode.PUSH_TO_TALK if record_mode == 'ptt' else HotkeyMode.TOGGLE
        callback = self.start_recording if mode == HotkeyMode.PUSH_TO_TALK else self.toggle_recording
        on_release = self.stop_recording if mode == HotkeyMode.PUSH_TO_TALK else None
        
        self.hotkey_manager.register(
            name='record',
            keys=record_keys,
            callback=callback,
            mode=mode,
            description=self.config.get('hotkeys.record.description', 'Запись голоса'),
            on_release=on_release
        )

    # === Управление записью ===
    
    def start_recording(self):
        """Начать запись (для PTT)"""
        if not self.audio_recorder.is_recording:
            self.audio_recorder.start_recording()
    
    def stop_recording(self):
        """Остановить запись (для PTT)"""
        if self.audio_recorder.is_recording:
            self.audio_recorder.stop_recording()
    
    def toggle_recording(self):
        """Переключить запись (для Toggle режима)"""
        self.audio_recorder.toggle_recording()
    
    # === Обработка записи ===
    
    def process_recording(self, audio_data: AudioData):
        """Обработка записанного аудио"""
        try:
            tmp_path = audio_data.save_to_temp_wav()
            if not tmp_path:
                return None
            
            logger.info("📡 Отправка на сервер...")
            result = self.send_to_server(tmp_path)
            
            os.unlink(tmp_path)
            
            if result:
                return self.handle_result(result)
        
        except Exception as e:
            logger.error(f"❌ Ошибка обработки: {str(e)}")
            return None
    
    def send_to_server(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """Отправка аудио файла на STT сервер"""
        try:
            with open(audio_path, 'rb') as audio_file:
                files = {'audio': ('recording.wav', audio_file, 'audio/wav')}
                response = requests.post(
                    f"{self.server_url}/transcribe/",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Ошибка сервера: {response.status_code}")
                return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка соединения: {str(e)}")
            return None
    
    def handle_result(self, result: Dict[str, Any]):
        """Обработка результата транскрипции"""
        text = result.get('text', '').strip()
        language = result.get('language', 'unknown')
        
        if not text:
            logger.warning("⚠️ Текст не распознан")
            return
        
        # Добавляем пробел если нужно
        if self.add_space:
            text = " " + text
        
        logger.info(f"✅ Текст распознан: {language=}, '{text[:50]}...'" if len(text) > 50 else f"✅ Текст распознан: {language=}, '{text}'")
        
        # Действия в зависимости от режима вывода
        if self.output_mode in ["clipboard", "both"]:
            pyperclip.copy(text)
            logger.info("📋 Текст скопирован в буфер обмена")
        
        if self.output_mode in ["typein", "both"]:
            logger.info("⌨️ Текст отправлен в ввод")
            self.hotkey_manager.stop()
            self.keyboard.type(text)
            
            if self.auto_paste:
                self.keyboard.tap(keyboard.Key.enter)
            self.hotkey_manager.start()
        
        return text
    
    def clean_up(self):
        """Остановить запись если она идёт и остановить менеджер горячих клавиш"""
        if self.audio_recorder.is_recording:
            self.audio_recorder.stop_recording()
        
        self.hotkey_manager.stop()
