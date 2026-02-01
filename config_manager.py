"""
Менеджер конфигурации с паттерном Singleton для YAML файлов
"""

import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

class ConfigManager:
    """
    Singleton класс для управления конфигурацией приложения.
    Загружает конфигурацию из YAML файла один раз и предоставляет к ней доступ.
    """
    
    _instance = None
    _config: Optional[Dict[str, Any]] = None
    _config_path: Optional[str] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Реализация паттерна Singleton"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация - загружает конфигурацию только при первом вызове"""
        if not self._initialized:
            # По умолчанию ищем config.yaml в текущей директории
            parent_dir = Path(__file__).resolve().parent
            self._config_path = Path.joinpath(parent_dir, "config.yaml").absolute().as_posix()
            self.load()
            self._initialized = True
    
    def load(self, config_path: Optional[str] = None) -> bool:
        """
        Загрузка конфигурации из YAML файла
        
        Args:
            config_path: Путь к конфигурационному файлу
            
        Returns:
            bool: True если загрузка успешна, False в случае ошибки
        """
        if config_path:
            self._config_path = config_path
        
        if not self._config_path:
            logging.error("Не указан путь к конфигурационному файлу")
            return False
        
        try:
            # Проверяем существование файла
            if not Path(self._config_path).exists():
                logging.error(f"Конфигурационный файл не найден: {self._config_path}")
                return False
            
            # Загружаем конфигурацию из YAML файла
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            if self._config is None:
                logging.warning(f"Конфигурационный файл пустой: {self._config_path}")
                self._config = {}
            
            logging.info(f"✅ Конфигурация загружена из {self._config_path}")
            return True
            
        except yaml.YAMLError as e:
            logging.error(f"Ошибка парсинга YAML файла {self._config_path}: {e}")
            return False
        except Exception as e:
            logging.error(f"Ошибка загрузки конфигурации: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получить значение конфигурации по ключу
        
        Args:
            key: Ключ конфигурации (например: 'server.port')
            default: Значение по умолчанию если ключ не найден
            
        Returns:
            Значение конфигурации или default
        """
        if self._config is None:
            return default
        
        # Поддержка вложенных ключей через точку
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_all(self) -> Dict[str, Any]:
        """
        Получить всю конфигурацию
        
        Returns:
            Словарь со всей конфигурацией
        """
        return self._config.copy() if self._config else {}
    
    def get_server_host(self):
        """Получить хост сервера"""
        return self.get('server.host', '0.0.0.0')
    
    def get_server_port(self):
        """Получить порт сервера"""
        return self.get('server.port', 8000)
    
    def get_server_url(self) -> str:
        """Получить полный URL сервера"""
        host = self.get_server_host()
        port = self.get_server_port()
        return f"http://{host}:{port}"

    def get_model_size(self):
        """Получить размер модели"""
        return self.get('model.size', 'small')

    def get_model_device(self):
        """Получить устройство для вычислений модели"""
        return self.get('model.device', 'cpu')

    def get_model_compute_type(self):
        """Получить compute_type модели"""
        return self.get('model.compute_type', 'float16')
    
    def get_config_path(self) -> Optional[str]:
        """Получить путь к конфигурационному файлу"""
        return self._config_path
    
    def is_loaded(self) -> bool:
        """Проверка, загружена ли конфигурация"""
        return self._config is not None

# Создаем глобальный экземпляр для удобного доступа
config = ConfigManager()