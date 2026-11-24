"""
Модуль для сбора данных раскроя и копирования файлов
"""

from collections import defaultdict
import pathlib
import shutil
import re
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional


class CuttingDataCollector:
    """Сборщик данных для раскроя"""
    
    def __init__(self):
        self.data = {
            'profile': defaultdict(list),
            'busbar': defaultdict(list),
            'laser': defaultdict(list),
            'punch': defaultdict(list),
            'cutting': defaultdict(list)
        }
    
    def add_profile(self, material: str, name: str, quantity: int, length: float):
        """Добавляет профиль в данные раскроя"""
        self.data['profile'][material].append({
            'name': name,
            'quantity': quantity,
            'length': length
        })
    
    def add_busbar(self, material: str, name: str, quantity: int, length: float):
        """Добавляет шину в данные раскроя"""
        self.data['busbar'][material].append({
            'name': name,
            'quantity': quantity,
            'length': length
        })
    
    def add_sheet(self, category: str, material: str, name: str, quantity: int, 
                  length: float, width: float):
        """Добавляет листовой материал в данные раскроя"""
        if category in self.data:
            self.data[category][material].append({
                'name': name,
                'quantity': quantity,
                'length': length,
                'width': width
            })
    
    def get_data(self) -> dict:
        """Возвращает все собранные данные"""
        return dict(self.data)
    
    def has_data(self) -> bool:
        """Проверяет, есть ли данные"""
        return any(v for v in self.data.values())
    
    def log_summary(self, logger) -> None:
        """Выводит краткую сводку в лог"""
        logger.info("\n🔍 ИТОГОВЫЕ ДАННЫЕ ДЛЯ ОТЧЕТА:")
        for cat, mats in self.data.items():
            if mats:
                total_parts = sum(len(v) for v in mats.values())
                logger.info(f"  {cat}: {total_parts} деталей")
                for mat, parts in mats.items():
                    logger.info(f"    {mat}: {len(parts)} шт")
            else:
                logger.info(f"  {cat}: нет данных")


class FileFinder:
    """Поиск файлов с любым регистром расширения"""
    
    def __init__(self, base_dir: pathlib.Path, logger=None):
        self.base_dir = base_dir
        self.logger = logger
    
    def find(self, name: str, ext: str) -> Optional[pathlib.Path]:
        """Ищет файл, игнорируя регистр расширения"""
        if not name or pd.isna(name):
            return None
        
        if self.logger:
            self.logger.debug(f"    Поиск файла: {name}{ext}")
        
        # Пробуем с нижним регистром
        file_path = self.base_dir / f"{name}{ext.lower()}"
        if self.logger:
            self.logger.debug(f"      Проверка: {file_path} -> {file_path.exists()}")
        if file_path.exists():
            return file_path
        
        # Пробуем с верхним регистром
        file_path = self.base_dir / f"{name}{ext.upper()}"
        if self.logger:
            self.logger.debug(f"      Проверка: {file_path} -> {file_path.exists()}")
        if file_path.exists():
            return file_path
        
        # Ищем через glob
        try:
            pattern = f"{re.escape(str(name))}.*"
            for f in self.base_dir.glob(pattern):
                if self.logger:
                    self.logger.debug(f"      Найдено по glob: {f.name}")
                if f.suffix.lower() == ext.lower():
                    if self.logger:
                        self.logger.debug(f"      Совпадает по расширению: {f.name}")
                    return f
        except Exception as e:
            if self.logger:
                self.logger.debug(f"      Ошибка glob: {e}")
        
        if self.logger:
            self.logger.debug(f"    Файл не найден: {name}{ext}")
        return None


