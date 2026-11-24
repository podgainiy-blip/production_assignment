"""
Отрисовка раскладки деталей на листах
"""

import pathlib
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib не установлен, визуализация недоступна")


class LayoutDrawer:
    """Отрисовщик раскладки деталей на листах"""
    
    def __init__(self, logger=None, dpi: int = 150):
        self.logger = logger
        self.dpi = dpi
        self.colors = plt.cm.tab20.colors if MATPLOTLIB_AVAILABLE else []
    
    def draw_sheet(self, sheet_data: Dict, output_path: pathlib.Path) -> bool:
        """
        Отрисовывает один лист с деталями
        
        Args:
            sheet_data: Словарь с данными листа:
                - sheet_index: номер листа
                - sheet_width: ширина листа
                - sheet_height: высота листа
                - material: материал
                - parts: список деталей [{'x', 'y', 'width', 'height', 'name', 'rotation'}]
                - total_parts: общее количество деталей на листе
            output_path: путь для сохранения изображения
            
        Returns:
            True если успешно
        """
        if not MATPLOTLIB_AVAILABLE:
            return False
        
        try:
            fig, ax = plt.subplots(1, 1, figsize=(14, 10))
            
            # Рисуем границы листа
            sheet_rect = Rectangle(
                (0, 0), 
                sheet_data['sheet_width'], 
                sheet_data['sheet_height'],
                linewidth=2, 
                edgecolor='black',
                facecolor='none', 
                linestyle='--'
            )
            ax.add_patch(sheet_rect)
            
            # Отрисовываем каждую деталь
            for i, part in enumerate(sheet_data['parts']):
                x = part['x']
                y = part['y']
                w = part['width']
                h = part['height']
                name = part.get('name', f"{w:.0f}x{h:.0f}")
                rotation = part.get('rotation', 0)
                color = self.colors[i % len(self.colors)] if self.colors else 'lightblue'
                
                # Рисуем прямоугольник детали
                rect = Rectangle(
                    (x, y), w, h,
                    linewidth=1.5,
                    edgecolor='darkblue',
                    facecolor=color,
                    alpha=0.7
                )
                ax.add_patch(rect)
                
                # Отмечаем повернутые детали
                if rotation != 0:
                    ax.text(
                        x + w - 10, y + 15, '↻', 
                        fontsize=12, fontweight='bold',
                        bbox=dict(boxstyle='circle', facecolor='yellow', alpha=0.8)
                    )
                
                # Подпись детали (в центре)
                center_x = x + w / 2
                center_y = y + h / 2
                # Обрезаем длинные имена (максимум 15 символов)
                display_name = name if len(name) <= 15 else name[:12] + '...'
                ax.text(
                    center_x, center_y, display_name,
                    ha='center', va='center',
                    fontsize=7 if len(display_name) > 10 else 8,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none')
                )
            
            # Настройки графика
            ax.set_xlim(-50, sheet_data['sheet_width'] + 50)
            ax.set_ylim(-50, sheet_data['sheet_height'] + 50)
            ax.set_xlabel('Ширина (мм)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Высота (мм)', fontsize=12, fontweight='bold')
            ax.set_title(
                f'Раскладка листа #{sheet_data["sheet_index"]}\n'
                f'Материал: {sheet_data["material"]}\n'
                f'Размер: {sheet_data["sheet_width"]:.0f}x{sheet_data["sheet_height"]:.0f} мм\n'
                f'Деталей: {sheet_data["total_parts"]} шт.',
                fontsize=14, 
                fontweight='bold'
            )
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_aspect('equal')
            
            # Информация в углу
            info_text = f"Всего деталей: {sheet_data['total_parts']}"
            ax.text(
                sheet_data['sheet_width'] - 10, 
                sheet_data['sheet_height'] - 20, 
                info_text,
                fontsize=9, 
                ha='right', 
                va='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
            )
            
            # Сохраняем
            plt.tight_layout()
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight', facecolor='white')
            plt.close()
            
            if self.logger:
                self.logger.debug(f"  📊 Сохранена раскладка: {output_path.name}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"  ❌ Ошибка отрисовки листа: {e}")
            return False
    
    def draw_all_sheets(self, solutions_by_material: Dict[str, List[Dict]], 
                       output_dir: pathlib.Path, excel_name: str = "") -> Dict[str, List[str]]:
        """
        Отрисовывает все листы для всех материалов
        
        Args:
            solutions_by_material: {material: [sheet_data1, sheet_data2, ...]}
            output_dir: папка для сохранения
            excel_name: имя Excel файла для группировки
            
        Returns:
            {material: [список_путей_к_изображениям]}
        """
        if not MATPLOTLIB_AVAILABLE:
            if self.logger:
                self.logger.warning("matplotlib не установлен, визуализация недоступна")
            return {}
        
        output_dir = pathlib.Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_images = {}
        
        for material, sheets in solutions_by_material.items():
            material_images = []
            safe_material = self._sanitize_filename(material)
            
            for sheet_data in sheets:
                img_filename = f"layout_{safe_material}_sheet{sheet_data['sheet_index']:02d}.png"
                if excel_name:
                    img_filename = f"{excel_name}_{img_filename}"
                img_path = output_dir / img_filename
                
                if self.draw_sheet(sheet_data, img_path):
                    material_images.append(str(img_path))
            
            all_images[material] = material_images
            
            if self.logger and material_images:
                self.logger.info(f"  📊 {material}: сохранено {len(material_images)} изображений раскладки")
        
        return all_images
    
    def _sanitize_filename(self, name: str) -> str:
        """Очищает имя файла от недопустимых символов"""
        import re
        name = re.sub(r'[\\/*?:"<>|]', '_', str(name))
        name = name.replace(' ', '_')
        name = name[:100]
        return name