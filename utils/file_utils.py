"""
Вспомогательные функции для работы с файлами и строками
"""

import re
import pathlib
from datetime import datetime


def sanitize_filename(filename: str) -> str:
    """
    Очищает имя файла от запрещенных символов Windows
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        Очищенное имя файла
    """
    # Запрещенные символы в Windows заменяем на $
    forbidden_chars = r'[\\/*?:"<>|]'
    sanitized = re.sub(forbidden_chars, '$', str(filename))
    
    # Дополнительная замена слешей
    sanitized = sanitized.replace('/', '$').replace('\\', '$')
    
    # Удаляем пробелы в начале и конце
    sanitized = sanitized.strip()
    
    # Ограничиваем длину
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    # Если получилась пустая строка
    if not sanitized:
        sanitized = "unknown"
    
    return sanitized

def get_timestamp() -> str:
    """
    Возвращает текущую метку времени для имен файлов
    
    Returns:
        Строка с датой и временем: YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def ensure_directory(path: pathlib.Path) -> pathlib.Path:
    """
    Создает директорию, если она не существует
    
    Args:
        path: Путь к директории
        
    Returns:
        Путь к директории
    """
    path.mkdir(parents=True, exist_ok=True)
    return path