class FileCopier:
    """Копирование файлов с переименованием"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.missing_files = []
    
    def sanitize_filename(self, name: str) -> str:
        """Очищает имя файла от запрещенных символов, заменяя их на $"""
        if not name or pd.isna(name):
            return "unknown"
        
        result = str(name)
        # Заменяем все запрещенные символы на $
        forbidden_chars = r'[\\/*?:"<>|]'
        result = re.sub(forbidden_chars, '$', result)
        # Дополнительная замена слешей
        result = result.replace('/', '$').replace('\\', '$')
        # Удаляем пробелы в начале и конце
        result = result.strip()
        # Ограничиваем длину
        if len(result) > 200:
            result = result[:200]
        if not result or result.strip() == "":
            result = "unknown"
        return result
    
    def add_missing(self, file_path: str):
        """Добавляет файл в список отсутствующих"""
        self.missing_files.append(file_path)
    
    def get_missing(self) -> list:
        """Возвращает список отсутствующих файлов"""
        return self.missing_files
    
    def copy_file(self, source: pathlib.Path, dest_dir: pathlib.Path, 
                  filename: str = None) -> bool:
        """Копирует файл в папку назначения"""
        if not source or not source.exists():
            return False
        
        # Создаем папку назначения
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            if self.logger:
                self.logger.error(f"  ❌ Не удалось создать папку {dest_dir}: {e}")
            return False
        
        if filename:
            dest_file = dest_dir / filename
        else:
            dest_file = dest_dir / source.name
        
        if dest_file.exists():
            if self.logger:
                self.logger.debug(f"  Файл уже существует: {dest_file.name}")
            return True
        
        try:
            shutil.copy2(source, dest_file)
            if self.logger:
                self.logger.info(f"  ✅ Копирован: {dest_file.name}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"  ❌ Ошибка копирования: {e}")
            return False
    
    def copy_with_rename(self, source: pathlib.Path, dest_dir: pathlib.Path,
                         detail_name: str, material: str, quantity: int, ext: str) -> bool:
        """Копирует файл с переименованием по шаблону"""
        clean_detail = self.sanitize_filename(detail_name)
        clean_material = self.sanitize_filename(material)
        new_name = f"{clean_detail}_{clean_material}_{quantity}шт{ext}"
        
        if self.logger:
            self.logger.debug(f"  Новое имя: {new_name}")
        
        return self.copy_file(source, dest_dir, new_name)


class RowProcessor:
    """Обработчик строк Excel"""
    
    def __init__(self, logger, material_dict: dict, dxf_processor, 
                 file_finder: FileFinder, file_copier: FileCopier,
                 cutting_data: CuttingDataCollector):
        self.logger = logger
        self.material_dict = material_dict
        self.dxf_processor = dxf_processor
        self.file_finder = file_finder
        self.file_copier = file_copier
        self.cutting_data = cutting_data
    
    def process_busbar(self, detail_name: str, material: str, quantity: int,
                       category_dir: pathlib.Path, rename: bool,
                       category_df: pd.DataFrame = None, idx: int = None) -> Optional[dict]:
        """Обрабатывает шину"""
        self.logger.info(f"  🚌 Обработка ШИНЫ: {detail_name}")
        
        dxf_file = self.file_finder.find(detail_name, '.dxf')
        if not dxf_file:
            self.file_copier.add_missing(f"{detail_name}.dxf")
            self.logger.error(f"  ❌ ШИНА {detail_name}: нет DXF файла")
            return None
        
        # Копируем DXF
        if rename:
            self.file_copier.copy_with_rename(dxf_file, category_dir, detail_name, material, quantity, '.dxf')
            self.logger.info(f"  ✅ Копирован DXF")
        else:
            self.file_copier.copy_file(dxf_file, category_dir)
        
        # Обрабатываем DXF
        dxf_data = self.dxf_processor.process_dxf(dxf_file)
        if dxf_data:
            length_val = dxf_data['length']
            if length_val > 0:
                self.cutting_data.add_busbar(material, detail_name, quantity, length_val)
                self.logger.info(f"  ✅ ШИНА: {detail_name} длина={length_val:.0f} мм x {quantity} шт")
            else:
                self.logger.warning(f"  ⚠️ ШИНА {detail_name}: длина = 0")
        
        # Копируем PDF и STP
        for ext in ['.pdf', '.stp']:
            file_path = self.file_finder.find(detail_name, ext)
            if file_path:
                if rename:
                    self.file_copier.copy_with_rename(file_path, category_dir, detail_name, material, quantity, ext)
                    self.logger.info(f"  ✅ Копирован {ext.upper()}")
                else:
                    self.file_copier.copy_file(file_path, category_dir)
            else:
                self.logger.warning(f"  ⚠️ ШИНА {detail_name}: нет файла {ext.upper()}")
        
        return dxf_data
    
    def process_profile_no_busbar(self, detail_name: str, material: str, quantity: int,
                                   length_val: float, category_dir: pathlib.Path,
                                   rename: bool) -> None:
        """Обрабатывает профиль (не шину) - копирует только PDF и STP"""
        self.logger.info(f"  📏 Обработка ПРОФИЛЯ: {detail_name}")
        
        # Копируем только PDF и STP (DXF не копируем)
        for ext in ['.pdf', '.stp']:
            file_path = self.file_finder.find(detail_name, ext)
            if file_path:
                if rename:
                    success = self.file_copier.copy_with_rename(file_path, category_dir, detail_name, material, quantity, ext)
                    if success:
                        self.logger.info(f"  ✅ ПРОФИЛЬ: скопирован {ext.upper()}")
                    else:
                        self.logger.error(f"  ❌ ПРОФИЛЬ {detail_name}: ошибка копирования {ext.upper()}")
                else:
                    success = self.file_copier.copy_file(file_path, category_dir)
                    if success:
                        self.logger.info(f"  ✅ ПРОФИЛЬ: скопирован {ext.upper()}")
                    else:
                        self.logger.error(f"  ❌ ПРОФИЛЬ {detail_name}: ошибка копирования {ext.upper()}")
            else:
                self.file_copier.add_missing(f"{detail_name}{ext}")
                self.logger.warning(f"  ⚠️ ПРОФИЛЬ {detail_name}: нет файла {ext.upper()}")
        
        # Добавляем в раскрой
        if length_val > 0:
            self.cutting_data.add_profile(material, detail_name, quantity, length_val)
            self.logger.info(f"  ✅ ПРОФИЛЬ: {detail_name} длина={length_val:.0f} мм x {quantity} шт")
        else:
            self.logger.warning(f"  ⚠️ ПРОФИЛЬ {detail_name}: длина = 0")
    
    def process_sheet_material(self, category: str, detail_name: str, material: str,
                                quantity: int, category_dir: pathlib.Path,
                                rename: bool, category_df: pd.DataFrame = None, idx: int = None) -> Optional[dict]:
        """Обрабатывает листовой материал (laser, punch, cutting)"""
        self.logger.info(f"  🛠️ Обработка {category}: {detail_name}")
        
        dxf_file = self.file_finder.find(detail_name, '.dxf')
        if not dxf_file:
            self.file_copier.add_missing(f"{detail_name}.dxf")
            self.logger.error(f"  ❌ {category} {detail_name}: нет DXF файла")
            return None
        
        # Копируем DXF
        if rename:
            self.file_copier.copy_with_rename(dxf_file, category_dir, detail_name, material, quantity, '.dxf')
            self.logger.info(f"  ✅ Копирован DXF")
        else:
            self.file_copier.copy_file(dxf_file, category_dir)
        
        # Обрабатываем DXF
        dxf_data = self.dxf_processor.process_dxf(dxf_file)
        if dxf_data and dxf_data['width'] > 0 and dxf_data['height'] > 0:
            self.cutting_data.add_sheet(category, material, detail_name, quantity,
                                       dxf_data['width'], dxf_data['height'])
            self.logger.info(f"  ✅ {category}: {detail_name} {dxf_data['width']:.0f}x{dxf_data['height']:.0f} мм x {quantity} шт")
        
        # Копируем PDF и STP
        for ext in ['.pdf', '.stp']:
            file_path = self.file_finder.find(detail_name, ext)
            if file_path:
                if rename:
                    self.file_copier.copy_with_rename(file_path, category_dir, detail_name, material, quantity, ext)
                    self.logger.info(f"  ✅ Копирован {ext.upper()}")
                else:
                    self.file_copier.copy_file(file_path, category_dir)
            else:
                self.logger.warning(f"  ⚠️ {category} {detail_name}: нет файла {ext.upper()}")
        
        return dxf_data
    
    def process_other_category(self, category: str, detail_name: str, material: str,
                                quantity: int, category_dir: pathlib.Path,
                                rename: bool, category_df: pd.DataFrame = None, idx: int = None) -> Optional[dict]:
        """Обрабатывает остальные категории (включая порошковую покраску) - копирует все файлы"""
        self.logger.info(f"  📁 Обработка {category}: {detail_name}")
        
        dxf_file = self.file_finder.find(detail_name, '.dxf')
        if not dxf_file:
            self.file_copier.add_missing(f"{detail_name}.dxf")
            self.logger.warning(f"  ⚠️ {category} {detail_name}: нет DXF")
            return None
        
        # Копируем DXF
        if rename:
            self.file_copier.copy_with_rename(dxf_file, category_dir, detail_name, material, quantity, '.dxf')
            self.logger.info(f"  ✅ Копирован DXF")
        else:
            self.file_copier.copy_file(dxf_file, category_dir)
        
        # Копируем PDF и STP
        for ext in ['.pdf', '.stp']:
            file_path = self.file_finder.find(detail_name, ext)
            if file_path:
                if rename:
                    self.file_copier.copy_with_rename(file_path, category_dir, detail_name, material, quantity, ext)
                    self.logger.info(f"  ✅ Копирован {ext.upper()}")
                else:
                    self.file_copier.copy_file(file_path, category_dir)
            else:
                self.logger.warning(f"  ⚠️ {category} {detail_name}: нет файла {ext.upper()}")
        
        # Обрабатываем DXF для получения данных
        dxf_data = self.dxf_processor.process_dxf(dxf_file)
        return dxf_data