"""
Модуль управления горячими клавишами для голосового клиента
"""

import threading
from typing import Optional, Callable, Dict, Set, List, Tuple
from pynput import keyboard
from pynput.keyboard import Key, KeyCode
from Client.HotkeyManager import HotkeyAction, HotkeyMode, HotkeyState
from logger import get_logger


logger = get_logger(__name__)


class HotkeyManager:
    """
    Менеджер горячих клавиш с поддержкой:
    - Toggle режима (нажатие включает/выключает)
    - Push-to-Talk режима (удержание для записи)
    - Комбинированных клавиш (Ctrl+Shift+A)
    - Обнаружения конфликтов
    """
    
    def __init__(self):
        self._actions: Dict[str, HotkeyAction] = {}
        self._state = HotkeyState()
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()
        
        # Инициализация логгера
        logger.info("HotkeyManager инициализирован")
        
        # Специальные клавиши для конвертации
        self._special_keys = {
            'alt_gr': Key.alt_gr,
            'alt': Key.alt,
            'alt_l': Key.alt_l,
            'alt_r': Key.alt_r,
            'ctrl': Key.ctrl,
            'ctrl_l': Key.ctrl_l,
            'ctrl_r': Key.ctrl_r,
            'shift': Key.shift,
            'shift_l': Key.shift_l,
            'shift_r': Key.shift_r,
            'cmd': Key.cmd,
            'cmd_l': Key.cmd_l,
            'cmd_r': Key.cmd_r,
            'space': Key.space,
            'enter': Key.enter,
            'tab': Key.tab,
            'esc': Key.esc,
            'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
            'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
            'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
        }
    
    # === Регистрация горячих клавиш ===
    
    def register(
        self,
        name: str,
        keys: str | List[str] | keyboard.Key | keyboard.KeyCode | Tuple,
        callback: Callable[[], None],
        mode: HotkeyMode = HotkeyMode.TOGGLE,
        description: str = "",
        on_release: Optional[Callable[[], None]] = None
    ) -> bool:
        """
        Зарегистрировать горячую клавишу.
        
        Args:
            name: Уникальное имя действия
            keys: Клавиша или комбинация (строка, список или tuple)
            callback: Функция при активации
            mode: Режим работы (toggle/ptt)
            description: Описание для UI
            on_release: Callback при отпускании (для PTT)
        
        Returns:
            True если регистрация успешна
        """
        logger.debug(f"Регистрация горячей клавиши: {name}, клавиши: {keys}, режим: {mode}")
        logger.info(f"🔥 HOTKEY REGISTRATION EVENT: {name} (количество регистраций: {len(self._actions) + 1})")
        
        # Конвертируем ключи в tuple
        key_tuple = self._parse_keys(keys)
        if not key_tuple:
            logger.error(f"❌ Неверный формат клавиш: {keys}")
            return False
        
        # Проверяем конфликты
        conflicts = self._check_conflicts(name, key_tuple)
        if conflicts:
            logger.warning(f"⚠️ Конфликт горячих клавиш: {name} конфликтует с {conflicts}")
        
        action = HotkeyAction(
            name=name,
            keys=key_tuple,
            callback=callback,
            mode=mode,
            description=description,
            on_release=on_release
        )
        
        self._actions[name] = action
        logger.info(f"✅ Горячая клавиша '{name}' успешно зарегистрирована: {key_tuple}")
        return True
    
    def unregister(self, name: str) -> bool:
        """Удалить регистрацию горячей клавиши"""
        if name in self._actions:
            del self._actions[name]
            return True
        return False
    
    def clear(self):
        """Удалить все регистрации"""
        with self._lock:
            count = len(self._actions)
            self._actions.clear()
            logger.info(f"🧹 HOTKEY CLEAR EVENT: удалено {count} горячих клавиш")
    
    # === Парсинг клавиш ===
    
    def _parse_keys(self, keys) -> Tuple:
        """Преобразовать различные форматы клавиш в tuple"""
        logger.debug(f"🔍 ПАРСИНГ КЛАВИШ: {keys} (тип: {type(keys)})")
        
        if isinstance(keys, tuple):
            logger.debug(f"✅ Входные данные уже в формате tuple: {keys}")
            return keys
        
        if isinstance(keys, (Key, KeyCode)):
            result = (keys,)
            logger.debug(f"✅ Преобразование Key/KeyCode в tuple: {result}")
            return result
        
        if isinstance(keys, str):
            # Одна клавиша или комбинация через +
            result = self._parse_key_string(keys)
            logger.debug(f"✅ Парсинг строки '{keys}' результат: {result}")
            return result
        
        if isinstance(keys, list):
            # Список клавиш
            result = []
            for k in keys:
                parsed = self._parse_single_key(k)
                if parsed:
                    result.append(parsed)
            final_result = tuple(result) if result else ()
            logger.debug(f"✅ Парсинг списка {keys} результат: {final_result}")
            return final_result
        
        logger.warning(f"❌ Неподдерживаемый тип клавиш: {type(keys)}, значение: {keys}")
        return ()
    
    def _parse_key_string(self, key_str: str) -> Tuple:
        """Парсинг строки типа 'Ctrl+Shift+A' или 'alt_gr'"""
        key_str = key_str.strip().lower()
        logger.debug(f"Парсинг строки клавиш: '{key_str}'")
        
        # Проверяем комбинацию через +
        if '+' in key_str:
            parts = [p.strip() for p in key_str.split('+')]
            logger.debug(f"Обнаружена комбинация, части: {parts}")
            keys = []
            for part in parts:
                key = self._parse_single_key(part)
                if key:
                    keys.append(key)
                else:
                    logger.warning(f"Не удалось распарсить часть '{part}' в комбинации '{key_str}'")
            result = tuple(keys)
            logger.debug(f"Результат парсинга комбинации '{key_str}': {result}")
            return result
        
        # Одна клавиша
        key = self._parse_single_key(key_str)
        result = (key,) if key else ()
        logger.debug(f"Результат парсинг одиночной клавиши '{key_str}': {result}")
        return result
    
    def _parse_single_key(self, key_str: str) -> Optional[keyboard.Key | keyboard.KeyCode]:
        """Парсинг одной клавиши"""
        key_str = key_str.strip().lower()
        logger.debug(f"🔍 ПАРСИНГ ОДИНОЧНОЙ КЛАВИШИ: '{key_str}'")
        
        # Специальные клавиши
        if key_str in self._special_keys:
            result = self._special_keys[key_str]
            logger.debug(f"✅ Найдена специальная клавиша: '{key_str}' -> {result}")
            return result
        
        # Одиночный символ (включая цифры)
        if len(key_str) == 1:
            result = KeyCode.from_char(key_str)
            logger.debug(f"✅ Создан KeyCode для символа: '{key_str}' -> {result}, тип: {type(result)}")
            logger.debug(f"   Свойства KeyCode: char='{getattr(result, 'char', 'N/A')}', vk={getattr(result, 'vk', 'N/A')}")
            return result
        
        # F-клавиши
        if key_str.startswith('f') and key_str[1:].isdigit():
            f_num = int(key_str[1:])
            if 1 <= f_num <= 12:
                result = getattr(Key, f'f{f_num}', None)
                logger.debug(f"✅ Найдена F-клавиша: f{f_num} -> {result}")
                return result
        
        # Дополнительная диагностика для цифровых клавиш
        if key_str.isdigit():
            logger.debug(f"🔍 Обнаружена цифровая клавиша: '{key_str}', пробуем создать KeyCode")
            try:
                result = KeyCode.from_char(key_str)
                logger.debug(f"✅ Успешно создан KeyCode для цифры: '{key_str}' -> {result}")
                logger.debug(f"   Свойства KeyCode: char='{getattr(result, 'char', 'N/A')}', vk={getattr(result, 'vk', 'N/A')}")
                return result
            except Exception as e:
                logger.error(f"❌ Ошибка при создании KeyCode для цифры '{key_str}': {e}")
        
        logger.warning(f"❌ Не удалось распарсить клавишу: '{key_str}'")
        return None
    
    # === Проверка конфликтов ===
    
    def _check_conflicts(self, name: str, keys: Tuple) -> List[str]:
        """Проверить конфликты с существующими горячими клавишами"""
        logger.debug(f"Проверка конфликтов для '{name}': {keys}")
        conflicts = []
        
        for action_name, action in self._actions.items():
            if action_name == name:
                continue
            # Проверяем пересечение множеств клавиш
            action_keys_set = set(action.keys)
            new_keys_set = set(keys)
            is_conflict = action_keys_set == new_keys_set
            
            logger.debug(f"  Сравнение с '{action_name}': {action.keys} == {keys} -> {is_conflict}")
            
            if is_conflict:
                conflicts.append(action_name)
                logger.warning(f"  Конфликт обнаружен: '{name}' конфликтует с '{action_name}'")
        
        if conflicts:
            logger.warning(f"Итоговые конфликты для '{name}': {conflicts}")
        else:
            logger.debug(f"Конфликты для '{name}' не обнаружены")
            
        return conflicts
    
    def get_conflicts(self) -> Dict[str, List[str]]:
        """Получить все конфликты между горячими клавишами"""
        conflicts = {}
        for name, action in self._actions.items():
            action_conflicts = self._check_conflicts(name, action.keys)
            if action_conflicts:
                conflicts[name] = action_conflicts
        return conflicts
    
    # === Запуск и остановка ===
    
    def start(self):
        """Запустить слушатель горячих клавиш"""
        if self._listener is not None:
            logger.warning("Попытка запустить уже запущенный слушатель")
            return
        
        logger.info("Запуск слушателя горячих клавиш")
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._listener.start()
        logger.info("✅ Менеджер горячих клавиш запущен")
    
    def stop(self):
        """Остановить слушатель"""
        if self._listener:
            logger.info("Остановка слушателя горячих клавиш")
            self._listener.stop()
            self._listener = None
        self._state.clear()
        self._state.active_hotkey = None
        logger.info("⏹️ Менеджер горячих клавиш остановлен")
    
    def is_running(self) -> bool:
        """Проверить, запущен ли слушатель"""
        return self._listener is not None and self._listener.is_alive()
    
    # === Обработка событий ===
    
    def _on_press(self, key):
        """Обработка нажатия клавиши"""
        logger.debug(f"Нажатие клавиши: {key}, текущие нажатые: {self._state.pressed_keys}")
        
        self._state.add_key(key)
        logger.debug(f"Добавлена клавиша {key}, текущее состояние: {self._state.pressed_keys}")
        
        # Ищем совпадающую горячую клавишу
        for name, action in self._actions.items():
            logger.debug(f"🔍 Проверка действия '{name}': ожидаемые клавиши={action.keys}")
            match_result = self._keys_match(action.keys, self._state.pressed_keys)
            logger.debug(f"Проверка горячего клавиши '{name}': требуется {action.keys}, нажато {self._state.pressed_keys}, совпадение: {match_result}")
            
            if match_result:
                logger.info(f"Найдено совпадение для '{name}', активация")
                self._activate_hotkey(action)
                break
            else:
                logger.debug(f"Совпадение для '{name}' не найдено")
    
    def _on_release(self, key):
        """Обработка отпускания клавиши"""
        logger.debug(f"Отпускание клавиши: {key}, текущие нажатые: {self._state.pressed_keys}")
        
        # Удаляем из нажатых
        self._state.discard_key(key)
        logger.debug(f"Удалена клавиша {key}, текущее состояние: {self._state.pressed_keys}")
        
        # Проверяем PTT режим
        if self._state.active_hotkey:
            logger.debug(f"Активная горячая клавиша: {self._state.active_hotkey}")
            action = self._actions.get(self._state.active_hotkey)
            if action and action.mode == HotkeyMode.PUSH_TO_TALK:
                # Проверяем, все ли клавиши ещё нажаты
                match_result = self._keys_match(action.keys, self._state.pressed_keys)
                logger.debug(f"PTT проверка для '{self._state.active_hotkey}': требуется {action.keys}, нажато {self._state.pressed_keys}, совпадение: {match_result}")
                
                if not match_result:
                    logger.info(f"Деактивация PTT горячего клавиши '{self._state.active_hotkey}'")
                    self._deactivate_hotkey(action)
                else:
                    logger.debug(f"PTT горячего клавиша '{self._state.active_hotkey}' остаётся активной")
    
    def _keys_match(self, required: Tuple, pressed: Set) -> bool:
        """Проверить соответствие нажатых клавиш требуемым"""
        required_set = set(required)
        result = required_set == pressed
        
        # Детальная диагностика для отладки
        logger.debug(f"=== ДИАГНОСТИКА СРАВНЕНИЯ КЛАВИШ ===")
        logger.debug(f"Требуемые клавиши: {required_set}")
        logger.debug(f"Нажатые клавиши: {pressed}")
        logger.debug(f"Типы требуемых: {[type(k) for k in required_set]}")
        logger.debug(f"Типы нажатых: {[type(k) for k in pressed]}")
        
        # Проверка по отдельности для каждой клавиши
        for req_key in required_set:
            for press_key in pressed:
                logger.debug(f"Сравнение: {req_key} ({type(req_key)}) == {press_key} ({type(press_key)})")
                if req_key == press_key:
                    logger.debug(f"✅ Клавиши совпадают: {req_key}")
                else:
                    logger.debug(f"❌ Клавиши не совпадают: {req_key} != {press_key}")
        
        logger.debug(f"Итоговый результат сравнения: {result}")
        logger.debug(f"=== КОНЕЦ ДИАГНОСТИКИ ===")
        
        return result
    
    def _activate_hotkey(self, action: HotkeyAction):
        """Активировать горячую клавишу"""
        logger.info(f"Активация горячего клавиши '{action.name}', режим: {action.mode}")
        
        # Для PTT - активируем только если не была активна
        if action.mode == HotkeyMode.PUSH_TO_TALK:
            if self._state.active_hotkey == action.name:
                logger.debug(f"PTT горячего клавиши '{action.name}' уже активна, пропускаем")
                return  # Уже активна
            self._state.active_hotkey = action.name
            logger.info(f"PTT горячего клавиши '{action.name}' активирована, вызов callback")
            action.callback()
        
        # Для Toggle - переключаем
        elif action.mode == HotkeyMode.TOGGLE:
            logger.info(f"Toggle горячего клавиши '{action.name}' вызов callback")
            action.callback()
    
    def _deactivate_hotkey(self, action: HotkeyAction):
        """Деактивировать горячую клавишу (для PTT)"""
        logger.info(f"Деактивация горячего клавиши '{action.name}'")
        self._state.active_hotkey = None
        if action.on_release:
            logger.debug(f"Вызов on_release callback для '{action.name}'")
            action.on_release()
    
    # === Информационные методы ===
    
    def get_registered_hotkeys(self) -> Dict[str, HotkeyAction]:
        """Получить все зарегистрированные горячие клавиши"""
        return self._actions.copy()
    