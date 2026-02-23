import tempfile
from typing import Optional
from dataclasses import dataclass
import numpy as np
import soundfile as sf

from logger import get_logger


logger = get_logger(__name__)


@dataclass
class AudioData:
    """Контейнер для записанных аудиоданных"""
    samples: np.ndarray
    sample_rate: int
    channels: int
    duration: float
    
    def save_to_wav(self, path: str) -> bool:
        """Сохранить аудио в WAV файл"""
        try:
            sf.write(path, self.samples, self.sample_rate)
            logger.debug(f"✅ Аудио сохранено по пути {path=}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения аудио: {e}")
            return False
    
    def save_to_temp_wav(self) -> Optional[str]:
        """Сохранить аудио во временный WAV файл"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                sf.write(tmp_path, self.samples, self.sample_rate)
                logger.debug(f"✅ Аудио сохранено по временному пути {tmp_path=}")
            return tmp_path
        except Exception as e:
            logger.error(f"❌ Ошибка создания временного файла: {e}")
            return None
