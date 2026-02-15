import os
import sys
import time
import threading
import queue
import pyperclip
import tempfile
import sounddevice as sd
import soundfile as sf
import numpy as np
import requests

from typing import Optional, Dict, Any
from pynput import keyboard

from config_manager import ConfigManager

class VoiceRecorderClient:
    """
    Клиент для записи голоса по нажатию горячей клавиши
    """
    
    def __init__(self, config: ConfigManager):
        # Загружаем конфигурацию

        self.config = config

        # Настройки из конфигурации
        self.server_url = config.get_server_url()
        self.hotkey = keyboard.Key.alt_gr
        self.sample_rate = config.get("audio.sample_rate", 16000)
        self.channels = 1
        self.dtype = "float32"
        
        # Состояние записи
        self.is_recording = False
        self.audio_data = []
        self.stream = None

        self.controller = keyboard.Controller()
        
        # Очередь для сообщений
        self.message_queue = queue.Queue()
        
        # Настройки вывода результата
        self.output_mode = config.get("client.output_mode", "typein")  # clipboard, typein, both
        
        print(f"🎤 Голосовой клиент инициализирован")
        print(f"🔗 Сервер: {self.server_url}")
        print(f"🎯 Горячая клавиша: {self.hotkey}")
        print(f"📤 Режим вывода: {self.output_mode}")
        print(f"\nНажмите '{self.hotkey}' для начала/окончания записи")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback функция для записи аудио"""
        if self.is_recording:
            self.audio_data.append(indata.copy())
    
    def start_recording(self):
        """Начать запись аудио"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.audio_data = []
        
        # Создаем аудио поток
        self.stream = sd.InputStream(
            callback=self._audio_callback,
            channels=self.channels,
            samplerate=self.sample_rate,
            dtype=self.dtype
        )
        
        self.stream.start()
        
        # Запускаем таймер для отображения времени записи
        self.recording_start_time = time.time()
        self._start_recording_timer()
        
        self.message_queue.put("🎤 Запись начата...")
    
    def _start_recording_timer(self):
        """Запускает таймер для отображения времени записи"""
        def timer_thread():
            while self.is_recording:
                elapsed = time.time() - self.recording_start_time
                sys.stdout.write(f"\r⏱️  Запись: {elapsed:.1f} сек")
                sys.stdout.flush()
                time.sleep(0.1)
            print()  # Новая строка после остановки
        
        threading.Thread(target=timer_thread, daemon=True).start()
    
    def stop_recording(self):
        """Остановить запись аудио"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        recording_time = time.time() - self.recording_start_time
        self.message_queue.put(f"⏹️  Запись остановлена ({recording_time:.1f} сек)")
        
        # Обрабатываем запись в отдельном потоке
        if len(self.audio_data) > 0:
            threading.Thread(target=self._process_recording, daemon=True).start()
        else:
            self.message_queue.put("⚠️  Запись пуста")
    
    def _process_recording(self):
        """Обработка записанного аудио"""
        try:
            # Объединяем все куски аудио
            audio_array = np.concatenate(self.audio_data, axis=0)
            
            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                sf.write(tmp_path, audio_array, self.sample_rate)
            
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
        
        # Выводим результат
        print(f"\n📝 Результат ({language}):")
        print(f"┌{'─' * (len(text) + 2)}┐")
        print(f"│ {text} │")
        print(f"└{'─' * (len(text) + 2)}┘")
        
        self.message_queue.put(f"✅ Текст распознан: {text[:50]}..." if len(text) > 50 else f"✅ Текст распознан")

        # Действия в зависимости от режима вывода
        if self.output_mode in ["clipboard", "both"]:    
            pyperclip.copy(text)
            self.message_queue.put("✅ Текст скопирован в буфер обмена")
        
        if self.output_mode in ["typein", "both"]:
            self.message_queue.put("✅ Текст отправлен в ввод")
            self.controller.type(text)
    
    def _process_messages(self):
        """Обработка сообщений из очереди"""
        while True:
            try:
                message = self.message_queue.get(timeout=0.1)
                print(f"\n{message}")
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break
    
    def _on_press(self, key):
        if key == self.hotkey:
            self.toggle_recording()

    def toggle_recording(self):
        """Переключение режима записи"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def run(self):
        """Основной цикл клиента"""
        # Регистрируем горячую клавишу
        listener = keyboard.Listener(on_press=self._on_press) # type: ignore
        listener.start()

        # Запускаем поток для обработки сообщений
        message_thread = threading.Thread(target=self._process_messages, daemon=True)
        message_thread.start()
        
        # Основной цикл
        try:
            print("✅ Клиент запущен. Ожидание нажатия клавиши...")
            listener.join()
        
        except KeyboardInterrupt:
            pass
        
        finally:
            if self.is_recording:
                self.stop_recording()
            
            print("\n👋 Клиент остановлен")
