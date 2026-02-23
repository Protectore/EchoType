"""
Модуль записи аудио для голосового клиента
"""

import time
from typing import Optional, Callable, List
import numpy as np
import sounddevice as sd

from Client.AudioRecorder import AudioData
from Client.AudioRecorder import RecordingState
from logger import get_logger


logger = get_logger(__name__)


class AudioRecorder:
    """
    Класс для записи аудио с микрофона.
    Поддерживает callback-уведомления о событиях записи.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "float32",
        device: Optional[int] = None
    ):
        """
        Инициализация рекордера.
        
        Args:
            sample_rate: Частота дискретизации (по умолчанию 16000 Гц для Whisper)
            channels: Количество каналов (1 = моно)
            dtype: Тип данных аудио
            device: ID устройства записи (None = устройство по умолчанию)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.device = device
        
        # Состояние
        self._state = RecordingState.IDLE
        self._audio_chunks: List[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._recording_start_time: Optional[float] = None
        
        # Callbacks
        self._on_recording_start: Optional[Callable[[], None]] = None
        self._on_recording_stop: Optional[Callable[[AudioData], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_audio_update: Optional[Callable[[np.ndarray, AudioData], None]] = None
    
    # === Свойства ===
    
    @property
    def state(self) -> RecordingState:
        """Текущее состояние записи"""
        return self._state
    
    @property
    def is_recording(self) -> bool:
        """Идёт ли запись в данный момент"""
        return self._state == RecordingState.RECORDING
    
    @property
    def duration(self) -> float:
        """Длительность текущей записи в секундах"""
        if self._recording_start_time is None:
            return 0.0
        return time.time() - self._recording_start_time
    
    @property
    def audio_data(self) -> AudioData:
        """Накопленные аудио-данные"""
        audio_array = np.concatenate(self._audio_chunks, axis=0)
        audio_data = AudioData(
            samples=audio_array,
            sample_rate=self.sample_rate,
            channels=self.channels,
            duration=self.duration
        )
        return audio_data
    
    # === Настройка callback-ов ===
    
    def on_recording_start(self, callback: Callable[[], None]):
        """Установить callback на начало записи"""
        self._on_recording_start = callback
    
    def on_recording_stop(self, callback: Callable[[AudioData], None]):
        """Установить callback на остановку записи"""
        self._on_recording_stop = callback
    
    def on_error(self, callback: Callable[[str], None]):
        """Установить callback на ошибку"""
        self._on_error = callback
    
    def on_audio_update(self, callback: Callable[[np.ndarray, AudioData], None]):
        """Установить callback для обновления уровня звука"""
        self._on_audio_update = callback
    
    # === Управление записью ===
    
    def start_recording(self) -> bool:
        """
        Начать запись аудио.
        
        Returns:
            True если запись успешно начата
        """
        if self._state != RecordingState.IDLE:
            return False
        
        try:
            logger.debug("🎤 Starting recording")
            self._audio_chunks = []
            self._state = RecordingState.RECORDING
            
            # Создаём аудио поток
            self._stream = sd.InputStream(
                callback=self._audio_callback,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
                device=self.device
            )
            
            self._stream.start()
            self._recording_start_time = time.time()
            
            # Уведомляем о начале записи
            if self._on_recording_start:
                self._on_recording_start()
            
            return True
            
        except Exception as e:
            self._state = RecordingState.IDLE
            error_msg = f"Ошибка начала записи: {e}"
            logger.error(f"❌ {error_msg}")
            if self._on_error:
                self._on_error(error_msg)
            return False
    
    def stop_recording(self) -> Optional[AudioData]:
        """
        Остановить запись и вернуть записанные данные.
        
        Returns:
            AudioData с записью или None если запись пуста
        """
        if self._state != RecordingState.RECORDING:
            return None
        
        logger.debug("🎤 Stopping recording")
        self._state = RecordingState.PROCESSING
        
        # Останавливаем поток
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        duration = self.duration
        self._recording_start_time = None
        
        # Объединяем чанки
        if not self._audio_chunks:
            self._state = RecordingState.IDLE
            return None
        
        try:
            audio_data = self.audio_data
            
            self._state = RecordingState.IDLE
            self._audio_chunks = []
            
            # Уведомляем об остановке
            if self._on_recording_stop:
                self._on_recording_stop(audio_data)
            
            return audio_data
            
        except Exception as e:
            self._state = RecordingState.IDLE
            error_msg = f"Ошибка обработки записи: {e}"
            logger.error(f"❌ {error_msg}")
            if self._on_error:
                self._on_error(error_msg)
            return None
    
    def toggle_recording(self) -> bool:
        """
        Переключить состояние записи.
        
        Returns:
            True если запись началась, False если остановилась
        """
        if self.is_recording:
            self.stop_recording()
            return False
        else:
            return self.start_recording()
    
    # === Внутренние методы ===
    
    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Callback функция для аудио потока"""
        if self._state == RecordingState.RECORDING:
            self._audio_chunks.append(indata.copy())
            
            # Вычисляем уровень звука для визуализации
            if self._on_audio_update:
                self._on_audio_update(indata, self.audio_data)
    
    # === Статические методы ===
    
    @staticmethod
    def list_devices() -> List[dict]:
        """
        Получить список доступных аудиоустройств.
        
        Returns:
            Список словарей с информацией об устройствах
        """
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                devices.append({
                    'id': i,
                    'name': dev['name'],
                    'channels': dev['max_input_channels'],
                    'default_samplerate': dev['default_samplerate'],
                    'is_default': i == sd.default.device[0]
                })
        return devices
    
    @staticmethod
    def get_default_device() -> Optional[dict]:
        """Получить устройство записи по умолчанию"""
        try:
            device_id = sd.default.device[0]
            if device_id >= 0:
                dev = sd.query_devices(device_id)
                return {
                    'id': device_id,
                    'name': dev['name'],
                    'channels': dev['max_input_channels'],
                    'default_samplerate': dev['default_samplerate'],
                    'is_default': True
                }
        except Exception:
            pass
        return None
