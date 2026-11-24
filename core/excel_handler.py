"""
Обработка Excel файлов
"""

import pandas as pd
import pathlib
from typing import Dict, List, Tuple, Any


class ExcelHandler:
    """
    Класс для работы с Excel файлами
    """
    
    def __init__(self, material_dict: dict, logger=None):
        """
        Args:
            material_dict: Словарь замены материалов
            logger: Объект логгера
        """
        self.material_dict = material_dict
        self.logger = logger
    
    def replace_materials(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Заменяет материалы в DataFrame по словарю
        """
        if 'Материал' in df.columns:
            df['Материал'] = df['Материал'].apply(
                lambda x: self.material_dict.get(x, x) if pd.notna(x) else x
            )
            if self.logger:
                self.logger.info("Выполнена замена материалов")
        return df
    
    def group_by_category(self, df: pd.DataFrame) -> Dict[str, List[Tuple[int, Any]]]:
        """
        Группирует строки DataFrame по категориям
        """
        categories = {}
        
        for idx, row in df.iterrows():
            category = row.get('Категория', '!Без категории')
            if pd.isna(category) or category == "":
                category = "!Без категории"
            
            if category not in categories:
                categories[category] = []
            categories[category].append((idx, row))
        
        if self.logger:
            self.logger.info(f"Найдено категорий: {len(categories)}")
        
        return categories
    
    def find_powder_parts(self, df: pd.DataFrame) -> List[Tuple[int, Any]]:
        """
        Находит детали с порошковой покраской
        """
        powder_parts = []
        
        for idx, row in df.iterrows():
            comment = row.get('Комментарий', '')
            if pd.notna(comment) and isinstance(comment, str):
                if 'порошковая' in comment.lower():
                    powder_parts.append((idx, row))
                    if self.logger:
                        self.logger.info(f"Найдена порошковая: {row.get('Обозначение', 'Unknown')}")
        
        return powder_parts
    
    def save_category_excel(self, rows: List[Tuple[int, Any]], output_path: pathlib.Path,
                            category_name: str) -> pd.DataFrame:
        """
        Сохраняет категорию в отдельный Excel файл и возвращает DataFrame
        
        Returns:
            DataFrame с данными категории
        """
        from utils.file_utils import sanitize_filename
        
        # Создаем DataFrame из строк
        category_rows = [row for _, row in rows]
        category_df = pd.DataFrame(category_rows)
        
        # Удаляем ненужные колонки
        for col in ['Поз.', 'Категория']:
            if col in category_df.columns:
                category_df = category_df.drop(columns=[col])
                # Гарантируем наличие колонки ХЭШ во всех финальных Excel
        if 'ХЭШ' not in category_df.columns:
            category_df['ХЭШ'] = ''
            
        # Сохраняем
        safe_name = sanitize_filename(category_name)
        excel_file = output_path / f"spec_{safe_name}.xlsx"
        category_df.to_excel(excel_file, index=False)
        
        if self.logger:
            self.logger.info(f"Сохранен Excel: {excel_file.name}")
        
        return category_df  # Возвращаем DataFrame
    
    def update_excel_with_hash(self, file_path: pathlib.Path, row_index: int, 
                                dxf_hash: str, circles: str, width: float, height: float):
        """
        Обновляет Excel файл с данными из DXF
        """
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
            
            if 'ХЭШ' in df.columns:
                df.at[row_index, 'ХЭШ'] = dxf_hash
            if 'Отверстия' in df.columns:
                df.at[row_index, 'Отверстия'] = circles
            if 'Длина развертки' in df.columns:
                df.at[row_index, 'Длина развертки'] = width
            if 'Ширина Развертки' in df.columns:
                df.at[row_index, 'Ширина Развертки'] = height
            
            df.to_excel(file_path, index=False)
            
            if self.logger:
                self.logger.debug(f"Обновлен Excel: {file_path.name}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка обновления Excel: {e}")
    
    def read_excel(self, path: pathlib.Path) -> pd.DataFrame:
        """Читает Excel файл"""
        try:
            df = pd.read_excel(path, engine='openpyxl')
            if self.logger:
                self.logger.info(f"Загружено строк: {len(df)}")
            return df
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка чтения Excel {path.name}: {e}")
            raise
    
    def get_quantity(self, row) -> int:
        """Получает количество из строки"""
        quantity = row.get('Количество', row.get('Кол.', 1))
        if pd.isna(quantity):
            return 1
        return int(quantity)
    
    def get_detail_length(self, row, df: pd.DataFrame) -> float:
        """Получает длину детали из Excel (для профиля)"""
        if 'Длина' in df.columns:
            length = row.get('Длина', 0)
            if pd.notna(length) and length > 0:
                return float(length)
        return 0