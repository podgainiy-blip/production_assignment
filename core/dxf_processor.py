"""
Обработка DXF файлов
"""

import pathlib
from typing import Optional, Dict, Tuple


class DXFProcessor:
    """Класс для обработки DXF файлов"""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def process_dxf(self, dxf_path: pathlib.Path) -> Optional[Dict]:
        """Обрабатывает DXF файл и возвращает его характеристики"""
        try:
            from dxf_hash import get_dxf_hash
            
            dxf_hash, circles, arcs, is_bad_circles, is_bad_arcs, bb_width, bb_height = get_dxf_hash(dxf_path)
            
            result = {
                'hash': dxf_hash,
                'circles': circles,
                'arcs': arcs,
                'is_bad_circles': is_bad_circles,
                'is_bad_arcs': is_bad_arcs,
                'width': bb_width,
                'height': bb_height,
                'length': max(bb_width, bb_height),
                'area': bb_width * bb_height if bb_width > 0 and bb_height > 0 else 0
            }
            
            if self.logger:
                self.logger.debug(f"Обработан DXF: {dxf_path.name} ({bb_width:.1f}x{bb_height:.1f})")
            
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка DXF {dxf_path.name}: {e}")
            return None
    
    def get_dimensions(self, dxf_path: pathlib.Path) -> Tuple[float, float]:
        """Возвращает только габариты из DXF"""
        result = self.process_dxf(dxf_path)
        if result:
            return result['width'], result['height']
        return 0, 0