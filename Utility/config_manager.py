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
            # Trying to search config.yaml in dir level above (project root)
            parent_dir = Path(__file__).resolve().parent.parent
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
    
    # === Методы для горячих клавиш ===
    
    def get_hotkeys(self) -> Dict[str, Any]:
        """Получить все настройки горячих клавиш"""
        return self.get('hotkeys', {})
    
    def get_hotkey(self, name: str) -> Dict[str, Any]:
        """
        Получить настройки конкретной горячей клавиши.
        
        Args:
            name: Имя горячей клавиши (например, 'record')
        
        Returns:
            Словарь с keys, mode, description
        """
        default_hotkey = {
            'keys': 'alt_gr',
            'mode': 'toggle',
            'description': 'Запись голоса'
        }
        return self.get(f'hotkeys.{name}', default_hotkey)
    
    def get_hotkey_keys(self, name: str) -> str:
        """Получить клавиши для горячей клавиши"""
        return self.get(f'hotkeys.{name}.keys', 'alt_gr')
    
    def get_hotkey_mode(self, name: str) -> str:
        """Получить режим горячей клавиши (toggle/ptt)"""
        return self.get(f'hotkeys.{name}.mode', 'toggle')
    
    # === Методы для аудио ===
    
    def get_audio_sample_rate(self) -> int:
        """Получить частоту дискретизации"""
        return self.get('audio.sample_rate', 16000)
    
    def get_audio_channels(self) -> int:
        """Получить количество каналов"""
        return self.get('audio.channels', 1)
    
    def get_audio_device(self) -> Optional[int]:
        """Получить ID устройства записи"""
        return self.get('audio.device', None)
    
    # === Методы для клиента ===
    
    def get_output_mode(self) -> str:
        """Получить режим вывода (clipboard/typein/both)"""
        return self.get('client.output_mode', 'typein')
    
    def get_auto_paste(self) -> bool:
        """Получить настройку авто-вставки Enter"""
        return self.get('client.auto_paste', False)
    
    def get_add_space(self) -> bool:
        """Получить настройку добавления пробела"""
        return self.get('client.add_space', False)
    
    # === Методы для GUI ===
    
    def is_gui_enabled(self) -> bool:
        """Проверить, включен ли GUI"""
        return self.get('gui.enabled', True)
    
    def get_gui_settings(self) -> Dict[str, Any]:
        """Получить все настройки GUI"""
        defaults = {
            'enabled': True,
            'show_popup': True,
            'show_timer': True,
            'show_visualizer': True,
            'minimize_to_tray': True,
            'start_minimized': False,
            'autostart': False
        }
        return self.get('gui', defaults)
    
    def show_popup(self) -> bool:
        """Показывать ли popup при записи"""
        return self.get('gui.show_popup', True)
    
    def minimize_to_tray(self) -> bool:
        """Сворачивать ли в трей при закрытии"""
        return self.get('gui.minimize_to_tray', True)
    
    def start_minimized(self) -> bool:
        """Запускать ли свернутым"""
        return self.get('gui.start_minimized', False)
    
    def is_autostart_enabled(self) -> bool:
        """Включен ли автозапуск"""
        return self.get('gui.autostart', False)
    
    # === Методы для изменения конфигурации ===
    
    def set(self, key: str, value: Any) -> bool:
        """
        Установить значение конфигурации.
        
        Args:
            key: Ключ конфигурации (например: 'server.port')
            value: Новое значение
        
        Returns:
            True если значение установлено
        """
        if self._config is None:
            self._config = {}
        
        keys = key.split('.')
        data = self._config
        
        # Проходим по всем ключам кроме последнего
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        # Устанавливаем значение
        data[keys[-1]] = value
        return True
    
    def save(self) -> bool:
        """
        Сохранить конфигурацию в файл.
        
        Returns:
            True если сохранение успешно
        """
        if not self._config_path or not self._config:
            return False
        
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            logging.info(f"✅ Конфигурация сохранена в {self._config_path}")
            return True
        except Exception as e:
            logging.error(f"Ошибка сохранения конфигурации: {e}")
            return False


# Создаем глобальный экземпляр для удобного доступа
config = ConfigManager()
