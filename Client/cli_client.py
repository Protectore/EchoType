"""
Консольный клиент для записи голоса по горячим клавишам
"""

import sys
import time
import threading
import queue

from config_manager import ConfigManager
from Client.AudioRecorder import AudioData
from Client.HotkeyManager import HotkeyManager, HotkeyMode
from Client.client import Client


class CliClient(Client):
    """
    Клиент для записи голоса по нажатию горячей клавиши.
    Использует выделенные модули AudioRecorder и HotkeyManager.
    """
    
    def __init__(self, config: ConfigManager):
        super().__init__(config)

        self.message_queue = queue.Queue()
        self._running = False

        self._init_audio_recorder()
    
        self.audio_recorder.on_recording_start(self._on_recording_start)
        self.audio_recorder.on_recording_stop(self._on_recording_stop)
        self.audio_recorder.on_error(self._on_recording_error)
    
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

    # === Callbacks для AudioRecorder ===
    
    def _on_recording_start(self):
        """Callback при начале записи"""
        self.message_queue.put("🎤 Запись начата...")
        threading.Thread(target=self._recording_timer, daemon=True).start()
    
    def _on_recording_stop(self, audio_data: AudioData):
        """Callback при остановке записи"""
        self.message_queue.put(f"⏹️  Запись остановлена ({audio_data.duration:.1f} сек)")
        threading.Thread(target=self.process_recording, args=(audio_data,), daemon=True).start()
    
    def _on_recording_error(self, error: str):
        """Callback при ошибке"""
        self.message_queue.put(f"❌ Ошибка: {error}")
    
    def _recording_timer(self):
        """Таймер записи для отображения длительности"""
        while self.audio_recorder.is_recording:
            elapsed = self.audio_recorder.duration
            sys.stdout.write(f"\r⏱️  Запись: {elapsed:.1f} сек")
            sys.stdout.flush()
            time.sleep(0.1)
        print()

    # === Основной цикл ===
    
    def _process_messages(self):
        """Обработка сообщений из очереди"""
        while self._running:
            try:
                message = self.message_queue.get(timeout=0.1)
                print(f"\n{message}")
            except queue.Empty:
                pass

    def run(self):
        """Основной цикл клиента"""
        self._running = True
        
        self.hotkey_manager.start()
        
        message_thread = threading.Thread(target=self._process_messages, daemon=True)
        message_thread.start()
        
        try:
            print("✅ Клиент запущен. Ожидание нажатия клавиши...")
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Остановить клиент"""
        self._running = False
        
        if self.audio_recorder.is_recording:
            self.audio_recorder.stop_recording()
        
        self.hotkey_manager.stop()
        
        print("\n👋 Клиент остановлен")


def main():
    """Точка входа консольного клиента"""
    config = ConfigManager()
    client = CliClient(config)
    client.run()


if __name__ == "__main__":
    main()
