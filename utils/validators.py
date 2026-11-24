"""
Валидаторы для проверки данных
"""

import pathlib
import pandas as pd
from typing import Tuple, List, Optional


class Validator:
    """
    Класс для проверки данных
    """
    
    @staticmethod
    def validate_file_exists(file_path: pathlib.Path) -> bool:
        """
        Проверяет существование файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если файл существует
        """
        return file_path.exists() and file_path.is_file()
    
    @staticmethod
    def validate_directory_exists(dir_path: pathlib.Path) -> bool:
        """
        Проверяет существование директории
        
        Args:
            dir_path: Путь к директории
            
        Returns:
            True если директория существует
        """
        return dir_path.exists() and dir_path.is_dir()
    
    @staticmethod
    def validate_excel_columns(df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, List[str]]:
        """
        Проверяет наличие обязательных колонок в Excel
        
        Args:
            df: DataFrame
            required_columns: Список обязательных колонок
            
        Returns:
            (все_ли_колонки_есть, список_отсутствующих)
        """
        missing = [col for col in required_columns if col not in df.columns]
        return len(missing) == 0, missing
    
    @staticmethod
    def validate_positive_number(value, default: float = 0) -> float:
        """
        Проверяет, что число положительное
        
        Args:
            value: Проверяемое значение
            default: Значение по умолчанию
            
        Returns:
            Положительное число или значение по умолчанию
        """
        try:
            num = float(value)
            return num if num > 0 else default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def validate_sheet_size(size_str: str) -> Tuple[int, int]:
        """
        Проверяет и парсит размер листа формата "ШиринаxВысота"
        
        Args:
            size_str: Строка с размерами
            
        Returns:
            Кортеж (ширина, высота)
        """
        try:
            width, height = map(int, size_str.lower().split('x'))
            if width > 0 and height > 0:
                return width, height
        except:
            pass
        return 1250, 2500  # Значение по умолчанию
    
    @staticmethod
    def validate_material_name(material: str, max_length: int = 100) -> str:
        """
        Валидирует имя материала
        
        Args:
            material: Имя материала
            max_length: Максимальная длина
            
        Returns:
            Очищенное имя материала
        """
        if not material or pd.isna(material):
            return "неизвестный_материал"
        
        # Удаляем запрещенные символы
        import re
        material = str(material)
        material = re.sub(r'[\\/*?:"<>|]', '_', material)
        material = material.strip()
        
        # Ограничиваем длину
        if len(material) > max_length:
            material = material[:max_length]
        
        return material
    
    @staticmethod
    def validate_dimensions(width: float, height: float) -> Tuple[float, float]:
        """
        Валидирует габариты детали
        
        Args:
            width: Ширина
            height: Высота
            
        Returns:
            Кортеж (ширина, высота) с гарантированно положительными значениями
        """
        width = float(width) if width > 0 else 0
        height = float(height) if height > 0 else 0
        return width, height


class ExcelValidator:
    """
    Валидатор для Excel файлов
    """
    
    REQUIRED_COLUMNS = ['Обозначение', 'Количество', 'Материал', 'Категория']
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def validate_excel_file(self, file_path: pathlib.Path) -> Tuple[bool, List[str]]:
        """
        Полная проверка Excel файла
        
        Args:
            file_path: Путь к Excel файлу
            
        Returns:
            (валиден_ли, список_ошибок)
        """
        errors = []
        
        # Проверяем существование
        if not Validator.validate_file_exists(file_path):
            errors.append(f"Файл не найден: {file_path}")
            return False, errors
        
        # Проверяем расширение
        if file_path.suffix.lower() not in ['.xls', '.xlsx']:
            errors.append(f"Неверный формат файла: {file_path.suffix}")
            return False, errors
        
        try:
            # Читаем Excel
            df = pd.read_excel(file_path, engine='openpyxl', nrows=1)
            
            # Проверяем колонки
            has_all, missing = Validator.validate_excel_columns(df, self.REQUIRED_COLUMNS)
            if not has_all:
                errors.append(f"Отсутствуют колонки: {', '.join(missing)}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Ошибка чтения Excel: {e}")
            return False, errors
    
    def validate_row(self, row: pd.Series) -> Tuple[bool, List[str]]:
        """
        Проверяет одну строку данных
        
        Args:
            row: Строка DataFrame
            
        Returns:
            (валидна_ли, список_ошибок)
        """
        errors = []
        
        # Проверяем обозначение
        detail_name = row.get('Обозначение', '')
        if pd.isna(detail_name) or str(detail_name).strip() == '':
            errors.append("Пустое обозначение детали")
        
        # Проверяем количество
        quantity = row.get('Количество', row.get('Кол.', 1))
        if pd.isna(quantity) or float(quantity) <= 0:
            errors.append("Некорректное количество")
        
        # Проверяем материал
        material = row.get('Материал', '')
        if pd.isna(material) or str(material).strip() == '':
            errors.append("Пустой материал")
        
        return len(errors) == 0, errors


class FileStructureValidator:
    """
    Валидатор структуры файлов
    """
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def validate_file_structure(self, excel_dir: pathlib.Path, 
                                detail_name: str) -> Tuple[bool, dict]:
        """
        Проверяет наличие всех файлов для детали
        
        Args:
            excel_dir: Директория с файлами
            detail_name: Наименование детали
            
        Returns:
            (все_ли_файлы_есть, словарь_с_результатами)
        """
        result = {
            'dxf': False,
            'pdf': False,
            'stp': False,
            'missing': []
        }
        
        dxf_file = excel_dir / f"{detail_name}.dxf"
        pdf_file = excel_dir / f"{detail_name}.pdf"
        stp_file = excel_dir / f"{detail_name}.stp"
        
        if dxf_file.exists():
            result['dxf'] = True
        else:
            result['missing'].append(f"{detail_name}.dxf")
        
        if pdf_file.exists():
            result['pdf'] = True
        else:
            result['missing'].append(f"{detail_name}.pdf")
        
        if stp_file.exists():
            result['stp'] = True
        else:
            result['missing'].append(f"{detail_name}.stp")
        
        all_exist = result['dxf']  # DXF обязателен, остальные опциональны
        
        return all_exist, result