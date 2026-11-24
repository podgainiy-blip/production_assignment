"""
Модуль для расчета раскроя и визуализации с использованием rectpack
Берет на вход словарь {категория_материал: [(ширина, высота, имя), ...]}
Выдает раскладку и сохраняет картинки
"""

import pathlib
import time
from typing import Dict, List, Tuple, Optional
from collections import Counter

try:
    from rectpack import newPacker, MaxRectsBssf
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    RECTPACK_AVAILABLE = True
except ImportError as e:
    RECTPACK_AVAILABLE = False
    print(f"⚠️ rectpack или matplotlib не загружены: {e}")


class RectpackVisualizer:
    """Класс для расчета раскроя и визуализации"""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def process_material(self, key: str, items: List[Tuple[float, float, str]],
                         sheet_width: float, sheet_height: float, kerf: float,
                         output_dir: pathlib.Path) -> Dict:
        """
        Обрабатывает один материал (ключ вида category_material)
        
        Args:
            key: ключ вида "категория_материал" (например "punch_оц_1.5мм")
            items: список кортежей (ширина, высота, имя) для каждой детали
            sheet_width: ширина листа
            sheet_height: высота листа
            kerf: ширина реза
            output_dir: базовая папка (например МТП_proc/)
        """
        if not RECTPACK_AVAILABLE:
            return {'error': 'rectpack не установлен'}
        
        # Разделяем ключ на категорию и материал
        parts = key.split('_', 1)
        if len(parts) == 2:
            category, material = parts
        else:
            category = 'other'
            material = key
        
        # Извлекаем размеры для упаковки и сохраняем имена
        rectangles = [(w, h) for w, h, name in items]
        names = [name for w, h, name in items]
        
        if self.logger:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"📐 РАСЧЕТ РАСКРОЯ: {category} / {material}")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"  Размер листа: {sheet_width} x {sheet_height} мм")
            self.logger.info(f"  Ширина реза: {kerf} мм")
            self.logger.info(f"  Всего деталей: {len(items)} шт")
            
            # Показываем уникальные размеры
            unique = Counter(rectangles)
            self.logger.info(f"  Уникальных размеров: {len(unique)}")
            for (w, h), cnt in list(unique.items())[:5]:
                self.logger.info(f"    {w:.0f}x{h:.0f} мм: {cnt} шт")
            if len(unique) > 5:
                self.logger.info(f"    ... и еще {len(unique) - 5} типов")
        
        # Создаем упаковщик
        packer = newPacker(
            pack_algo=MaxRectsBssf,
            rotation=True
        )
        
        # Добавляем детали с учетом kerf (для упаковки)
        for w, h in rectangles:
            packer.add_rect(w + kerf, h + kerf)
        
        # Добавляем листы с запасом
        for _ in range(len(items)):
            packer.add_bin(sheet_width, sheet_height)
        
        # Запускаем упаковку
        start = time.time()
        packer.pack()
        elapsed = time.time() - start
        
        # Получаем результаты
        used_bins = len(packer)
        total_area = sum(w * h for w, h in rectangles)
        sheet_area = sheet_width * sheet_height
        utilization = (total_area / (used_bins * sheet_area)) * 100 if used_bins > 0 else 0
        
        if self.logger:
            self.logger.info(f"  Время расчета: {elapsed:.3f} сек")
            self.logger.info(f"\n  ▶ РЕЗУЛЬТАТ:")
            self.logger.info(f"     Требуется листов: {used_bins} шт")
            self.logger.info(f"     Использование материала: {utilization:.1f}%")
        
        # Сохраняем изображения и текстовый отчет
        images, report_file = self._save_results(
            packer, category, material, rectangles, names,
            sheet_width, sheet_height, kerf, output_dir
        )
        
        return {
            'category': category,
            'material': material,
            'key': key,
            'required': used_bins,
            'total_area': total_area,
            'sheet_width': sheet_width,
            'sheet_height': sheet_height,
            'kerf': kerf,
            'utilization': utilization,
            'layout_images': images,
            'report_file': report_file,
            'time': elapsed
        }
    
    def _save_results(self, packer, category: str, material: str, 
                      original_rectangles: List[Tuple[float, float]],
                      names: List[str],
                      sheet_width: float, sheet_height: float, kerf: float,
                      output_dir: pathlib.Path) -> Tuple[List[str], Optional[pathlib.Path]]:
        """
        Сохраняет изображения и текстовый отчет
        
        Returns:
            (список_путей_к_изображениям, путь_к_текстовому_отчету)
        """
        images = []
        
        if len(packer) == 0:
            return images, None
        
        # Создаем структуру папок: категория/layouts/материал/
        category_dir = output_dir / category
        layouts_dir = category_dir / "layouts"
        material_dir = layouts_dir / material
        material_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка цветов
        colors = plt.cm.tab20(range(20))
        
        # Собираем информацию для текстового отчета
        report_lines = []
        report_lines.append("="*80)
        report_lines.append(f"ОТЧЕТ О РАСКРОЕ")
        report_lines.append("="*80)
        report_lines.append(f"Категория: {category}")
        report_lines.append(f"Материал: {material}")
        report_lines.append(f"Размер листа: {sheet_width:.0f} x {sheet_height:.0f} мм")
        report_lines.append(f"Ширина реза: {kerf} мм")
        report_lines.append(f"Всего листов: {len(packer)}")
        report_lines.append("")
        
        # Сохраняем каждый лист
        rect_idx = 0
        for bin_idx, abin in enumerate(packer):
            fig, ax = plt.subplots(figsize=(12, 10))
            
            # Рисуем границу листа
            ax.add_patch(Rectangle((0, 0), sheet_width, sheet_height, 
                                   fill=False, edgecolor='black', linewidth=2))
            
            sheet_info = []
            sheet_info.append(f"\n{'='*60}")
            sheet_info.append(f"ЛИСТ {bin_idx + 1}")
            sheet_info.append(f"{'='*60}")
            sheet_info.append(f"{'№':<4} {'Обозначение':<20} {'Размер (мм)':<15} {'Поворот':<8} {'Координаты (x,y)':<20}")
            sheet_info.append(f"{'-'*60}")
            
            # Рисуем каждую деталь на листе
            for idx, rect in enumerate(abin):
                if hasattr(rect, 'x'):
                    x, y, w, h = rect.x, rect.y, rect.width, rect.height
                else:
                    x, y, w, h = rect[0], rect[1], rect[2], rect[3]
                
                # Получаем оригинальные размеры и имя
                if rect_idx < len(original_rectangles):
                    orig_w, orig_h = original_rectangles[rect_idx]
                    name = names[rect_idx]
                else:
                    orig_w, orig_h = w - kerf, h - kerf
                    name = f"деталь_{rect_idx}"
                
                rect_idx += 1
                
                # Определяем поворот
                rotation = 0
                if abs(w - orig_h - kerf) < 0.1 and abs(h - orig_w - kerf) < 0.1:
                    rotation = 90
                
                color = colors[idx % len(colors)]
                rect_patch = Rectangle((x, y), w, h, 
                                      fill=True, alpha=0.7, edgecolor='blue', 
                                      facecolor=color, linewidth=1)
                ax.add_patch(rect_patch)
                
                # Подписываем ОБОЗНАЧЕНИЕМ детали
                # Обрезаем длинные имена для отображения
                display_name = name if len(name) <= 15 else name[:12] + '...'
                ax.text(x + w/2, y + h/2, display_name, 
                       ha='center', va='center', fontsize=7 if len(display_name) > 10 else 8,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
                
                # Добавляем в текстовый отчет
                sheet_info.append(f"{idx+1:<4} {name:<20} {orig_w:.0f}x{orig_h:<4} {rotation:>3}°      ({x:.0f}, {y:.0f})")
            
            ax.set_xlim(-10, sheet_width + 10)
            ax.set_ylim(-10, sheet_height + 10)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_title(f'{category} / {material} - Лист {bin_idx + 1} ({sheet_width:.0f}x{sheet_height:.0f}) - {len(abin)} деталей', 
                        fontsize=14, fontweight='bold')
            ax.set_xlabel('X (мм)', fontsize=10)
            ax.set_ylabel('Y (мм)', fontsize=10)
            
            # Сохраняем картинку
            img_path = material_dir / f"sheet_{bin_idx + 1:03d}.png"
            plt.savefig(img_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            
            images.append(str(img_path))
            
            # Добавляем информацию о листе в общий отчет
            report_lines.extend(sheet_info)
            report_lines.append(f"\n📄 Изображение: {img_path.name}")
        
        # Сохраняем текстовый отчет
        report_lines.append("\n" + "="*80)
        report_file = material_dir / "layout_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        
        if self.logger:
            self.logger.info(f"  📊 Сохранено {len(images)} изображений в {material_dir}")
            self.logger.info(f"  📄 Текстовый отчет: {report_file}")
        
        return images, report_file
    
    def process_all_materials(self, sheet_data: Dict[str, List[Tuple[float, float, str]]],
                              sheet_params: Dict[str, Dict],
                              output_dir: pathlib.Path) -> Dict[str, Dict]:
        """
        Обрабатывает все материалы
        
        Args:
            sheet_data: {категория_материал: [(w, h, имя), (w, h, имя), ...]}
            sheet_params: {категория_материал: {'width': w, 'height': h, 'cut': kerf}}
            output_dir: базовая папка (например МТП_proc/)
        """
        if not RECTPACK_AVAILABLE:
            return {}
        
        results = {}
        
        # Выводим полученные данные для проверки
        if self.logger:
            self.logger.info("\n" + "="*80)
            self.logger.info("ПОЛУЧЕННЫЕ ДАННЫЕ ДЛЯ РАСКРОЯ")
            self.logger.info("="*80)
            for key, items in sheet_data.items():
                self.logger.info(f"\n  📦 {key}:")
                self.logger.info(f"     Количество деталей: {len(items)} шт")
                # Считаем уникальные размеры
                rectangles = [(w, h) for w, h, name in items]
                unique = Counter(rectangles)
                self.logger.info(f"     Уникальных размеров: {len(unique)}")
                for (w, h), cnt in list(unique.items())[:3]:
                    # Показываем пример имени
                    example_name = next(name for w2, h2, name in items if w2 == w and h2 == h)
                    self.logger.info(f"       {w:.0f}x{h:.0f} мм ({example_name}): {cnt} шт")
                if len(unique) > 3:
                    self.logger.info(f"       ... и еще {len(unique) - 3} типов")
            self.logger.info("="*80)
        
        # Обрабатываем каждый ключ
        for key, items in sheet_data.items():
            params = sheet_params.get(key, {})
            sheet_width = params.get('width', 1250)
            sheet_height = params.get('height', 2500)
            kerf = params.get('cut', 2)
            
            result = self.process_material(
                key, items, sheet_width, sheet_height, kerf, output_dir
            )
            results[key] = result
        
        return results