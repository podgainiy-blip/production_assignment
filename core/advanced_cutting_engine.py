"""
Расчет раскроя с использованием pyckingsolver
"""

from typing import List, Dict, Tuple, Optional, Any
import pathlib
from collections import defaultdict

# Пробуем импортировать pyckingsolver
PYCKING_AVAILABLE = False
try:
    from pyckingsolver import nest, Objective
    from shapely.geometry import box
    PYCKING_AVAILABLE = True
    print("✅ pyckingsolver успешно загружен")
except ImportError as e:
    print(f"⚠️ pyckingsolver не загружен: {e}")


class AdvancedCuttingEngine:
    """Класс для расчета раскроя с использованием pyckingsolver"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.cutting_params = {}
        self._current_sheet_width = 1250
        self._current_sheet_height = 2500
    
    def set_params(self, params: dict):
        self.cutting_params = params
    
    def group_parts_by_material(self, parts: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Группирует детали по материалу
        
        Args:
            parts: Список деталей с полями name, width, length, quantity, material
            
        Returns:
            {material: [список деталей этого материала]}
        """
        grouped = defaultdict(list)
        
        for part in parts:
            material = part.get('material', 'unknown')
            grouped[material].append(part)
        
        if self.logger:
            self.logger.info(f"  📦 Группировка по материалам: {len(grouped)} материалов")
            for material, material_parts in grouped.items():
                total_qty = sum(p.get('quantity', 1) for p in material_parts)
                self.logger.info(f"     - {material}: {len(material_parts)} типов, {total_qty} шт")
        
        return dict(grouped)
    
    def calculate_sheet_by_material(self, material: str, parts: List[Dict],
                                     sheet_width: float, sheet_height: float,
                                     kerf: float, time_limit: int = 600,
                                     output_dir: Optional[pathlib.Path] = None) -> Dict:
        """
        Рассчитывает раскрой для одного материала
        
        Args:
            material: Название материала
            parts: Список деталей этого материала
            sheet_width: Ширина листа
            sheet_height: Высота листа
            kerf: Ширина реза
            time_limit: Таймаут в секундах
            output_dir: Папка для сохранения изображений
            
        Returns:
            Словарь с результатами расчета для этого материала
        """
        self._current_sheet_width = sheet_width
        self._current_sheet_height = sheet_height
        
        if not parts:
            return self._get_empty_result(material)
        
        if not PYCKING_AVAILABLE:
            if self.logger:
                self.logger.warning("pyckingsolver не установлен")
            return self._calculate_sheet_simple(material, parts, sheet_width, sheet_height, kerf)
        
        if self.logger:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"📐 РАСЧЕТ РАСКРОЯ ДЛЯ МАТЕРИАЛА: {material}")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"  Размер листа: {sheet_width:.0f}x{sheet_height:.0f} мм")
            self.logger.info(f"  Ширина реза: {kerf} мм")
            self.logger.info(f"  Таймаут: {time_limit} сек")
        
        try:
            # Подготавливаем фигуры (каждый экземпляр детали отдельно)
            shapes = []
            item_areas = []
            part_names = []  # Сохраняем имена для каждого экземпляра
            
            for part in parts:
                width = part.get('width', part.get('length', 0))
                length = part.get('length', 0)
                quantity = part.get('quantity', 1)
                name = part.get('name', 'Unknown')
                
                if width <= 0 or length <= 0:
                    if self.logger:
                        self.logger.warning(f"     ⚠️ Деталь {name}: некорректные размеры ({width}x{length})")
                    continue
                
                # Проверяем, помещается ли деталь на лист (хотя бы одной стороной)
                min_dim = min(width, length)
                max_dim = max(width, length)
                sheet_min = min(sheet_width, sheet_height)
                sheet_max = max(sheet_width, sheet_height)
                
                if max_dim > sheet_max and min_dim > sheet_min:
                    if self.logger:
                        self.logger.warning(f"     ⚠️ Деталь {name} ({width}x{length}) не помещается на лист!")
                    continue
                
                # Добавляем каждую деталь отдельно
                shape = box(0, 0, width, length)
                for i in range(quantity):
                    shapes.append(shape)
                    item_areas.append(width * length)
                    # Сохраняем имя с номером экземпляра для отладки
                    part_names.append(name if quantity == 1 else f"{name}_{i+1}")
            
            if not shapes:
                if self.logger:
                    self.logger.warning(f"  ⚠️ Нет допустимых деталей для материала {material}")
                return self._calculate_sheet_simple(material, parts, sheet_width, sheet_height, kerf)
            
            total_items = len(shapes)
            total_area = sum(item_areas)
            sheet_area = sheet_width * sheet_height
            
            if self.logger:
                self.logger.info(f"  Всего экземпляров: {total_items}")
                self.logger.info(f"  Общая площадь деталей: {total_area/1e6:.3f} м²")
                self.logger.info(f"  Запуск оптимизации (таймаут {time_limit} сек)...")
            
            # Запускаем pyckingsolver с group_identical=True для ускорения
            solution = nest(
                shapes,
                bins=[(sheet_width, sheet_height)],
                objective=Objective.BIN_PACKING,
                spacing=kerf,
                allowed_rotations=[(0, 0), (90, 90)],
                time_limit=time_limit,
                group_identical=True,  # КЛЮЧЕВОЙ ПАРАМЕТР ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
            )
            
            # Извлекаем данные о листах (исправленная версия)
            # Сохраняем размеры каждой детали в том же порядке, что и shapes
            part_sizes = [(width, length) for part in parts for _ in range(part.get('quantity', 1))]
            sheets_data = self._extract_sheets_from_solution(solution, part_names, part_sizes)
            total_bins = len(sheets_data)
            utilization = (total_area / (total_bins * sheet_area)) * 100 if total_bins > 0 else 0
            
            if self.logger:
                self.logger.info(f"\n  ▶ РЕЗУЛЬТАТ ДЛЯ {material}:")
                self.logger.info(f"     Требуется листов: {total_bins} шт")
                self.logger.info(f"     Использование материала: {utilization:.1f}%")
                if total_bins > 0:
                    avg_per_sheet = total_items / total_bins
                    self.logger.info(f"     Среднее деталей на лист: {avg_per_sheet:.1f} шт")
            
            # Сохраняем изображения, если указана папка
            layout_images = []
            if output_dir and sheets_data:
                layout_images = self._save_sheet_images(sheets_data, material, output_dir)
            
            # Суммируем детали для отчета
            parts_summary = self._summarize_parts(parts)
            
            return {
                'material': material,
                'required': total_bins,
                'total_area': total_area,
                'sheet_width': sheet_width,
                'sheet_height': sheet_height,
                'kerf': kerf,
                'utilization': utilization,
                'parts': parts_summary,
                'layout_images': layout_images,
                'sheets_data': sheets_data,
                'algorithm': 'pyckingsolver'
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"  ❌ Ошибка при расчете раскроя для {material}: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
            return self._calculate_sheet_simple(material, parts, sheet_width, sheet_height, kerf)
    
    def calculate_all_materials(self, parts_by_material: Dict[str, List[Dict]],
                                sheet_params_by_material: Dict[str, Dict],
                                time_limit: int = 600,
                                output_dir: Optional[pathlib.Path] = None,
                                excel_name: str = "") -> Dict[str, Dict]:
        """
        Рассчитывает раскрой для всех материалов
        
        Args:
            parts_by_material: {material: [список деталей]}
            sheet_params_by_material: {material: {'width': w, 'height': h, 'cut': kerf}}
            time_limit: Таймаут в секундах
            output_dir: Папка для сохранения изображений
            excel_name: Имя Excel файла для группировки изображений
            
        Returns:
            {material: результат расчета}
        """
        results = {}
        all_sheets_by_material = {}
        
        for material, parts in parts_by_material.items():
            params = sheet_params_by_material.get(material, {})
            sheet_width = params.get('width', 1250)
            sheet_height = params.get('height', 2500)
            kerf = params.get('cut', 2)
            
            result = self.calculate_sheet_by_material(
                material, parts, sheet_width, sheet_height, kerf, time_limit, output_dir
            )
            results[material] = result
            
            if result.get('sheets_data'):
                # Добавляем информацию о материале и размерах в каждый лист
                for sheet in result['sheets_data']:
                    sheet['material'] = material
                    sheet['sheet_width'] = sheet_width
                    sheet['sheet_height'] = sheet_height
                
                all_sheets_by_material[material] = result['sheets_data']
        
        # Сохраняем все изображения в одном месте
        if output_dir and all_sheets_by_material:
            from visualization.layout_drawer import LayoutDrawer
            drawer = LayoutDrawer(self.logger)
            all_images = drawer.draw_all_sheets(all_sheets_by_material, output_dir, excel_name)
            
            # Обновляем результаты с путями к изображениям
            for material, images in all_images.items():
                if material in results:
                    results[material]['layout_images'] = images
        
        return results

    def _extract_sheets_from_solution(self, solution, part_names: List[str], part_sizes: List[Tuple[float, float]]) -> List[Dict]:
        """
        Извлекает данные о каждом листе из решения pyckingsolver
        
        Args:
            solution: решение от pyckingsolver
            part_names: список имен деталей (в порядке shapes)
            part_sizes: список размеров деталей (width, height) в том же порядке
        """
        sheets = []
        
        if not hasattr(solution, 'bins') or solution.bins is None:
            if self.logger:
                self.logger.warning("  Решение не содержит bins")
            return sheets
        
        try:
            for bin_idx, bin_item in enumerate(solution.bins):
                sheet_parts = []
                
                if not hasattr(bin_item, 'items') or bin_item.items is None:
                    continue
                
                for item_idx, item in enumerate(bin_item.items):
                    # Получаем координаты
                    x = getattr(item, 'x', 0)
                    y = getattr(item, 'y', 0)
                    angle = getattr(item, 'angle', 0)
                    
                    # Получаем размеры из сохраненного списка
                    if item_idx < len(part_sizes):
                        w, h = part_sizes[item_idx]
                    else:
                        if self.logger:
                            self.logger.warning(f"  Нет размеров для детали {item_idx}")
                        continue
                    
                    # Если угол 90 или 270, размеры меняются местами
                    if abs(angle) == 90 or abs(angle) == 270:
                        w, h = h, w
                    
                    name = part_names[item_idx] if item_idx < len(part_names) else f"part_{item_idx}"
                    
                    sheet_parts.append({
                        'x': float(x),
                        'y': float(y),
                        'width': float(w),
                        'height': float(h),
                        'name': name,
                        'rotation': angle
                    })
                
                if sheet_parts:
                    sheets.append({
                        'sheet_index': bin_idx + 1,
                        'parts': sheet_parts,
                        'total_parts': len(sheet_parts)
                    })
            
            if self.logger and sheets:
                self.logger.debug(f"  ✅ Извлечено {len(sheets)} листов из решения")
            
            return sheets
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"  ❌ Ошибка при извлечении данных из решения: {e}")
            return sheets



    def _save_sheet_images(self, sheets_data: List[Dict], material: str, output_dir: pathlib.Path) -> List[str]:
        """
        Сохраняет изображения для всех листов
        
        Returns:
            Список путей к сохраненным изображениям
        """
        try:
            from visualization.layout_drawer import LayoutDrawer
            
            drawer = LayoutDrawer(self.logger)
            images = []
            
            for sheet_data in sheets_data:
                # Добавляем информацию о материале и размерах
                sheet_data['material'] = material
                sheet_data['sheet_width'] = self._current_sheet_width
                sheet_data['sheet_height'] = self._current_sheet_height
                
                safe_material = material.replace('/', '_').replace('\\', '_').replace(' ', '_')
                img_path = output_dir / f"layout_{safe_material}_sheet{sheet_data['sheet_index']:02d}.png"
                
                if drawer.draw_sheet(sheet_data, img_path):
                    images.append(str(img_path))
            
            return images
        except ImportError as e:
            if self.logger:
                self.logger.warning(f"Не удалось импортировать LayoutDrawer: {e}")
            return []
    
    def _summarize_parts(self, parts: List[Dict]) -> List[Dict]:
        """Суммирует одинаковые детали для отчета"""
        parts_dict = {}
        for part in parts:
            key = part.get('name', 'Unknown')
            if key in parts_dict:
                parts_dict[key]['quantity'] += part.get('quantity', 1)
            else:
                parts_dict[key] = part.copy()
        return list(parts_dict.values())
    
    def _calculate_sheet_simple(self, material: str, parts: List[Dict], 
                                 sheet_width: float, sheet_height: float, 
                                 kerf: float) -> Dict:
        """Упрощенный расчет (запасной вариант)"""
        parts_dict = {}
        for part in parts:
            key = part.get('name', 'Unknown')
            if key in parts_dict:
                parts_dict[key]['quantity'] += part.get('quantity', 1)
            else:
                parts_dict[key] = part.copy()
        
        unique_parts = list(parts_dict.values())
        
        total_area = 0
        for p in unique_parts:
            width = p.get('width', p.get('length', 0))
            length = p.get('length', 0)
            total_area += width * length * p.get('quantity', 1)
        
        sheet_area = sheet_width * sheet_height
        required = max(1, int((total_area + sheet_area - 1) // sheet_area))
        utilization = (total_area / (required * sheet_area)) * 100 if required > 0 else 0
        
        if self.logger:
            self.logger.info(f"  Упрощенный расчет для {material}: {required} листов, использование {utilization:.1f}%")
        
        return {
            'material': material,
            'required': required,
            'total_area': total_area,
            'sheet_width': sheet_width,
            'sheet_height': sheet_height,
            'kerf': kerf,
            'utilization': utilization,
            'parts': unique_parts,
            'layout_images': [],
            'sheets_data': [],
            'algorithm': 'simple'
        }
    
    def _get_empty_result(self, material: str = "") -> Dict:
        return {
            'material': material,
            'required': 0,
            'total_area': 0,
            'sheet_width': 0,
            'sheet_height': 0,
            'kerf': 0,
            'utilization': 0,
            'parts': [],
            'layout_images': [],
            'sheets_data': [],
            'algorithm': 'none'
        }
    
    def calculate_sheet_advanced(self, parts: List[Dict], sheet_width: float = 1250,
                                  sheet_height: float = 2500, kerf: float = 2.0,
                                  time_limit: int = 600, output_dir: pathlib.Path = None,
                                  material: str = "") -> Dict:
        """
        (Старый метод для обратной совместимости)
        Расчет листового раскроя для одного материала
        """
        parts_with_material = []
        for part in parts:
            part_copy = part.copy()
            part_copy['material'] = material if material else 'unknown'
            parts_with_material.append(part_copy)
        
        return self.calculate_sheet_by_material(
            material if material else 'unknown', 
            parts_with_material, 
            sheet_width, sheet_height, 
            kerf, time_limit, output_dir
        )
    
    def calculate_linear_advanced(self, parts: List[Dict], stock_length: float = 6000,
                                   cut_width: float = 10) -> Dict:
        """Расчет линейного раскроя (оставляем без изменений)"""
        if not parts:
            return {'required': 0, 'total_length': 0, 'stock_length': stock_length,
                    'cut_width': cut_width, 'utilization': 0, 'parts': []}
        
        parts_sorted = []
        for part in parts:
            for _ in range(part.get('quantity', 1)):
                parts_sorted.append({
                    'name': part.get('name', 'Unknown'),
                    'length': part.get('length', 0)
                })
        
        parts_sorted.sort(key=lambda x: x['length'], reverse=True)
        
        stocks = []
        for part in parts_sorted:
            placed = False
            for stock in stocks:
                current_length = sum(p['length'] for p in stock)
                if current_length + part['length'] + cut_width <= stock_length + cut_width:
                    stock.append(part)
                    placed = True
                    break
            if not placed:
                stocks.append([part])
        
        total_length = sum(p['length'] for p in parts_sorted)
        required = len(stocks)
        utilization = (total_length / (required * stock_length)) * 100 if required > 0 else 0
        
        parts_summary = {}
        for stock in stocks:
            for part in stock:
                key = part['name']
                if key not in parts_summary:
                    parts_summary[key] = {'name': key, 'quantity': 0, 'length': part['length']}
                parts_summary[key]['quantity'] += 1
        
        if self.logger:
            self.logger.info(f"     Линейный раскрой: {required} заготовок, использование {utilization:.1f}%")
        
        return {
            'required': required,
            'total_length': total_length,
            'stock_length': stock_length,
            'cut_width': cut_width,
            'utilization': utilization,
            'parts': list(parts_summary.values()),
            'algorithm': 'first_fit_decreasing'
        }