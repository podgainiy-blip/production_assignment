"""
Расчет раскроя с использованием rectpack
Быстрый и надежный алгоритм для прямоугольных деталей
"""

from typing import List, Dict, Tuple, Optional
import pathlib
from collections import defaultdict

try:
    from rectpack import newPacker, MaxRectsBssf
    RECTPACK_AVAILABLE = True
    print("✅ rectpack успешно загружен")
except ImportError as e:
    RECTPACK_AVAILABLE = False
    print(f"⚠️ rectpack не загружен: {e}")


class RectPackEngine:
    """Класс для расчета раскроя с использованием rectpack"""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def calculate_sheet_by_material(self, material: str, rectangles: List[Tuple[float, float]],
                                    sheet_width: float, sheet_height: float, kerf: float,
                                    output_dir: Optional[pathlib.Path] = None) -> Dict:
        """
        Рассчитывает раскрой для одного материала
        
        Args:
            material: Название материала
            rectangles: Список кортежей (ширина, высота) для каждой детали (уже развернуто)
            sheet_width: Ширина листа
            sheet_height: Высота листа
            kerf: Ширина реза
            output_dir: Папка для сохранения изображений
            
        Returns:
            Словарь с результатами расчета
        """
        if not rectangles:
            return self._get_empty_result(material)
        
        if not RECTPACK_AVAILABLE:
            if self.logger:
                self.logger.warning("rectpack не установлен")
            return self._calculate_simple(material, rectangles, sheet_width, sheet_height)
        
        if self.logger:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"📐 РАСЧЕТ РАСКРОЯ: {material}")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"  Размер листа: {sheet_width:.0f}x{sheet_height:.0f} мм")
            self.logger.info(f"  Ширина реза: {kerf} мм")
            self.logger.info(f"  Всего деталей: {len(rectangles)} шт")
            
            from collections import Counter
            unique = Counter(rectangles)
            self.logger.info(f"  Уникальных размеров: {len(unique)}")
        
        # Создаем упаковщик
        packer = newPacker(
            pack_algo=MaxRectsBssf,
            rotation=True
        )
        
        # Добавляем детали (с учетом kerf)
        for w, h in rectangles:
            packer.add_rect(w + kerf, h + kerf)
        
        # Добавляем листы с запасом (максимум 1 деталь на лист)
        for _ in range(len(rectangles)):
            packer.add_bin(sheet_width, sheet_height)
        
        # Запускаем упаковку
        packer.pack()
        
        # Получаем результаты
        used_bins = len(packer)
        total_area = sum(w * h for w, h in rectangles)
        sheet_area = sheet_width * sheet_height
        utilization = (total_area / (used_bins * sheet_area)) * 100 if used_bins > 0 else 0
        
        if self.logger:
            self.logger.info(f"\n  ▶ РЕЗУЛЬТАТ:")
            self.logger.info(f"     Требуется листов: {used_bins} шт")
            self.logger.info(f"     Использование: {utilization:.1f}%")
            if used_bins > 0:
                avg_per_sheet = len(rectangles) / used_bins
                self.logger.info(f"     Среднее деталей на лист: {avg_per_sheet:.1f} шт")
        
        # Извлекаем данные для визуализации
        sheets_data = self._extract_sheets(packer, rectangles, kerf, sheet_width, sheet_height)
        
        # Сохраняем изображения
        layout_images = []
        if output_dir and sheets_data:
            layout_images = self._save_images(sheets_data, material, sheet_width, sheet_height, output_dir)
        
        return {
            'material': material,
            'required': used_bins,
            'total_area': total_area,
            'sheet_width': sheet_width,
            'sheet_height': sheet_height,
            'kerf': kerf,
            'utilization': utilization,
            'layout_images': layout_images,
            'sheets_data': sheets_data,
            'algorithm': 'rectpack'
        }
    
    def _extract_sheets(self, packer, original_rectangles: List[Tuple[float, float]], 
                        kerf: float, sheet_width: float, sheet_height: float) -> List[Dict]:
        """
        Извлекает данные о каждом листе из packer
        """
        sheets = []
        rect_idx = 0
        
        for bin_idx, bin_item in enumerate(packer):
            sheet_parts = []
            
            for rect in bin_item:
                # Получаем координаты и размеры
                if hasattr(rect, 'x'):
                    x = rect.x
                    y = rect.y
                    w = rect.width
                    h = rect.height
                else:
                    x, y, w, h = rect[0], rect[1], rect[2], rect[3]
                
                # Оригинальные размеры (без kerf)
                if rect_idx < len(original_rectangles):
                    orig_w, orig_h = original_rectangles[rect_idx]
                else:
                    orig_w, orig_h = w - kerf, h - kerf
                
                rect_idx += 1
                
                # Определяем поворот
                rotation = 0
                if abs(w - orig_h - kerf) < 0.1 and abs(h - orig_w - kerf) < 0.1:
                    rotation = 90
                
                # БЕЗ ПРЕОБРАЗОВАНИЯ КООРДИНАТ - как в тестовом скрипте
                # Координаты из rectpack уже подходят для matplotlib
                y_transformed = y
                
                # Создаем имя детали на основе размеров
                name = f"{orig_w:.0f}x{orig_h:.0f}"
                
                sheet_parts.append({
                    'x': float(x),
                    'y': float(y_transformed),
                    'width': float(orig_w),
                    'height': float(orig_h),
                    'name': name,
                    'rotation': rotation
                })
            
            if sheet_parts:
                sheets.append({
                    'sheet_index': bin_idx + 1,
                    'parts': sheet_parts,
                    'total_parts': len(sheet_parts)
                })
        
        # Отладка
        if self.logger and sheets:
            self.logger.debug(f"  📊 Пример данных первого листа:")
            for part in sheets[0]['parts'][:3]:
                self.logger.debug(f"     {part['name']}: x={part['x']:.1f}, y={part['y']:.1f}, w={part['width']:.1f}, h={part['height']:.1f}")
        
        return sheets


    def _save_images(self, sheets_data: List[Dict], material: str, 
                     sheet_width: float, sheet_height: float, 
                     output_dir: pathlib.Path) -> List[str]:
        """
        Сохраняет изображения для всех листов
        
        Args:
            sheets_data: список данных о листах
            material: название материала
            sheet_width: ширина листа
            sheet_height: высота листа
            output_dir: папка для сохранения
        """
        try:
            from visualization.layout_drawer import LayoutDrawer
            drawer = LayoutDrawer(self.logger)
            images = []
            
            for sheet_data in sheets_data:
                # Добавляем размеры листа и материал в данные
                sheet_data['material'] = material
                sheet_data['sheet_width'] = sheet_width
                sheet_data['sheet_height'] = sheet_height
                
                safe_material = material.replace('/', '_').replace('\\', '_').replace(' ', '_')
                img_path = output_dir / f"layout_{safe_material}_sheet{sheet_data['sheet_index']:02d}.png"
                
                if drawer.draw_sheet(sheet_data, img_path):
                    images.append(str(img_path))
            
            if self.logger and images:
                self.logger.info(f"  📊 Сохранено {len(images)} изображений раскладки для {material}")
            
            return images
        except ImportError as e:
            if self.logger:
                self.logger.warning(f"Не удалось импортировать LayoutDrawer: {e}")
            return []
    
    def _calculate_simple(self, material: str, rectangles: List[Tuple[float, float]],
                          sheet_width: float, sheet_height: float) -> Dict:
        """Упрощенный расчет по площади (запасной вариант)"""
        total_area = sum(w * h for w, h in rectangles)
        sheet_area = sheet_width * sheet_height
        required = max(1, int((total_area + sheet_area - 1) // sheet_area))
        utilization = (total_area / (required * sheet_area)) * 100 if required > 0 else 0
        
        if self.logger:
            self.logger.info(f"  Упрощенный расчет: {required} листов, использование {utilization:.1f}%")
        
        return {
            'material': material,
            'required': required,
            'total_area': total_area,
            'sheet_width': sheet_width,
            'sheet_height': sheet_height,
            'kerf': 0,
            'utilization': utilization,
            'layout_images': [],
            'sheets_data': [],
            'algorithm': 'simple'
        }
    
    def _get_empty_result(self, material: str) -> Dict:
        return {
            'material': material,
            'required': 0,
            'total_area': 0,
            'sheet_width': 0,
            'sheet_height': 0,
            'kerf': 0,
            'utilization': 0,
            'layout_images': [],
            'sheets_data': [],
            'algorithm': 'none'
        }
    
    def calculate_all_materials(self, parts_by_material: Dict[str, List[Tuple[float, float]]],
                                sheet_params_by_material: Dict[str, Dict],
                                output_dir: Optional[pathlib.Path] = None,
                                excel_name: str = "") -> Dict[str, Dict]:
        """
        Рассчитывает раскрой для всех материалов
        
        Args:
            parts_by_material: {material: [(ширина, высота), ...]}
            sheet_params_by_material: {material: {'width': w, 'height': h, 'cut': kerf}}
            output_dir: папка для сохранения изображений
            excel_name: имя Excel файла (не используется, оставлен для совместимости)
            
        Returns:
            {material: результат расчета}
        """
        results = {}
        
        for material, rectangles in parts_by_material.items():
            if not rectangles:
                continue
            
            params = sheet_params_by_material.get(material, {})
            sheet_width = params.get('width', 1250)
            sheet_height = params.get('height', 2500)
            kerf = params.get('cut', 2)
            
            result = self.calculate_sheet_by_material(
                material, rectangles, sheet_width, sheet_height, kerf, output_dir
            )
            results[material] = result
        
        return results