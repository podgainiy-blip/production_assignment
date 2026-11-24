"""
Сохранение отчетов в файлы
"""

import pathlib
from datetime import datetime
from typing import Optional


class ReportSaver:
    """
    Класс для сохранения отчетов в файлы
    """
    
    def __init__(self, logger=None):
        """
        Args:
            logger: Объект логгера
        """
        self.logger = logger
    
    def save_report(self, report_text: str, output_dir: pathlib.Path, 
                    report_name: str = "cutting_report") -> Optional[pathlib.Path]:
        """
        Сохраняет отчет в файл
        
        Args:
            report_text: Текст отчета
            output_dir: Папка для сохранения
            report_name: Базовое имя файла
            
        Returns:
            Путь к сохраненному файлу или None при ошибке
        """
        if not report_text:
            if self.logger:
                self.logger.warning("Нет текста для сохранения")
            return None
        
        # Создаем папку если нужно
        output_dir = pathlib.Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Формируем имя файла с датой и временем
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}.txt"
        filepath = output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            if self.logger:
                self.logger.success(f"Отчет сохранен: {filepath}")
            
            return filepath
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка сохранения отчета: {e}")
            return None
    
    def save_summary_report(self, summary_lines: list, output_dir: pathlib.Path,
                           report_name: str = "summary_report") -> Optional[pathlib.Path]:
        """
        Сохраняет краткий отчет (только итоги)
        
        Args:
            summary_lines: Список строк краткого отчета
            output_dir: Папка для сохранения
            report_name: Базовое имя файла
            
        Returns:
            Путь к сохраненному файлу
        """
        report_text = "\n".join(summary_lines)
        return self.save_report(report_text, output_dir, report_name)
    
    def save_missing_files_report(self, missing_files: list, output_dir: pathlib.Path) -> Optional[pathlib.Path]:
        """
        Сохраняет отчет об отсутствующих файлах
        
        Args:
            missing_files: Список отсутствующих файлов
            output_dir: Папка для сохранения
            
        Returns:
            Путь к сохраненному файлу
        """
        if not missing_files:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = output_dir / f"missing_files_{timestamp}.txt"
        
        lines = []
        lines.append("=" * 60)
        lines.append("ОТЧЕТ ОБ ОТСУТСТВУЮЩИХ ФАЙЛАХ")
        lines.append("=" * 60)
        lines.append(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        lines.append(f"Всего отсутствует: {len(missing_files)} файлов")
        lines.append("")
        
        for file in missing_files:
            lines.append(f"  • {file}")
        
        lines.append("=" * 60)
        
        return self.save_report("\n".join(lines), output_dir, "missing_files")
    
    def save_all_reports(self, full_report: str, summary_lines: list, 
                         missing_files: list, output_dir: pathlib.Path) -> dict:
        """
        Сохраняет все отчеты сразу
        
        Args:
            full_report: Полный отчет
            summary_lines: Краткий отчет для лога
            missing_files: Список отсутствующих файлов
            output_dir: Папка для сохранения
            
        Returns:
            Словарь с путями к сохраненным файлам
        """
        results = {}
        
        # Полный отчет
        full_path = self.save_report(full_report, output_dir, "cutting_report")
        if full_path:
            results['full_report'] = full_path
        
        # Отчет об отсутствующих файлах
        missing_path = self.save_missing_files_report(missing_files, output_dir)
        if missing_path:
            results['missing_report'] = missing_path
        
        return results