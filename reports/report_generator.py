"""
Формирование отчетов о раскрое
"""

from datetime import datetime
from typing import Dict, List, Tuple


class ReportGenerator:
    """Класс для формирования отчетов о раскрое"""
    
    @staticmethod
    def generate_calculation_report(engine, excel_name: str = "") -> Tuple[str, List[str]]:
        """
        Генерирует отчет с расчетом необходимого количества материалов
        """
        full_lines = []
        summary_lines = []
        
        full_lines.append("=" * 80)
        full_lines.append("РАСЧЕТ РАСКРОЯ МАТЕРИАЛОВ")
        full_lines.append("=" * 80)
        if excel_name:
            full_lines.append(f"Файл: {excel_name}")
        full_lines.append(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        full_lines.append("")
        
        summary_lines.append("")
        summary_lines.append("=" * 50)
        summary_lines.append("НЕОБХОДИМОЕ КОЛИЧЕСТВО МАТЕРИАЛА")
        summary_lines.append("=" * 50)
        
        has_data = False
        all_layout_images = []
        
        # Пробуем получить результаты из нового метода
        if hasattr(engine, 'calculate_all_materials_advanced'):
            try:
                results = engine.calculate_all_materials_advanced(excel_name=excel_name)
                if results:
                    has_data = True
                    for material, result in results.items():
                        full_lines.append(f"\n{'=' * 60}")
                        full_lines.append(f"МАТЕРИАЛ: {material}")
                        full_lines.append(f"{'=' * 60}")
                        full_lines.append(f"  Общая площадь: {result.get('total_area', 0) / 1e6:.2f} м²")
                        full_lines.append(f"  Размер листа: {result.get('sheet_width', 0):.0f}x{result.get('sheet_height', 0):.0f} мм")
                        full_lines.append(f"  Ширина реза: {result.get('kerf', 0)} мм")
                        full_lines.append(f"  ▶ ТРЕБУЕТСЯ ЛИСТОВ: {result.get('required', 0)} шт")
                        full_lines.append(f"  Использование: {result.get('utilization', 0):.1f}%")
                        full_lines.append(f"  Алгоритм: {result.get('algorithm', 'стандартный')}")
                        
                        summary_lines.append(f"\n{material}:")
                        summary_lines.append(f"  {result.get('required', 0)} шт (лист {result.get('sheet_width', 0):.0f}x{result.get('sheet_height', 0):.0f} мм)")
                        summary_lines.append(f"  Использование: {result.get('utilization', 0):.1f}%")
                        
                        if result.get('layout_images'):
                            all_layout_images.extend(result['layout_images'])
                            full_lines.append(f"\n  📊 Изображения раскладки:")
                            for img in result['layout_images']:
                                full_lines.append(f"    - {img}")
                        
                        if result.get('parts'):
                            full_lines.append(f"\n  Список деталей:")
                            for part in result['parts']:
                                w = part.get('width', part.get('length', 0))
                                l = part.get('length', 0)
                                full_lines.append(f"    - {part.get('name', 'Unknown')}: {l:.0f}x{w:.0f} мм x {part.get('quantity', 1)} шт")
                    return "\n".join(full_lines), summary_lines
            except Exception as e:
                if hasattr(engine, 'logger') and engine.logger:
                    engine.logger.debug(f"Новый метод расчета не сработал: {e}")
        
        # Если новый метод не сработал, пробуем старые данные
        # Линейные материалы (profile, busbar)
        linear_data = engine.get_linear_data() if hasattr(engine, 'get_linear_data') else {}
        for cat in ['profile', 'busbar']:
            if linear_data.get(cat):
                has_data = True
                full_lines.append(f"\n{'=' * 60}")
                full_lines.append(f"{cat.upper()} (линейный раскрой)")
                full_lines.append(f"{'=' * 60}")
                summary_lines.append(f"\n{cat.upper()}:")
                
                for material, parts in linear_data[cat].items():
                    from data.cutting_params import get_material_params
                    params = get_material_params(cat, material)
                    stock_length = params.get('length', 6000)
                    cut_width = params.get('cut', 10)
                    
                    result = engine.calculate_linear(parts, stock_length, cut_width)
                    
                    full_lines.append(f"\n--- Материал: {material} ---")
                    full_lines.append(f"  Общая длина: {result['total_length']:.0f} мм")
                    full_lines.append(f"  Длина заготовки: {stock_length} мм")
                    full_lines.append(f"  Ширина реза: {cut_width} мм")
                    full_lines.append(f"  ▶ ТРЕБУЕТСЯ ЗАГОТОВОК: {result['required']} шт")
                    full_lines.append(f"  Использование: {result['utilization']:.1f}%")
                    
                    summary_lines.append(f"  {material}: {result['required']} шт (длина {stock_length} мм)")
                    
                    if result.get('parts'):
                        full_lines.append(f"\n  Список деталей:")
                        for part in result['parts']:
                            full_lines.append(f"    - {part['name']}: {part['length']:.0f} мм x {part['quantity']} шт")
        
        if not has_data:
            full_lines.append("\n⚠️ НЕТ ДАННЫХ ДЛЯ РАСЧЕТА")
            summary_lines.append("\n⚠️ НЕТ ДАННЫХ")
        
        full_lines.append("\n" + "=" * 80)
        
        return "\n".join(full_lines), summary_lines

