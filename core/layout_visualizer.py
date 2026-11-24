"""
Визуализация раскладки деталей на листах
"""

import pathlib
from typing import List, Dict, Any, Optional

# Проверяем наличие matplotlib
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib не установлен, визуализация недоступна")


class LayoutVisualizer:
    """Класс для визуализации раскладки деталей"""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def save_layout_image(self, solution, sheet_width: float, sheet_height: float,
                          output_dir: pathlib.Path, material: str = "") -> List[str]:
        """
        Сохраняет изображения раскладки для всех листов
        
        Args:
            solution: Объект решения от pyckingsolver
            sheet_width: Ширина листа (мм)
            sheet_height: Высота листа (мм)
            output_dir: Папка для сохранения
            material: Название материала
            
        Returns:
            Список путей к сохраненным изображениям
        """
        if not MATPLOTLIB_AVAILABLE:
            if self.logger:
                self.logger.warning("matplotlib не установлен, визуализация недоступна")
            return []
        
        layout_images = []
        
        # Получаем список листов из решения
        sheets = self._extract_sheets_from_solution(solution)
        
        if not sheets:
            if self.logger:
                self.logger.warning("Не удалось извлечь данные о листах из решения")
            return []
        
        if self.logger:
            self.logger.info(f"     Визуализация {len(sheets)} листов для материала {material}")
        
        for sheet_idx, sheet_parts in enumerate(sheets):
            try:
                img_path = self._draw_single_sheet(
                    sheet_parts, sheet_width, sheet_height, 
                    output_dir, material, sheet_idx + 1
                )
                if img_path:
                    layout_images.append(img_path)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Ошибка визуализации листа {sheet_idx + 1}: {e}")
        
        return layout_images
    
    def _extract_sheets_from_solution(self, solution) -> List[List[Dict]]:
        """
        Извлекает список листов с деталями из решения pyckingsolver
        
        Пробует разные способы получения данных, так как API может отличаться
        """
        sheets = []
        
        # Способ 1: solution.bins
        if hasattr(solution, 'bins') and solution.bins is not None:
            try:
                for bin_item in solution.bins:
                    sheet_parts = []
                    # Проверяем, является ли bin_item итерируемым
                    if hasattr(bin_item, '__iter__'):
                        for item in bin_item:
                            part_info = self._extract_part_info(item)
                            if part_info:
                                sheet_parts.append(part_info)
                    sheets.append(sheet_parts)
                if sheets:
                    if self.logger:
                        self.logger.debug(f"Извлечено {len(sheets)} листов через solution.bins")
                    return sheets
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Ошибка при доступе к solution.bins: {e}")
        
        # Способ 2: solution.get_bins() или solution.bins_list
        if hasattr(solution, 'get_bins'):
            try:
                bins = solution.get_bins()
                for bin_item in bins:
                    sheet_parts = []
                    for item in bin_item:
                        part_info = self._extract_part_info(item)
                        if part_info:
                            sheet_parts.append(part_info)
                    sheets.append(sheet_parts)
                if sheets:
                    return sheets
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Ошибка при вызове get_bins(): {e}")
        
        # Способ 3: solution.items (все детали с bin_index)
        if hasattr(solution, 'items') or hasattr(solution, 'all_items'):
            items = solution.items if hasattr(solution, 'items') else solution.all_items
            if items:
                # Группируем по bin_index
                bins_dict = {}
                for item in items:
                    bin_idx = getattr(item, 'bin_index', getattr(item, 'bin', 0))
                    if bin_idx not in bins_dict:
                        bins_dict[bin_idx] = []
                    part_info = self._extract_part_info(item)
                    if part_info:
                        bins_dict[bin_idx].append(part_info)
                
                # Преобразуем в список
                for bin_idx in sorted(bins_dict.keys()):
                    sheets.append(bins_dict[bin_idx])
                
                if sheets:
                    if self.logger:
                        self.logger.debug(f"Извлечено {len(sheets)} листов через items")
                    return sheets
        
        if self.logger:
            self.logger.warning("Не удалось извлечь данные о листах из решения")
        
        return sheets
    
    def _extract_part_info(self, item) -> Optional[Dict]:
        """
        Извлекает информацию о детали из объекта item
        """
        try:
            # Получаем координаты и размеры
            x = getattr(item, 'x', 0)
            y = getattr(item, 'y', 0)
            width = getattr(item, 'width', getattr(item, 'w', 0))
            height = getattr(item, 'height', getattr(item, 'h', 0))
            
            # Получаем имя/индекс детали
            name = str(getattr(item, 'original_index', getattr(item, 'id', '?')))
            
            # Получаем угол поворота
            rotation = getattr(item, 'rotation', 0)
            
            if width > 0 and height > 0:
                return {
                    'x': float(x),
                    'y': float(y),
                    'width': float(width),
                    'height': float(height),
                    'name': name,
                    'rotation': rotation
                }
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Ошибка извлечения информации о детали: {e}")
        
        return None
    
    def _draw_single_sheet(self, parts: List[Dict], sheet_width: float, sheet_height: float,
                           output_dir: pathlib.Path, material: str, sheet_num: int) -> Optional[str]:
        """
        Рисует один лист с размещенными деталями
        """
        try:
            fig, ax = plt.subplots(1, 1, figsize=(14, 10))
            
            # Рисуем границы листа
            sheet_rect = patches.Rectangle((0, 0), sheet_width, sheet_height,
                                           linewidth=2, edgecolor='black',
                                           facecolor='none', linestyle='--')
            ax.add_patch(sheet_rect)
            
            colors = plt.cm.tab20.colors
            
            for i, part in enumerate(parts):
                x = part['x']
                y = part['y']
                w = part['width']
                h = part['height']
                name = part['name']
                color = colors[i % len(colors)]
                
                # Рисуем деталь
                rect = patches.Rectangle((x, y), w, h,
                                         linewidth=1, edgecolor='blue',
                                         facecolor=color, alpha=0.7)
                ax.add_patch(rect)
                
                # Добавляем отметку о повороте
                if part.get('rotation', 0) != 0:
                    ax.text(x + 5, y + 15, '↻', fontsize=10, fontweight='bold',
                           bbox=dict(boxstyle='circle', facecolor='yellow', alpha=0.8))
                
                # Подпись детали
                center_x = x + w / 2
                center_y = y + h / 2
                ax.text(center_x, center_y, name,
                       ha='center', va='center', fontsize=8, fontweight='bold')
            
            # Настройки графика
            ax.set_xlim(-50, sheet_width + 50)
            ax.set_ylim(-50, sheet_height + 50)
            ax.set_xlabel('Ширина (мм)', fontsize=12)
            ax.set_ylabel('Высота (мм)', fontsize=12)
            ax.set_title(f'Раскладка листа #{sheet_num}\n'
                        f'Размер: {sheet_width:.0f}x{sheet_height:.0f} мм\n'
                        f'Материал: {material}\n'
                        f'Всего деталей: {len(parts)} шт.',
                        fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_aspect('equal')
            
            # Информация в углу
            info_text = f"Деталей: {len(parts)}"
            ax.text(sheet_width - 10, sheet_height - 20, info_text,
                   fontsize=9, ha='right', va='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Сохраняем
            safe_material = material.replace('/', '_').replace('\\', '_').replace(' ', '_')
            output_path = output_dir / f"cutting_layout_{safe_material}_{sheet_num}.png"
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            if self.logger:
                self.logger.info(f"📊 Изображение раскладки сохранено: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка рисования листа {sheet_num}: {e}")
            return None