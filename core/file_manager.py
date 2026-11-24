"""
Управление файлами (копирование, создание папок)
"""

import pathlib
import shutil
from typing import List, Tuple, Optional


class FileManager:
    """
    Класс для управления файлами
    """
    
    def __init__(self, logger=None):
        """
        Args:
            logger: Объект логгера
        """
        self.logger = logger
        self.missing_files = []
    
    def copy_file(self, source: pathlib.Path, dest: pathlib.Path, rename: bool = False,
                  new_name: str = None) -> bool:
        """
        Копирует файл из source в dest
        
        Args:
            source: Исходный путь
            dest: Путь назначения
            rename: Нужно ли переименовывать
            new_name: Новое имя файла (если rename=True)
            
        Returns:
            True если успешно, False если файл не найден
        """
        if not source.exists():
            self.missing_files.append(str(source))
            if self.logger:
                self.logger.warning(f"Файл не найден: {source.name}")
            return False
        
        # Создаем папку назначения
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Определяем имя файла
        if rename and new_name:
            dest_file = dest.parent / new_name
        else:
            dest_file = dest
        
        # Копируем
        try:
            shutil.copy2(source, dest_file)
            if self.logger:
                self.logger.debug(f"Скопирован: {source.name} -> {dest_file.name}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка копирования {source.name}: {e}")
            return False
    
    def copy_dxf_with_rename(self, source: pathlib.Path, dest_dir: pathlib.Path,
                              detail_name: str, material: str, quantity: int) -> Optional[pathlib.Path]:
        """
        Копирует DXF файл с переименованием по шаблону
        
        Args:
            source: Исходный DXF файл
            dest_dir: Папка назначения
            detail_name: Наименование детали
            material: Материал
            quantity: Количество
            
        Returns:
            Путь к скопированному файлу или None при ошибке
        """
        from utils.file_utils import sanitize_filename
        
        if not source.exists():
            self.missing_files.append(str(source))
            return None
        
        new_name = f"{sanitize_filename(detail_name)}_{material}_{quantity}шт.dxf"
        dest_file = dest_dir / new_name
        
        try:
            shutil.copy2(source, dest_file)
            if self.logger:
                self.logger.debug(f"Скопирован DXF: {new_name}")
            return dest_file
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка копирования DXF: {e}")
            return None
    
    def copy_pdf_stp(self, source: pathlib.Path, dest_dir: pathlib.Path,
                     detail_name: str, material: str, quantity: int, ext: str) -> bool:
        """
        Копирует PDF или STP файл с переименованием
        
        Args:
            source: Исходный файл
            dest_dir: Папка назначения
            detail_name: Наименование детали
            material: Материал
            quantity: Количество
            ext: Расширение файла (.pdf или .stp)
            
        Returns:
            True при успехе
        """
        from utils.file_utils import sanitize_filename
        
        if not source.exists():
            self.missing_files.append(str(source))
            return False
        
        new_name = f"{sanitize_filename(detail_name)}_{material}_{quantity}шт{ext}"
        dest_file = dest_dir / new_name
        
        try:
            shutil.copy2(source, dest_file)
            if self.logger:
                self.logger.debug(f"Скопирован {ext}: {new_name}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка копирования {ext}: {e}")
            return False
    
    def create_directory(self, path: pathlib.Path) -> pathlib.Path:
        """Создает директорию"""
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_missing_files(self) -> List[str]:
        """Возвращает список отсутствующих файлов"""
        return self.missing_files
    
    def clear_missing_files(self):
        """Очищает список отсутствующих файлов"""
        self.missing_files = []