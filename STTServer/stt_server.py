import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
import tempfile
import os
import logging
from typing import Optional

from config_manager import ConfigManager

from logger import get_logger


class STTServer:
    """
    STT сервер на основе faster-whisper и FastAPI
    """
    
    def __init__(self, config: ConfigManager):
        """
        Инициализация STT сервера
        
        Args:
            config: Конфиг приложения
        """
        self.config = config
        
        # Инициализация модели
        self.model: Optional[WhisperModel] = None
        
        # Инициализация FastAPI приложения
        self.app = FastAPI(
            title="STT Whisper Server",
            description="Сервис распознавания речи",
            version="1.0.0"
        )
        
        # Регистрация маршрутов
        self._setup_routes()
        
        # Настройка логирования
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка логирования"""
        log_level = self.config.get("logging.level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=self.config.get("logging.format", "%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger = get_logger(__name__)
    
    def _setup_routes(self):
        """Регистрация маршрутов FastAPI"""
        
        @self.app.get("/")
        def read_root():
            return {
                "message": "STT Server is running",
                "endpoints": [
                    "POST /transcribe/ - распознать аудио",
                    "GET /health - проверка состояния",
                ]
            }
        
        @self.app.post("/transcribe/")
        async def transcribe_audio(audio: UploadFile = File(...)):
            """
            Принимает аудио файл, возвращает текст
            """
            self.logger.info("Получен запрос на расшифровку аудио")
            # Загружаем модель при первом запросе (LazyLoading)
            if self.model is None:
                self.logger.info("Loading Whisper model...")
                try:
                    self.model = WhisperModel(
                        model_size_or_path=self.config.get_model_size(),
                        device=self.config.get_model_device(),
                        compute_type=self.config.get_model_compute_type()
                    )
                    self.logger.info("Model loaded successfully!")
                except Exception as e:
                    self.logger.error(f"Failed to load model: {e}")
                    return JSONResponse(
                        content={"error": f"Model loading failed: {str(e)}"},
                        status_code=500
                    )
            
            # Сохраняем временный файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                content = await audio.read()
                tmp.write(content)
                tmp_path = tmp.name
            
            try:
                # Транскрибируем
                segments, info = self.model.transcribe(tmp_path)
                
                # Собираем текст
                text = " ".join([segment.text for segment in segments])
                
                self.logger.info(f"Transcription successful: {len(text)} chars, language: {info.language}")
                
                return JSONResponse(
                    content={
                        "text": text.strip(),
                        "language": info.language,
                        "duration": info.duration,
                        "model": self.config.get_model_size()
                    },
                    status_code=200
                )
                
            except Exception as e:
                self.logger.error(f"Transcription error: {e}")
                return JSONResponse(
                    content={"error": f"Transcription failed: {str(e)}"},
                    status_code=500
                )
            
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        @self.app.get("/health")
        def health_check():
            """Проверка состояния сервера"""
            return {
                "status": "ok" if self.model is not None else "initializing",
                "model_loaded": self.model is not None,
                "model": self.config.get_model_size(),
                "server": f"{self.config.get_server_url()}"
            }
    
    def load_model(self):
        """Предзагрузка модели (опционально)"""
        if self.model is None:
            self.logger.info("Pre-loading Whisper model...")
            try:
                self.model = WhisperModel(
                    model_size_or_path=self.config.get_model_size(),
                    device=self.config.get_model_device(),
                    compute_type=self.config.get_model_compute_type()
                )
                self.logger.info("Model pre-loaded successfully!")
            except Exception as e:
                self.logger.error(f"Failed to pre-load model: {e}")
                raise
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None, reload: Optional[bool] = None):
        """
        Запуск сервера
        
        Args:
            host: Хост для запуска (если None, берется из конфигурации)
            port: Порт для запуска (если None, берется из конфигурации)
            reload: Включить авто-перезагрузку (если None, берется из конфигурации)
        """
        # Определяем параметры запуска
        server_host = host or self.config.get_server_host()
        server_port = port or self.config.get_server_port()
        
        # Предзагрузка модели если требуется
        if self.config.get("server.preload_model", False):
            self.load_model()
        
        self.logger.info(f"🚀 Starting STT Server on {server_host}:{server_port}")
        self.logger.info(f"📋 Model: {self.config.get_model_size()} on {self.config.get_model_device()}")
        self.logger.info(f"🔗 Endpoint: http://{server_host}:{server_port}/transcribe/")
        
        # Запуск сервера
        uvicorn.run(
            self.app,
            host=server_host,
            port=server_port,
            log_level="info"
        )
    
    def get_app(self):
        """Получить FastAPI приложение (для тестирования или интеграции)"""
        return self.app
