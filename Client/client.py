"""
Консольный клиент для записи голоса по горячим клавишам
"""

import os
import sys
import time
import threading
import queue
import pyperclip
from typing import Optional, Dict, Any

import requests
from pynput import keyboard

from config_manager import ConfigManager
from Client.AudioRecorder import AudioRecorder, AudioData
from Client.hotkey_manager import HotkeyManager, HotkeyMode


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
        
        # Очередь для сообщений
        self.message_queue = queue.Queue()
        
        # Контроллер для ввода текста
        self.controller = keyboard.Controller()
        
        # Флаг работы
        self._running = False
    
    def _init_audio_recorder(self):
        """Инициализация аудио рекордера"""
        self.audio_recorder = AudioRecorder(
            sample_rate=self.config.get_audio_sample_rate(),
            channels=self.config.get_audio_channels(),
            device=self.config.get_audio_device()
        )
        
        # Устанавливаем callbacks
        self.audio_recorder.on_recording_start(self._on_recording_start)
        self.audio_recorder.on_recording_stop(self._on_recording_stop)
        self.audio_recorder.on_error(self._on_recording_error)
    
    def init_hotkey_manager(self):
        """Инициализация менеджера горячих клавиш"""
        self.hotkey_manager = HotkeyManager()
        
        # Регистрируем основную горячую клавишу записи
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
        
        # Регистрируем дополнительные горячие клавиши из конфигурации
        hotkeys = self.config.get_hotkeys()
        for name, settings in hotkeys.items():
            if name != 'record' and isinstance(settings, dict):
                keys = settings.get('keys')
                mode = settings.get('mode', 'toggle')
                description = settings.get('description', '')
                
                if keys:
                    self.hotkey_manager.register(
                        name=name,
                        keys=keys,
                        callback=lambda n=name: self._custom_action(n),
                        mode=HotkeyMode.PUSH_TO_TALK if mode == 'ptt' else HotkeyMode.TOGGLE,
                        description=description
                    )
    
    # === Callbacks для AudioRecorder ===
    
    def _on_recording_start(self):
        """Callback при начале записи"""
        self.message_queue.put("🎤 Запись начата...")
        # Запускаем таймер
        threading.Thread(target=self._recording_timer, daemon=True).start()
    
    def _on_recording_stop(self, audio_data: AudioData):
        """Callback при остановке записи"""
        self.message_queue.put(f"⏹️  Запись остановлена ({audio_data.duration:.1f} сек)")
        # Обрабатываем запись в отдельном потоке
        threading.Thread(target=self._process_recording, args=(audio_data,), daemon=True).start()
    
    def _on_recording_error(self, error: str):
        """Callback при ошибке"""
        self.message_queue.put(f"❌ Ошибка: {error}")
    
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
    
    def _custom_action(self, action_name: str):
        """Выполнить кастомное действие"""
        # Здесь можно добавить обработку дополнительных действий
        self.message_queue.put(f"⚡ Действие: {action_name}")
    
    def _recording_timer(self):
        """Таймер записи для отображения длительности"""
        while self.audio_recorder.is_recording:
            elapsed = self.audio_recorder.duration
            sys.stdout.write(f"\r⏱️  Запись: {elapsed:.1f} сек")
            sys.stdout.flush()
            time.sleep(0.1)
        print()  # Новая строка после остановки
    
    # === Обработка записи ===
    
    def _process_recording(self, audio_data: AudioData):
        """Обработка записанного аудио"""
        try:
            # Сохраняем во временный файл
            tmp_path = audio_data.save_to_temp_wav()
            if not tmp_path:
                self.message_queue.put("❌ Ошибка создания временного файла")
                return
            
            # Отправляем на сервер
            self.message_queue.put("📡 Отправка на сервер...")
            result = self._send_to_server(tmp_path)
            
            # Удаляем временный файл
            os.unlink(tmp_path)
            
            if result:
                self._handle_result(result)
        
        except Exception as e:
            self.message_queue.put(f"❌ Ошибка обработки: {str(e)}")
    
    def _send_to_server(self, audio_path: str) -> Optional[Dict[str, Any]]:
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
                self.message_queue.put(f"❌ Ошибка сервера: {response.status_code}")
                return None
        
        except requests.exceptions.RequestException as e:
            self.message_queue.put(f"❌ Ошибка соединения: {str(e)}")
            return None
    
    def _handle_result(self, result: Dict[str, Any]):
        """Обработка результата транскрипции"""
        text = result.get('text', '').strip()
        language = result.get('language', 'unknown')
        
        if not text:
            self.message_queue.put("⚠️  Текст не распознан")
            return
        
        # Добавляем пробел если нужно
        if self.add_space:
            text = " " + text
        
        # Выводим результат
        print(f"\n📝 Результат ({language}):")
        print(f"┌{'─' * (len(text) + 2)}┐")
        print(f"│ {text} │")
        print(f"└{'─' * (len(text) + 2)}┘")
        
        self.message_queue.put(f"✅ Текст распознан: {text[:50]}..." if len(text) > 50 else f"✅ Текст распознан")
        
        # Действия в зависимости от режима вывода
        if self.output_mode in ["clipboard", "both"]:
            pyperclip.copy(text)
            self.message_queue.put("📋 Текст скопирован в буфер обмена")
        
        if self.output_mode in ["typein", "both"]:
            self.message_queue.put("⌨️ Текст отправлен в ввод")
            self.hotkey_manager.stop()
            self.controller.type(text)
            
            if self.auto_paste:
                self.controller.tap(keyboard.Key.enter)
            self.hotkey_manager.start()
    
    # === Обработка сообщений ===
    
    def _process_messages(self):
        """Обработка сообщений из очереди"""
        while self._running:
            try:
                message = self.message_queue.get(timeout=0.1)
                print(f"\n{message}")
            except queue.Empty:
                pass
    
    # === Основной цикл ===
    
    def run(self):
        """Основной цикл клиента"""
        self._running = True
        
        # Запускаем менеджер горячих клавиш
        self.hotkey_manager.start()
        
        # Запускаем поток для обработки сообщений
        message_thread = threading.Thread(target=self._process_messages, daemon=True)
        message_thread.start()
        
        # Основной цикл
        try:
            print("✅ Клиент запущен. Ожидание нажатия клавиши...")
            
            # Держим основной поток живым
            while self._running:
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            pass
        
        finally:
            self.stop()
    
    def stop(self):
        """Остановить клиент"""
        self._running = False
        
        # Останавливаем запись если идёт
        if self.audio_recorder.is_recording:
            self.audio_recorder.stop_recording()
        
        # Останавливаем менеджер горячих клавиш
        self.hotkey_manager.stop()
        
        print("\n👋 Клиент остановлен")


def main():
    """Точка входа консольного клиента"""
    config = ConfigManager()
    client = Client(config)
    client.run()


if __name__ == "__main__":
    main()
