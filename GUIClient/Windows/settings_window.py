"""
Окно настроек для EchoType
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, 
    QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QFormLayout, QLineEdit, QTabWidget,
    QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QKeySequence

from GUIClient.Widgets.hotkey_edit import HotkeyEdit
from Client.AudioRecorder import AudioRecorder

from Utility import ConfigManager, get_logger


logger = get_logger(__name__)


class SettingsWindow(QDialog):
    """
    Окно настроек EchoType.
    Содержит вкладки: Горячие клавиши, Аудио, Вывод, GUI, Сервер.
    """
    
    settings_saved = pyqtSignal()
    
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        
        self.config = config
        
        self.setWindowTitle("Настройки EchoType")
        self.setMinimumSize(500, 450)
        self.resize(550, 500)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        
        # Табы
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Создаём вкладки
        self.tabs.addTab(self._create_hotkeys_tab(), "🎯 Горячие клавиши")
        self.tabs.addTab(self._create_audio_tab(), "🎤 Аудио")
        self.tabs.addTab(self._create_output_tab(), "📤 Вывод")
        self.tabs.addTab(self._create_gui_tab(), "🖥️ Интерфейс")
        self.tabs.addTab(self._create_server_tab(), "🔗 Сервер")
        
        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _create_hotkeys_tab(self) -> QWidget:
        """Создать вкладку горячих клавиш"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Группа основной записи
        record_group = QGroupBox("Запись голоса")
        form = QFormLayout(record_group)
        
        # Горячая клавиша записи
        self.record_hotkey_edit = HotkeyEdit()
        form.addRow("Горячая клавиша:", self.record_hotkey_edit)
        
        # Режим записи
        self.record_mode_combo = QComboBox()
        self.record_mode_combo.addItems([
            "Toggle (нажатие вкл/выкл)",
            "Push-to-Talk (удержание)"
        ])
        form.addRow("Режим:", self.record_mode_combo)
        
        layout.addWidget(record_group)
        
        # Информация
        info_label = QLabel(
            "💡 Toggle: одно нажатие начинает запись, повторное - останавливает.\n"
            "💡 Push-to-Talk: запись идёт пока клавиша нажата.\n"
            "⚠️ Инвалидность pyqt не позволяет ему различать левый альт от правого, но под капотом оно работает! Т.е. при нажатии alt_gr, на экране будет написано alt, но обработка будет повешена именно на правый альт"
        )
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        return widget
    
    def _create_audio_tab(self) -> QWidget:
        """Создать вкладку аудио"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Устройство записи
        device_group = QGroupBox("Устройство записи")
        form = QFormLayout(device_group)
        
        self.audio_device_combo = QComboBox()
        self._populate_audio_devices()
        form.addRow("Устройство:", self.audio_device_combo)
        
        layout.addWidget(device_group)
        
        # Параметры аудио
        params_group = QGroupBox("Параметры")
        form = QFormLayout(params_group)
        
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["16000", "22050", "44100", "48000"])
        form.addRow("Частота дискретизации:", self.sample_rate_combo)
        
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["1 (Моно)", "2 (Стерео)"])
        form.addRow("Каналы:", self.channels_combo)
        
        layout.addWidget(params_group)
        
        # Информация
        info_label = QLabel(
            "ℹ️ Для Whisper рекомендуется частота 16000 Гц и моно-запись."
        )
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        return widget
    
    def _populate_audio_devices(self):
        """Заполнить список аудиоустройств"""
        self.audio_device_combo.addItem("По умолчанию", None)
        
        devices = AudioRecorder.list_devices()
        for dev in devices:
            name = dev['name']
            if dev['is_default']:
                name += " (по умолчанию)"
            self.audio_device_combo.addItem(name, dev['id'])
    
    def _create_output_tab(self) -> QWidget:
        """Создать вкладку вывода"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Режим вывода
        output_group = QGroupBox("Режим вывода")
        form = QFormLayout(output_group)
        
        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItems([
            "Ввод текста (typein)",
            "Буфер обмена (clipboard)",
            "Оба режима (both)"
        ])
        form.addRow("Режим:", self.output_mode_combo)
        
        layout.addWidget(output_group)
        
        # Дополнительные опции
        options_group = QGroupBox("Дополнительные опции")
        form = QFormLayout(options_group)
        
        self.auto_paste_check = QCheckBox("Нажимать Enter после вставки")
        form.addRow(self.auto_paste_check)
        
        self.add_space_check = QCheckBox("Добавлять пробел перед текстом")
        form.addRow(self.add_space_check)
        
        layout.addWidget(options_group)
        
        layout.addStretch()
        return widget
    
    def _create_gui_tab(self) -> QWidget:
        """Создать вкладку GUI"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Popup окно
        popup_group = QGroupBox("Всплывающее окно")
        form = QFormLayout(popup_group)
        
        self.show_popup_check = QCheckBox("Показывать при записи")
        form.addRow(self.show_popup_check)
        
        layout.addWidget(popup_group)
        
        # Поведение
        behavior_group = QGroupBox("Поведение")
        form = QFormLayout(behavior_group)
        
        self.minimize_to_tray_check = QCheckBox("Сворачивать в трей при закрытии")
        form.addRow(self.minimize_to_tray_check)
        
        self.start_minimized_check = QCheckBox("Запускать свернутым")
        form.addRow(self.start_minimized_check)
        
        self.autostart_check = QCheckBox("Автозапуск при старте системы")
        form.addRow(self.autostart_check)
        
        layout.addWidget(behavior_group)
        
        layout.addStretch()
        return widget
    
    def _create_server_tab(self) -> QWidget:
        """Создать вкладку сервера"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Подключение
        conn_group = QGroupBox("Подключение")
        form = QFormLayout(conn_group)
        
        self.server_host_edit = QLineEdit()
        self.server_host_edit.setPlaceholderText("localhost")
        form.addRow("Хост:", self.server_host_edit)
        
        self.server_port_spin = QSpinBox()
        self.server_port_spin.setRange(1, 65535)
        self.server_port_spin.setValue(8100)
        form.addRow("Порт:", self.server_port_spin)
        
        layout.addWidget(conn_group)
        
        # Модель
        model_group = QGroupBox("Модель Whisper")
        form = QFormLayout(model_group)
        
        self.model_size_combo = QComboBox()
        self.model_size_combo.addItems([
            "tiny", "base", "small", "medium", "large-v2", "large-v3"
        ])
        form.addRow("Размер модели:", self.model_size_combo)
        
        self.model_device_combo = QComboBox()
        self.model_device_combo.addItems(["cuda", "cpu"])
        form.addRow("Устройство:", self.model_device_combo)
        
        self.compute_type_combo = QComboBox()
        self.compute_type_combo.addItems(["int8", "float16", "float32"])
        form.addRow("Тип вычислений:", self.compute_type_combo)
        
        layout.addWidget(model_group)
        
        # Информация о моделях
        info_label = QLabel(
            "ℹ️ tiny - самая быстрая, но менее точная\n"
            "ℹ️ large-v3 - самая точная, но медленная\n"
            "ℹ️ CUDA требует NVIDIA GPU с поддержкой CUDA"
        )
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addStretch()
        return widget
    
    # === Загрузка и сохранение ===
    
    def _load_settings(self):
        """Загрузить настройки в UI"""
        # Горячие клавиши
        record_keys = self.config.get_hotkey_keys('record')
        self.record_hotkey_edit.setKeySequence(
            QKeySequence(record_keys.replace("_", "+"))
        )
        
        record_mode = self.config.get_hotkey_mode('record')
        self.record_mode_combo.setCurrentIndex(0 if record_mode == 'toggle' else 1)
        
        # Аудио
        sample_rate = self.config.get_audio_sample_rate()
        idx = self.sample_rate_combo.findText(str(sample_rate))
        if idx >= 0:
            self.sample_rate_combo.setCurrentIndex(idx)
        
        channels = self.config.get_audio_channels()
        self.channels_combo.setCurrentIndex(0 if channels == 1 else 1)
        
        device = self.config.get_audio_device()
        if device is None:
            self.audio_device_combo.setCurrentIndex(0)
        else:
            idx = self.audio_device_combo.findData(device)
            if idx >= 0:
                self.audio_device_combo.setCurrentIndex(idx)
        
        # Вывод
        output_mode = self.config.get_output_mode()
        mode_idx = {"typein": 0, "clipboard": 1, "both": 2}.get(output_mode, 0)
        self.output_mode_combo.setCurrentIndex(mode_idx)
        
        self.auto_paste_check.setChecked(self.config.get_auto_paste())
        self.add_space_check.setChecked(self.config.get_add_space())
        
        # GUI
        self.show_popup_check.setChecked(self.config.show_popup())

        self.minimize_to_tray_check.setChecked(self.config.minimize_to_tray())
        self.start_minimized_check.setChecked(self.config.start_minimized())
        self.autostart_check.setChecked(self.config.is_autostart_enabled())
        
        # Сервер
        self.server_host_edit.setText(self.config.get_server_host())
        self.server_port_spin.setValue(self.config.get_server_port())
        
        self.model_size_combo.setCurrentText(self.config.get_model_size())
        self.model_device_combo.setCurrentText(self.config.get_model_device())
        self.compute_type_combo.setCurrentText(self.config.get_model_compute_type())
    
    def _save_settings(self):
        """Сохранить настройки из UI"""
        # Горячие клавиши
        record_keys = self.record_hotkey_edit.get_hotkey_string()
        if record_keys:
            self.config.set('hotkeys.record.keys', record_keys)
        
        record_mode = 'toggle' if self.record_mode_combo.currentIndex() == 0 else 'ptt'
        self.config.set('hotkeys.record.mode', record_mode)
        
        # Аудио
        sample_rate = int(self.sample_rate_combo.currentText())
        self.config.set('audio.sample_rate', sample_rate)
        
        channels = 1 if self.channels_combo.currentIndex() == 0 else 2
        self.config.set('audio.channels', channels)
        
        device = self.audio_device_combo.currentData()
        self.config.set('audio.device', device)
        
        # Вывод
        output_modes = ['typein', 'clipboard', 'both']
        self.config.set('client.output_mode', output_modes[self.output_mode_combo.currentIndex()])
        self.config.set('client.auto_paste', self.auto_paste_check.isChecked())
        self.config.set('client.add_space', self.add_space_check.isChecked())
        
        # GUI
        self.config.set('gui.show_popup', self.show_popup_check.isChecked())
        
        self.config.set('gui.minimize_to_tray', self.minimize_to_tray_check.isChecked())
        self.config.set('gui.start_minimized', self.start_minimized_check.isChecked())
        self.config.set('gui.autostart', self.autostart_check.isChecked())
        
        # Сервер
        self.config.set('server.host', self.server_host_edit.text())
        self.config.set('server.port', self.server_port_spin.value())
        
        self.config.set('model.size', self.model_size_combo.currentText())
        self.config.set('model.device', self.model_device_combo.currentText())
        self.config.set('model.compute_type', self.compute_type_combo.currentText())
        
        # Сохраняем в файл
        if self.config.save():
            self.settings_saved.emit()
            self.accept()
        else:
            # Показываем ошибку
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Ошибка сохранения",
                "Не удалось сохранить настройки в файл."
            )
