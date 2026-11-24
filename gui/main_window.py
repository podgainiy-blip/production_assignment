"""
Главное окно приложения
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
import pathlib
import shutil
import json
import socket
import requests
import pandas as pd
import re
from datetime import datetime
from collections import defaultdict
from tkinterdnd2 import DND_FILES, TkinterDnD

# Импорт модулей
from dxf_hash import get_dxf_hash, export_white_bg
from core.cutting_data_collector import CuttingDataCollector, FileFinder, FileCopier, RowProcessor
from core.dxf_processor import DXFProcessor
from core.file_manager import FileManager
from core.excel_handler import ExcelHandler
from core.cutting_engine import CuttingEngine
from reports.report_generator import ReportGenerator
from reports.report_saver import ReportSaver
from data.material_dict import load_material_dict
from data.cutting_params import load_cutting_params
from utils.logger import Logger
from utils.file_utils import sanitize_filename, get_timestamp


class MainWindow:
    """Главное окно приложения"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("DXF/Laser Punch Task Processor")
        self.root.geometry("1100x900")
        self.root.configure(bg='#f0f0f0')
        
        # Переменные
        self.input_path = tk.StringVar()
        
        # Загружаем настройки из файла
        from config.settings import load_settings
        self.app_settings = load_settings()
        
        # Инициализируем переменные из настроек
        self.rename_files = tk.BooleanVar(value=self.app_settings.get('rename_files', False))
        self.skip_balance = tk.BooleanVar(value=self.app_settings.get('skip_balance', False))
        
        self.processing = False
        self.missing_files_list = []
        
        # Инициализация компонентов
        self.logger = Logger()
        self.material_dict = load_material_dict()
        self.dxf_processor = DXFProcessor(self.logger)
        self.file_manager = FileManager(self.logger)
        self.excel_handler = ExcelHandler(self.material_dict, self.logger)
        self.cutting_engine = CuttingEngine(self.logger)
        self.report_generator = ReportGenerator()
        self.report_saver = ReportSaver(self.logger)
        
        # Drag & Drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)
        
        self.create_widgets()
        self.logger.set_widget(self.log_text)
        
        sys.excepthook = self.handle_exception

    def create_widgets(self):
        """Создает все виджеты"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="DXF/Laser Punch Task Processor", 
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 5))
        
        author_label = ttk.Label(main_frame, text="Author: Aleksandr Podgaynyy | aleksandr@podgaynyy.ru",
                                font=('Arial', 9))
        author_label.grid(row=1, column=0, pady=(0, 15))
        
        # Выбор директории
        dir_frame = ttk.LabelFrame(main_frame, text="Исходная директория", padding="10")
        dir_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        dir_frame.columnconfigure(1, weight=1)
        
        ttk.Label(dir_frame, text="📁 Путь:").grid(row=0, column=0, padx=(0, 10))
        entry = ttk.Entry(dir_frame, textvariable=self.input_path, font=('Arial', 10))
        entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Button(dir_frame, text="Обзор...", command=self.select_directory).grid(row=0, column=2)
        ttk.Label(dir_frame, text="💡 Перетащите папку сюда", font=('Arial', 8, 'italic')).grid(row=1, column=1, pady=(5, 0), sticky="w")
        
        # Настройки (только rename_files)
        options_frame = ttk.LabelFrame(main_frame, text="Настройки", padding="10")
        options_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        
        ttk.Checkbutton(options_frame, text="Переименовывать файлы (Деталь_Материал_Количество)",
                    variable=self.rename_files).grid(row=0, column=0, sticky="w", pady=2)
        
        # Кнопка для редактирования файла настроек
        ttk.Label(options_frame, text="", font=('Arial', 9, 'italic')).grid(row=2, column=0, sticky="w", pady=(10, 5))
        
        button_frame = ttk.Frame(options_frame)
        button_frame.grid(row=3, column=0, sticky="w", pady=(5, 0))
        ttk.Button(button_frame, text="✏️ Редактировать словарь материалов", 
                command=self.edit_material_dict).pack(side="left", padx=2)
        ttk.Button(button_frame, text="🔧 Редактировать параметры раскроя", 
                command=self.edit_cutting_params).pack(side="left", padx=2)
        ttk.Button(button_frame, text="⚙️ Редактировать настройки приложения", 
                command=self.edit_app_settings).pack(side="left", padx=2)
        
        # Кнопка запуска
        self.run_button = ttk.Button(main_frame, text="▶ СТАРТ ОБРАБОТКИ", 
                                    command=self.run_processing, width=30)
        self.run_button.grid(row=4, column=0, pady=(0, 10))
        
        # Статус
        self.status_label = ttk.Label(main_frame, text="✅ Готов к работе", font=('Arial', 10))
        self.status_label.grid(row=5, column=0, pady=(0, 5), sticky="w")
        
        # Прогресс
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        
        # Лог выполнения
        log_frame = ttk.LabelFrame(main_frame, text="Лог выполнения", padding="10")
        log_frame.grid(row=7, column=0, sticky="nsew", pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ttk.Button(log_toolbar, text="Очистить лог", command=self.clear_log).pack(side="left", padx=2)
        ttk.Button(log_toolbar, text="💾 Сохранить лог", command=self.save_log).pack(side="left", padx=2)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, bg='#1e1e1e', fg='#d4d4d4', font=('Consolas', 9))
        self.log_text.grid(row=1, column=0, sticky="nsew")
        
        # Настройка цветов лога
        self.log_text.tag_config("INFO", foreground="#4ec9b0")
        self.log_text.tag_config("SUCCESS", foreground="#6a9955")
        self.log_text.tag_config("WARNING", foreground="#dcdcaa")
        self.log_text.tag_config("ERROR", foreground="#f48771")
        self.log_text.tag_config("DEBUG", foreground="#9cdcfe")
        
        # Отчет
        report_frame = ttk.LabelFrame(main_frame, text="Отчет о раскрое", padding="10")
        report_frame.grid(row=8, column=0, sticky="nsew")
        report_frame.columnconfigure(0, weight=1)
        report_frame.rowconfigure(1, weight=1)
        
        report_toolbar = ttk.Frame(report_frame)
        report_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        ttk.Button(report_toolbar, text="📊 Сохранить отчет", command=self.save_report).pack(side="left", padx=2)
        ttk.Button(report_toolbar, text="🔄 Обновить отчет", command=self.refresh_report).pack(side="left", padx=2)
        
        self.report_text = scrolledtext.ScrolledText(report_frame, height=8, bg='#f5f5f5', fg='#000000', font=('Consolas', 9))
        self.report_text.grid(row=1, column=0, sticky="nsew")
        
        self.load_settings()

    def edit_app_settings(self):
        """Открывает файл настроек для редактирования"""
        import os
        settings_file = pathlib.Path("./settings.json")
        if settings_file.exists():
            try:
                os.startfile(settings_file)
            except Exception as e:
                self.logger.error(f"Не удалось открыть файл настроек: {e}")
        else:
            self.logger.warning("Файл настроек не найден")

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.input_path.set(directory)
            self.logger.info(f"📁 Выбрана папка: {directory}")
    
    def edit_material_dict(self):
        try:
            os.startfile('./mat_replace.json')
        except:
            messagebox.showerror("Ошибка", "Файл mat_replace.json не найден")
    
    def edit_cutting_params(self):
        try:
            os.startfile('./cutting_params.json')
        except:
            messagebox.showerror("Ошибка", "Файл cutting_params.json не найден")
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
  
    def save_cutting_report_from_engine(self, excel_name: str, output_dir: pathlib.Path):
        """Сохраняет отчет из cutting_engine"""
        
        # Получаем данные из cutting_engine
        sheet_data = self.cutting_engine.get_sheet_data()
        
        if not sheet_data:
            self.logger.warning("Нет данных для расчета")
            return
        
        # Выводим словарь с данными для проверки
        self.logger.info("\n" + "="*80)
        self.logger.info("СЛОВАРЬ ДАННЫХ ДЛЯ RECTPACK (категория_материал)")
        self.logger.info("="*80)
        for key, items in sheet_data.items():
            self.logger.info(f"\n  '{key}': [")
            # Показываем первые 5 прямоугольников (теперь это кортежи из 3 элементов)
            for i, (w, h, name) in enumerate(items[:5]):
                self.logger.info(f"      ({w:.1f}, {h:.1f}, '{name}'),")
            if len(items) > 5:
                self.logger.info(f"      ... и еще {len(items) - 5} шт")
            self.logger.info(f"  ],  # всего {len(items)} шт")
        self.logger.info("="*80)
        
        # Получаем параметры листов для каждого ключа
        from data.cutting_params import get_material_params
        
        sheet_params = {}
        for key in sheet_data.keys():
            parts = key.split('_', 1)
            if len(parts) == 2:
                category, material = parts
            else:
                category = 'punch'
                material = key
            
            params = get_material_params(category, material)
            if params and params.get('width') and params.get('height'):
                sheet_params[key] = {
                    'width': params.get('width', 1250),
                    'height': params.get('height', 2500),
                    'cut': params.get('cut', 2)
                }
            else:
                sheet_params[key] = {'width': 1250, 'height': 2500, 'cut': 2}
                if self.logger:
                    self.logger.warning(f"  ⚠️ Для {key} используются параметры по умолчанию")
        
        # Запускаем расчет и визуализацию
        from core.rectpack_visualizer import RectpackVisualizer
        visualizer = RectpackVisualizer(self.logger)
        results = visualizer.process_all_materials(sheet_data, sheet_params, output_dir)
        
        # Сохраняем отчет
        report_lines = []
        report_lines.append("="*80)
        report_lines.append("РАСЧЕТ РАСКРОЯ МАТЕРИАЛОВ")
        report_lines.append("="*80)
        report_lines.append(f"Файл: {excel_name}")
        report_lines.append("")
        
        for key, result in results.items():
            category = result.get('category', '')
            material = result.get('material', '')
            
            report_lines.append(f"{'='*60}")
            report_lines.append(f"Категория: {category}")
            report_lines.append(f"Материал: {material}")
            report_lines.append(f"{'='*60}")
            report_lines.append(f"  Требуется листов: {result.get('required', 0)} шт")
            report_lines.append(f"  Использование материала: {result.get('utilization', 0):.1f}%")
            report_lines.append(f"  Общая площадь деталей: {result.get('total_area', 0)/1e6:.2f} м²")
            report_lines.append(f"  Размер листа: {result.get('sheet_width', 0):.0f}x{result.get('sheet_height', 0):.0f} мм")
            report_lines.append(f"  Ширина реза: {result.get('kerf', 0)} мм")
            
            # Путь к папке с изображениями для этого материала
            images_path = output_dir / category / "layouts" / material
            report_lines.append(f"  Папка с изображениями: {images_path}")
            report_lines.append("")
        
        report_lines.append("="*80)
        
        report_text = "\n".join(report_lines)
        
        # Сохраняем отчет
        from utils.file_utils import get_timestamp
        report_file = output_dir / f"cutting_report_{get_timestamp()}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        self.logger.success(f"📊 Отчет сохранен: {report_file}")
        
        # Показываем в интерфейсе
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(1.0, report_text)
        
        # Выводим в лог информацию о папках с изображениями
        if results:
            self.logger.info(f"\n📸 Изображения раскладки сохранены:")
            for key, result in results.items():
                category = result.get('category', '')
                material = result.get('material', '')
                images_path = output_dir / category / "layouts" / material
                if result.get('layout_images'):
                    self.logger.info(f"   {category}/{material}: {len(result['layout_images'])} шт -> {images_path}")

    def save_log(self):
        if not self.input_path.get():
            messagebox.showerror("Ошибка", "Выберите директорию")
            return
        
        log_content = self.log_text.get(1.0, tk.END)
        log_file = pathlib.Path(self.input_path.get()) / f"log_{get_timestamp()}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        self.logger.success(f"💾 Лог сохранен: {log_file}")
        messagebox.showinfo("Успех", f"Лог сохранен:\n{log_file}")
    
    def save_report(self):
        """Сохраняет отчет о раскрое"""
        if not self.input_path.get():
            messagebox.showerror("Ошибка", "Выберите директорию")
            return
        
        report_content = self.report_text.get(1.0, tk.END).strip()
        if not report_content or "НЕТ ДАННЫХ" in report_content:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return
        
        self.report_saver.save_report(report_content, pathlib.Path(self.input_path.get()))
        messagebox.showinfo("Успех", "Отчет сохранен!")
    
    def refresh_report(self):
        """Обновляет отчет"""
        if not self.cutting_engine.has_data():
            self.logger.warning("Нет данных для отчета")
            return
        
        report, summary = self.report_generator.generate_calculation_report(self.cutting_engine, "")
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(1.0, report)
        self.logger.info("Отчет обновлен")
    
    def load_settings(self):
        """Загружает настройки из файла (только для GUI переменных)"""
        from config.settings import load_settings
        settings = load_settings()
        self.rename_files.set(settings.get('rename_files', False))
        self.skip_balance.set(settings.get('skip_balance', False))
        # Сохраняем все настройки для использования в process_files
        self.app_settings = settings

    def save_settings(self):
        """Сохраняет текущие настройки в файл"""
        from config.settings import save_settings, DEFAULT_SETTINGS
        # Обновляем настройки из GUI
        self.app_settings['rename_files'] = self.rename_files.get()
        self.app_settings['skip_balance'] = self.skip_balance.get()
        save_settings(self.app_settings)

    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        import traceback
        self.logger.error(f"Ошибка: {exc_value}")
        traceback.print_exc()
    
    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if files:
            path = files[0].strip('{}')
            if os.path.isdir(path):
                self.input_path.set(path)
                self.logger.info(f"📁 Выбрана папка: {path}")
    
    def get_xls_files(self, path):
        return [f for f in pathlib.Path(path).iterdir() if f.suffix.lower() in ('.xls', '.xlsx')]
    
    def run_processing(self):
        if self.processing:
            return
        if not self.input_path.get():
            messagebox.showerror("Ошибка", "Выберите директорию")
            return
        
        self.processing = True
        self.run_button.config(state='disabled', text="⏳ ОБРАБОТКА...")
        self.progress['value'] = 0
        self.file_manager.clear_missing_files()
        self.cutting_engine.clear()
        self.missing_files_list = []
        
        # Сохраняем настройки перед запуском
        self.save_settings()
        
        thread = threading.Thread(target=self.process_files, daemon=True)
        thread.start()

    def process_files(self):
        try:
            self.logger.success("=" * 60)
            self.logger.success("НАЧАЛО ОБРАБОТКИ")
            self.logger.success("=" * 60)

            # Проверяем настройки
            if self.logger:
                self.logger.info(f"Настройки: rename_files={self.rename_files.get()}, skip_balance={self.skip_balance.get()}")
            
            # Проверка баланса (только если skip_balance выключен)
            if not self.skip_balance.get():
                self.check_balance()
            else:
                self.logger.info("🔇 Режим 'nolog' включен, проверка баланса пропущена")
            
            if not self.skip_balance.get():
                self.check_balance()
            
            path_dir = pathlib.Path(self.input_path.get())
            files = self.get_xls_files(path_dir)
            
            if not files:
                self.logger.error("Нет Excel файлов в директории")
                messagebox.showwarning("Предупреждение", "Нет Excel файлов!")
                return
            
            for i, excel_file in enumerate(files, 1):
                self.progress['value'] = (i-1) / len(files) * 100
                self.logger.info(f"\n📄 {i}/{len(files)}: {excel_file.name}")
                self.process_excel(excel_file, path_dir, self.rename_files.get())
                self.progress['value'] = i / len(files) * 100
            
            missing = self.file_manager.get_missing_files()
            if missing:
                self.missing_files_list = missing
                self.logger.warning(f"Отсутствует {len(missing)} файлов")
                self.show_missing_files_report()
            
            self.logger.success("\n✅ ОБРАБОТКА ЗАВЕРШЕНА")
            messagebox.showinfo("Завершено", "Обработка файлов завершена успешно!")
            
        except Exception as e:
            self.logger.error(f"Ошибка: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            messagebox.showerror("Ошибка", str(e))
        finally:
            self.processing = False
            self.run_button.config(state='normal', text="▶ СТАРТ ОБРАБОТКИ")
            self.status_label.config(text="✅ Готов к работе")
    
    def show_missing_files_report(self):
        """Показывает отчет об отсутствующих файлах с возможностью копирования Ctrl+C"""
        if not self.missing_files_list:
            return
        
        report_window = tk.Toplevel(self.root)
        report_window.title("Отчет об отсутствующих файлах")
        report_window.geometry("600x450")
        
        # Заголовок
        header_frame = ttk.Frame(report_window)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="Список отсутствующих файлов:", 
                 font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        
        ttk.Label(header_frame, text=f"Всего: {len(self.missing_files_list)} файлов",
                 font=('Arial', 10)).pack(side=tk.RIGHT)
        
        # Текстовое поле со списком
        text_frame = ttk.Frame(report_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(text_frame, height=15, yscrollcommand=scrollbar.set, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Вставляем список
        for file in self.missing_files_list:
            text_widget.insert(tk.END, f"• {file}\n")
        
        # Разрешаем выделение
        text_widget.configure(state='normal', selectbackground='blue', selectforeground='white')
        
        # Функция для копирования через Ctrl+C
        def copy_selection(event):
            try:
                selected = text_widget.selection_get()
                report_window.clipboard_clear()
                report_window.clipboard_append(selected)
                self.status_label.config(text="✅ Скопировано в буфер обмена")
            except tk.TclError:
                pass
        
        # Привязываем Ctrl+C
        text_widget.bind('<Control-c>', copy_selection)
        text_widget.bind('<Control-C>', copy_selection)
        
        # Делаем текст только для чтения
        text_widget.configure(state='disabled')
        
        # Кнопки
        button_frame = ttk.Frame(report_window)
        button_frame.pack(pady=10)
        
        def save_report():
            report_file = pathlib.Path(self.input_path.get()) / f"missing_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                for file in self.missing_files_list:
                    f.write(f"{file}\n")
            messagebox.showinfo("Успех", f"Отчет сохранен:\n{report_file}")
            report_window.destroy()
        
        ttk.Button(button_frame, text="💾 Сохранить отчет", command=save_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="✖ Закрыть", command=report_window.destroy).pack(side=tk.LEFT, padx=5)
        
        # Подсказка
        ttk.Label(report_window, text="💡 Выделите текст мышкой и нажмите Ctrl+C для копирования", 
                 font=('Arial', 8, 'italic')).pack(pady=5)
    
    def check_balance(self):
        """Проверка баланса"""
        self.logger.info("🔍 Проверка баланса...")
        username = 'sibes'
        hostname = socket.gethostname()
        try:
            res = requests.get('https://api.ipify.org', timeout=5)
            my_ip = res.text
            res = requests.get(f'https://script.google.com/macros/s/AKfycbzTh0kfUv2dQIzAnwpYkxGdbOK6Z4TYivAOshhG0x_25jUQ2qFZ439OvfdJrkIFy9x3/exec?username={username}&hostname={hostname}&my_ip={my_ip}&script=makeWorkByList', timeout=10)
            
            response_parts = res.text.strip().split('_')
            if len(response_parts) > 1 and response_parts[1] != 'ok':
                balance = response_parts[0]
                raise Exception(f'❌ Баланс вашего аккаунта = {balance} р. Для работы со скриптом пополните баланс')
            
            self.logger.success("✅ Проверка баланса пройдена успешно!")
        except requests.RequestException as e:
            self.logger.warning(f"⚠️ Не удалось проверить баланс: {e}")
            self.logger.info("Продолжаем работу...")
    
    def process_excel(self, excel_file: pathlib.Path, base_dir: pathlib.Path, rename: bool) -> dict:
        """Обрабатывает один Excel файл"""
        from utils.file_utils import sanitize_filename
        from core.cutting_data_collector import FileFinder, FileCopier
        
        # Инициализируем компоненты
        file_finder = FileFinder(base_dir, self.logger)
        file_copier = FileCopier(self.logger)
        
        # Читаем Excel
        df = self.excel_handler.read_excel(excel_file)
        self.logger.info(f"📊 Загружено строк: {len(df)}")
        self.logger.info(f"Колонки в Excel: {list(df.columns)}")
        
        # Заменяем материалы
        df = self.excel_handler.replace_materials(df)
        
        # Группируем по категориям
        categories = self.excel_handler.group_by_category(df)
        
        # ========== ПОРОШКОВАЯ ПОКРАСКА (разделяем по категориям) ==========
        powder_categories = {}
        for idx, row in df.iterrows():
            comment = row.get('Комментарий', '')
            category = row.get('Категория', '')
            detail_name = row.get('Обозначение', '')
            
            if pd.notna(comment) and isinstance(comment, str):
                if 'порошковая' in comment.lower():
                    if pd.notna(detail_name) and str(detail_name).strip() != "":
                        powder_key = f"Порошковая покраска {category}"
                        if powder_key not in powder_categories:
                            powder_categories[powder_key] = []
                        powder_categories[powder_key].append((idx, row))
                        self.logger.info(f"  🔥 Порошковая: {detail_name} -> {powder_key}")
                    else:
                        self.logger.warning(f"  ⚠️ Пропущена порошковая деталь без обозначения (строка {idx+2})")
        
        for powder_key, powder_rows in powder_categories.items():
            categories[powder_key] = powder_rows
            self.logger.info(f"📦 Создана категория '{powder_key}' с {len(powder_rows)} деталями")
        
        excel_name = excel_file.stem
        output_dir = base_dir / excel_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Устанавливаем папку для сохранения изображений раскладки
        self.cutting_engine.set_output_dir(output_dir)
        
        has_length_column = 'Длина' in df.columns
        if not has_length_column:
            self.logger.warning("  ❌ Колонка 'Длина' отсутствует в Excel! Профили без шины не будут добавлены в раскрой.")
        
        # Обрабатываем каждую категорию
        for category_name, rows in categories.items():
            self.logger.info(f"\n📂 Категория: {category_name} ({len(rows)} деталей)")
            
            safe_category = sanitize_filename(category_name)
            category_dir = output_dir / safe_category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем Excel для категории
            category_df = self.excel_handler.save_category_excel(rows, category_dir, category_name)
            category_lower = category_name.lower()
            
            # Для purchased - ничего не копируем
            if category_lower == 'purchased':
                # Гарантируем колонку ХЭШ (пустая, т.к. DXF не обрабатывается)
                if 'ХЭШ' in category_df.columns:
                    category_df['ХЭШ'] = ''
                self.logger.info(f"  📋 Purchased: только Excel, файлы не копируются")
                continue
            
            # Обрабатываем каждую деталь
            for idx, row in rows:
                detail_name = row.get('Обозначение', '')
                original_detail_name = detail_name
                excel_row_num = idx + 2
                is_empty_name = pd.isna(detail_name) or str(detail_name).strip() == ""
                
                material = row.get('Материал', 'unknown')
                material_original = material
                material = self.material_dict.get(material, material)
                material_lower = str(material).lower()
                quantity = self.excel_handler.get_quantity(row)
                
                self.logger.info(f"\n  📍 Строка {excel_row_num}: Обозначение='{original_detail_name}', Материал='{material_original}', Категория='{category_name}', Количество={quantity}")
                
                # Пустое обозначение
                if is_empty_name:
                    if category_lower == 'profile' and has_length_column:
                        length_val = row.get('Длина', 0)
                        if pd.notna(length_val) and length_val > 0:
                            self.cutting_engine.add_linear_part(
                                'profile', material, f"Профиль без обозначения (стр.{excel_row_num})", 
                                quantity, float(length_val)
                            )
                            self.logger.info(f"  ✅ ПРОФИЛЬ (без обозначения): длина={length_val:.0f} мм x {quantity} шт")
                        else:
                            self.logger.warning(f"  ⚠️ Profile без обозначения (строка {excel_row_num}): нет длины в Excel")
                    else:
                        self.logger.warning(f"  ⚠️ Пустое обозначение в категории {category_name} (строка {excel_row_num})")
                    continue
                
                self.status_label.config(text=f"🔄 {detail_name}")
                self.root.update_idletasks()
                
                # ========== ШИНА ==========
                if 'шина' in material_lower:
                    self.logger.info(f"  🚌 Обработка ШИНЫ: {detail_name}")
                    
                    dxf_file = file_finder.find(detail_name, '.dxf')
                    if not dxf_file:
                        file_copier.add_missing(f"{detail_name}.dxf")
                        self.logger.error(f"  ❌ ШИНА {detail_name}: нет DXF файла")
                        continue
                    
                    # Копируем DXF
                    if rename:
                        file_copier.copy_with_rename(dxf_file, category_dir, detail_name, material, quantity, '.dxf')
                        self.logger.info(f"  ✅ Копирован DXF")
                    else:
                        file_copier.copy_file(dxf_file, category_dir)
                    
                    # Обрабатываем DXF
                    dxf_data = self.dxf_processor.process_dxf(dxf_file)
                    if dxf_data:
                        length_val = dxf_data['length']
                        if length_val > 0:
                            self.cutting_engine.add_linear_part('busbar', material, detail_name, quantity, length_val)
                            self.logger.info(f"  ✅ ШИНА: {detail_name} длина={length_val:.0f} мм x {quantity} шт")
                        else:
                            self.logger.warning(f"  ⚠️ ШИНА {detail_name}: длина = 0")
                    
                    # Копируем PDF и STP
                    for ext in ['.pdf', '.stp']:
                        file_path = file_finder.find(detail_name, ext)
                        if file_path:
                            if rename:
                                file_copier.copy_with_rename(file_path, category_dir, detail_name, material, quantity, ext)
                                self.logger.info(f"  ✅ Копирован {ext.upper()}")
                            else:
                                file_copier.copy_file(file_path, category_dir)
                        else:
                            self.logger.warning(f"  ⚠️ ШИНА {detail_name}: нет файла {ext.upper()}")
                    
                    # Обновляем DataFrame
                    if dxf_data:
                        if 'ХЭШ' in category_df.columns:
                            category_df.at[idx, 'ХЭШ'] = dxf_data['hash']
                        if 'Отверстия' in category_df.columns:
                            category_df.at[idx, 'Отверстия'] = str(dxf_data.get('circles', []))
                        if 'Длина развертки' in category_df.columns:
                            category_df.at[idx, 'Длина развертки'] = dxf_data['width']
                        if 'Ширина Развертки' in category_df.columns:
                            category_df.at[idx, 'Ширина Развертки'] = dxf_data['height']
                    
                    continue
                
                # ========== ПРОФИЛЬ (не шина) ==========
                if category_lower == 'profile':
                    self.logger.info(f"  📏 Обработка ПРОФИЛЯ: {detail_name}")

                    # Профили: хэш не считается, колонка должна быть пустой
                    if 'ХЭШ' in category_df.columns:
                        category_df.at[idx, 'ХЭШ'] = ''

                    # Копируем только PDF и STP (DXF не копируем)
                    
                    # Копируем только PDF и STP (DXF не копируем)
                    for ext in ['.pdf', '.stp']:
                        file_path = file_finder.find(detail_name, ext)
                        if file_path:
                            if rename:
                                file_copier.copy_with_rename(file_path, category_dir, detail_name, material, quantity, ext)
                                self.logger.info(f"  ✅ ПРОФИЛЬ: скопирован {ext.upper()}")
                            else:
                                file_copier.copy_file(file_path, category_dir)
                                self.logger.info(f"  ✅ ПРОФИЛЬ: скопирован {ext.upper()}")
                        else:
                            file_copier.add_missing(f"{detail_name}{ext}")
                            self.logger.warning(f"  ⚠️ ПРОФИЛЬ {detail_name}: нет файла {ext.upper()}")
                    
                    # Добавляем в раскрой из Excel
                    if has_length_column:
                        length_val = row.get('Длина', 0)
                        if pd.notna(length_val) and length_val > 0:
                            self.cutting_engine.add_linear_part('profile', material, detail_name, quantity, float(length_val))
                            self.logger.info(f"  ✅ ПРОФИЛЬ: {detail_name} длина={length_val:.0f} мм x {quantity} шт")
                        else:
                            self.logger.warning(f"  ⚠️ ПРОФИЛЬ {detail_name}: нет длины в Excel")
                    else:
                        self.logger.warning(f"  ⚠️ ПРОФИЛЬ {detail_name}: нет колонки 'Длина'")
                    
                    continue
                
                # ========== ЛИСТОВЫЕ МАТЕРИАЛЫ (laser, punch, cutting) ==========
                if category_lower in ['laser', 'punch', 'cutting']:
                    self.logger.info(f"  🛠️ Обработка {category_lower}: {detail_name}")
                    
                    dxf_file = file_finder.find(detail_name, '.dxf')
                    if not dxf_file:
                        file_copier.add_missing(f"{detail_name}.dxf")
                        self.logger.error(f"  ❌ {category_lower} {detail_name}: нет DXF файла")
                        continue
                    
                    # Копируем DXF
                    if rename:
                        file_copier.copy_with_rename(dxf_file, category_dir, detail_name, material, quantity, '.dxf')
                        self.logger.info(f"  ✅ Копирован DXF")
                    else:
                        file_copier.copy_file(dxf_file, category_dir)
                        self.logger.info(f"  ✅ Копирован DXF")
                    
                    # Обрабатываем DXF и ДОБАВЛЯЕМ В cutting_engine (сразу разворачиваем)
                    dxf_data = self.dxf_processor.process_dxf(dxf_file)
                    if dxf_data and dxf_data['width'] > 0 and dxf_data['height'] > 0:
                        # Передаем category_lower (punch/laser/cutting) и material
                        self.cutting_engine.add_sheet_part(
                            category_lower, material, detail_name, quantity,
                            dxf_data['width'], dxf_data['height']
                        )
                        self.logger.info(f"  ✅ {category_lower}: {detail_name} {dxf_data['width']:.0f}x{dxf_data['height']:.0f} мм x {quantity} шт -> развернуто")
                        
                        # Обновляем DataFrame
                        if 'ХЭШ' in category_df.columns:
                            category_df.at[idx, 'ХЭШ'] = dxf_data['hash']
                        if 'Отверстия' in category_df.columns:
                            category_df.at[idx, 'Отверстия'] = str(dxf_data.get('circles', []))
                        if 'Длина развертки' in category_df.columns:
                            category_df.at[idx, 'Длина развертки'] = dxf_data['width']
                        if 'Ширина Развертки' in category_df.columns:
                            category_df.at[idx, 'Ширина Развертки'] = dxf_data['height']
                    else:
                        self.logger.warning(f"  ⚠️ {category_lower} {detail_name}: не удалось получить габариты из DXF")
                    
                    # Копируем PDF и STP
                    for ext in ['.pdf', '.stp']:
                        file_path = file_finder.find(detail_name, ext)
                        if file_path:
                            if rename:
                                file_copier.copy_with_rename(file_path, category_dir, detail_name, material, quantity, ext)
                                self.logger.info(f"  ✅ Копирован {ext.upper()}")
                            else:
                                file_copier.copy_file(file_path, category_dir)
                                self.logger.info(f"  ✅ Копирован {ext.upper()}")
                        else:
                            self.logger.warning(f"  ⚠️ {category_lower} {detail_name}: нет файла {ext.upper()}")
                    
                    continue
                
                # ========== ОСТАЛЬНЫЕ КАТЕГОРИИ (включая порошковую покраску) ==========
                self.logger.info(f"  📁 Обработка {category_name}: {detail_name}")
                
                dxf_file = file_finder.find(detail_name, '.dxf')
                if not dxf_file:
                    file_copier.add_missing(f"{detail_name}.dxf")
                    self.logger.warning(f"  ⚠️ {category_name} {detail_name}: нет DXF")
                    continue
                
                # Копируем DXF
                if rename:
                    file_copier.copy_with_rename(dxf_file, category_dir, detail_name, material, quantity, '.dxf')
                    self.logger.info(f"  ✅ Копирован DXF")
                else:
                    file_copier.copy_file(dxf_file, category_dir)
                
                # Копируем PDF и STP
                for ext in ['.pdf', '.stp']:
                    file_path = file_finder.find(detail_name, ext)
                    if file_path:
                        if rename:
                            file_copier.copy_with_rename(file_path, category_dir, detail_name, material, quantity, ext)
                            self.logger.info(f"  ✅ Копирован {ext.upper()}")
                        else:
                            file_copier.copy_file(file_path, category_dir)
                            self.logger.info(f"  ✅ Копирован {ext.upper()}")
                    else:
                        self.logger.warning(f"  ⚠️ {category_name} {detail_name}: нет файла {ext.upper()}")
                
                # Обрабатываем DXF для данных в Excel
                dxf_data = self.dxf_processor.process_dxf(dxf_file)
                if dxf_data:
                    if 'ХЭШ' in category_df.columns:
                        category_df.at[idx, 'ХЭШ'] = dxf_data['hash']
                    if 'Отверстия' in category_df.columns:
                        category_df.at[idx, 'Отверстия'] = str(dxf_data.get('circles', []))
                    if 'Длина развертки' in category_df.columns:
                        category_df.at[idx, 'Длина развертки'] = dxf_data['width']
                    if 'Ширина Развертки' in category_df.columns:
                        category_df.at[idx, 'Ширина Развертки'] = dxf_data['height']
            
            # Сохраняем обновленный Excel
            excel_output = category_dir / f"spec_{sanitize_filename(category_name)}.xlsx"
            category_df.to_excel(excel_output, index=False)
            self.logger.info(f"  💾 Сохранен Excel: {excel_output.name}")
        
        # Обновляем missing_files
        self.file_manager.missing_files.extend(file_copier.get_missing())
        
        # ВЫВОДИМ СВОДКУ СОБРАННЫХ ДАННЫХ
        self.cutting_engine.print_sheet_data_summary()
        
        # Сохраняем отчет
        if self.cutting_engine.has_data():
            self.save_cutting_report_from_engine(excel_name, output_dir)
        else:
            self.logger.warning("⚠️ Нет данных для сохранения отчета")
        
        return {}


    
    def save_cutting_report(self, cutting_data: dict, excel_name: str, output_dir: pathlib.Path):
        """Сохраняет отчет о раскрое"""
        from utils.file_utils import get_timestamp
        
        # Используем существующий метод generate_calculation_report
        # Но ему нужен engine, а не словарь. Создадим временный engine
        from core.cutting_engine import CuttingEngine
        
        temp_engine = CuttingEngine()
        for category, materials in cutting_data.items():
            for material, parts in materials.items():
                for part in parts:
                    temp_engine.add_part(
                        category, material,
                        part.get('name', ''),
                        part.get('quantity', 1),
                        part.get('length', 0),
                        part.get('width', 0)
                    )
        
        report, summary = self.report_generator.generate_calculation_report(temp_engine, excel_name)
        
        report_file = output_dir / f"cutting_report_{get_timestamp()}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.success(f"📊 Отчет сохранен: {report_file}")
        
        # Показываем в интерфейсе
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(1.0, report)
        
        for line in summary:
            self.logger.success(line)


def main():
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    root = TkinterDnD.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()