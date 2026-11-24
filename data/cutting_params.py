"""
Параметры раскроя для разных материалов
"""

import json
import pathlib

# Параметры раскроя по умолчанию
DEFAULT_CUTTING_PARAMS = {
    "profile": {
        "default": {"length": 6000, "cut": 10}
    },
    "busbar": {
        "default": {"length": 6000, "cut": 10}
    },
    "laser": {
        "default": {"width": 1250, "height": 2500, "cut": 6}
    },
    "punch": {
        "default": {"width": 1200, "height": 2500, "cut": 15},
        "оц_2.0мм": {"width": 1200, "height": 2500, "cut": 15},
        "ст3_1.5мм": {"width": 1200, "height": 2500, "cut": 15}
    },
    "cutting": {
        "default": {"width": 1250, "height": 2500, "cut": 2}
    }
}


def load_cutting_params() -> dict:
    """
    Загружает параметры раскроя из файла cutting_params.json
    Если файла нет, создает его из параметров по умолчанию
    """
    params_file = pathlib.Path('./cutting_params.json')
    
    if params_file.exists():
        try:
            with open(params_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки параметров: {e}")
            return DEFAULT_CUTTING_PARAMS
    else:
        try:
            with open(params_file, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CUTTING_PARAMS, f, indent=4, ensure_ascii=False)
            return DEFAULT_CUTTING_PARAMS
        except Exception as e:
            print(f"Ошибка создания параметров: {e}")
            return DEFAULT_CUTTING_PARAMS


def save_cutting_params(params: dict):
    """Сохраняет параметры раскроя в файл"""
    params_file = pathlib.Path('./cutting_params.json')
    with open(params_file, 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=4, ensure_ascii=False)


def get_material_params(category: str, material: str) -> dict:
    """
    Возвращает параметры раскроя для конкретного материала
    
    Args:
        category: Категория (profile, busbar, laser, punch, cutting)
        material: Название материала
        
    Returns:
        Словарь с параметрами
    """
    params = load_cutting_params()
    
    # Сначала ищем параметры для конкретного материала
    if category in params and material in params[category]:
        return params[category][material]
    
    # Затем параметры по умолчанию для категории
    if category in params and "default" in params[category]:
        return params[category]["default"]
    
    # Самые стандартные значения
    if category in ['profile', 'busbar']:
        return {"length": 6000, "cut": 10}
    else:
        return {"width": 1250, "height": 2500, "cut": 2}