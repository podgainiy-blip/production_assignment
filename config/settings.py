"""
Управление настройками приложения
Настройки хранятся в файле settings.json рядом с программой
"""

import json
import pathlib
from typing import Dict, Any

# Значения по умолчанию
DEFAULT_SETTINGS = {
    "rename_files": False,      # Переименовывать файлы (по умолчанию ВЫКЛЮЧЕНО)
    "skip_balance": False,      # Режим nolog (по умолчанию ВЫКЛЮЧЕН, включается только вручную в файле)
    "profile_length": 6000,     # Длина заготовки для профиля (мм)
    "profile_cut": 10,          # Ширина реза для профиля (мм)
    "sheet_size": "1250x2500",  # Размер листа по умолчанию
    "sheet_cut": 2              # Ширина реза для листов по умолчанию (мм)
}

# Путь к файлу настроек
SETTINGS_FILE = pathlib.Path("./settings.json")


def load_settings() -> Dict[str, Any]:
    """
    Загружает настройки из файла settings.json
    Если файла нет, создает его с настройками по умолчанию
    """
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Обновляем недостающие ключи значениями по умолчанию
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            return DEFAULT_SETTINGS.copy()
    else:
        # Создаем файл с настройками по умолчанию
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> bool:
    """
    Сохраняет настройки в файл settings.json
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")
        return False


def get_setting(key: str, default: Any = None) -> Any:
    """Получает значение настройки по ключу"""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any) -> bool:
    """Устанавливает значение настройки"""
    settings = load_settings()
    settings[key] = value
    return save_settings(settings)