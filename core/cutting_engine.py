"""
Расчет раскроя материалов
"""

from collections import defaultdict
from typing import Dict, List, Any, Tuple
import pathlib


class CuttingEngine:
    """
    Класс для сбора данных о деталях и расчета раскроя
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        # Данные для линейных материалов (профиль, шины)
        self.linear_data = {
            'profile': defaultdict(list),
            'busbar': defaultdict(list)
        }
        # Данные для листовых материалов (лазер, пуансон, резка)
        # Формат: {категория_материал: [(ширина, длина), (ширина, длина), ...]}
        # Например: 'punch_оц_1.5мм', 'laser_оц_2.0мм'
        self.sheet_data = defaultdict(list)
        
        self.output_dir = None
        self.cutting_params = {}
    
    def set_output_dir(self, output_dir: pathlib.Path):
        """Устанавливает папку для сохранения изображений раскладки"""
        self.output_dir = output_dir
    
    def set_params(self, params: dict):
        """Устанавливает параметры раскроя"""
        self.cutting_params = params
    
    def add_sheet_part(self, category: str, material: str, name: str, quantity: int, width: float, length: float):
        """
        Добавляет листовую деталь для расчета раскроя
        Теперь храним кортеж (ширина, длина, имя)
        """
        if width <= 0 or length <= 0:
            if self.logger:
                self.logger.warning(f"  ⚠️ Пропущена деталь {name}: некорректные размеры ({width:.1f}x{length:.1f})")
            return
        
        # Создаем ключ: категория_материал
        key = f"{category}_{material}"
        
        # Разворачиваем каждую деталь отдельно, храним (ширина, длина, имя)
        for _ in range(quantity):
            self.sheet_data[key].append((width, length, name))
        
        if self.logger:
            self.logger.debug(f"  📏 Добавлена деталь: {name} ({width:.1f}x{length:.1f} мм) x {quantity} шт -> развернуто в {quantity} шт, ключ={key}")

    def add_linear_part(self, category: str, material: str, name: str, quantity: int, length: float):
        """
        Добавляет линейную деталь (профиль, шина)
        """
        if length <= 0:
            if self.logger:
                self.logger.warning(f"  ⚠️ Пропущена деталь {name}: длина = {length}")
            return
        
        cat_lower = category.lower()
        if cat_lower not in self.linear_data:
            return
        
        part = {
            'name': name,
            'quantity': quantity,
            'length': length,
            'material': material
        }
        self.linear_data[cat_lower][material].append(part)
    
    def clear(self):
        """Очищает все данные"""
        self.linear_data = {
            'profile': defaultdict(list),
            'busbar': defaultdict(list)
        }
        self.sheet_data = defaultdict(list)
    
    def get_sheet_data(self) -> Dict[str, List[Tuple[float, float, str]]]:
        """Возвращает данные листовых деталей: {категория_материал: [(ширина, длина, имя), ...]}"""
        return dict(self.sheet_data)
    
    def get_linear_data(self) -> Dict:
        """Возвращает данные линейных деталей"""
        return dict(self.linear_data)
    
    def has_data(self) -> bool:
        """Проверяет, есть ли данные для расчета"""
        return bool(self.sheet_data) or any(bool(v) for v in self.linear_data.values())
    
    
    def print_sheet_data_summary(self):
        """Выводит сводку по листовым материалам (для отладки)"""
        if not self.logger:
            return
        
        self.logger.info("\n" + "="*60)
        self.logger.info("СБОР ДАННЫХ ПО ЛИСТОВЫМ МАТЕРИАЛАМ (по категориям)")
        self.logger.info("="*60)
        
        if not self.sheet_data:
            self.logger.info("  Нет данных")
            return
        
        for key, items in self.sheet_data.items():
            self.logger.info(f"\n  📦 {key}:")
            self.logger.info(f"     Всего деталей: {len(items)} шт")
            
            # Считаем уникальные размеры
            from collections import Counter
            rectangles = [(w, h) for w, h, name in items]
            size_counter = Counter(rectangles)
            self.logger.info(f"     Уникальных размеров: {len(size_counter)}")
            for (w, h), count in sorted(size_counter.items(), key=lambda x: -x[1])[:5]:
                # Показываем пример имени
                example_name = next(name for w2, h2, name in items if w2 == w and h2 == h)
                self.logger.info(f"       {w:.1f}x{h:.1f} мм ({example_name}): {count} шт")
            if len(size_counter) > 5:
                self.logger.info(f"       ... и еще {len(size_counter) - 5} типов")
        
        self.logger.info("="*60)