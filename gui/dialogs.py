"""
Диалоговые окна для GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pathlib


class MissingFilesDialog:
    """
    Диалоговое окно со списком отсутствующих файлов
    """
    
    @staticmethod
    def show(parent, missing_files: list, output_dir: str = None):
        """
        Показывает диалог с отсутствующими файлами
        
        Args:
            parent: Родительское окно
            missing_files: Список отсутствующих файлов
            output_dir: Папка для сохранения отчета
        """
        if not missing_files:
            messagebox.showinfo("Информация", "Все файлы найдены!")
            return
        
        dialog = tk.Toplevel(parent)
        dialog.title("Отсутствующие файлы")
        dialog.geometry("600x400")
        dialog.transient(parent)
        dialog.grab_set()
        
        # Заголовок
        ttk.Label(dialog, text=f"Отсутствует {len(missing_files)} файлов:", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Список
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, height=15)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        for file in missing_files:
            text_widget.insert(tk.END, f"• {file}\n")
        
        text_widget.configure(state='disabled')
        
        # Кнопки
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def save_report():
            if output_dir:
                import json
                from datetime import datetime
                
                report_file = pathlib.Path(output_dir) / f"missing_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
                    for file in missing_files:
                        f.write(f"{file}\n")
                
                messagebox.showinfo("Успех", f"Отчет сохранен:\n{report_file}")
                dialog.destroy()
        
        ttk.Button(button_frame, text="Сохранить отчет", command=save_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=5)


class ProgressDialog:
    """
    Диалоговое окно с прогрессом обработки
    """
    
    def __init__(self, parent, title="Обработка"):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрируем
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 75
        self.dialog.geometry(f"+{x}+{y}")
        
        # Виджеты
        self.label = ttk.Label(self.dialog, text="Обработка файлов...")
        self.label.pack(pady=20)
        
        self.progress = ttk.Progressbar(self.dialog, mode='determinate', length=300)
        self.progress.pack(pady=10)
        
        self.percent_label = ttk.Label(self.dialog, text="0%")
        self.percent_label.pack()
        
        self.cancelled = False
    
    def update(self, value: float, text: str = None):
        """
        Обновляет прогресс
        """
        self.progress['value'] = value
        self.percent_label.config(text=f"{int(value)}%")
        if text:
            self.label.config(text=text)
        self.dialog.update_idletasks()
    
    def close(self):
        """Закрывает диалог"""
        self.dialog.destroy()
    
    def is_cancelled(self) -> bool:
        """Проверяет, была ли отмена"""
        return self.cancelled


class SettingsDialog:
    """
    Диалог настроек приложения
    """
    
    def __init__(self, parent, settings: dict):
        self.parent = parent
        self.settings = settings.copy()
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Настройки")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
    
    def create_widgets(self):
        """Создает виджеты настроек"""
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка "Общие"
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="Общие")
        
        ttk.Label(general_frame, text="Настройки обработки:").pack(anchor="w", pady=5)
        
        self.rename_var = tk.BooleanVar(value=self.settings.get('rename_files', True))
        ttk.Checkbutton(general_frame, text="Переименовывать файлы", 
                       variable=self.rename_var).pack(anchor="w", pady=2)
        
        self.nolog_var = tk.BooleanVar(value=self.settings.get('skip_balance', False))
        ttk.Checkbutton(general_frame, text="Режим nolog (пропустить проверку баланса)",
                       variable=self.nolog_var).pack(anchor="w", pady=2)
        
        # Вкладка "Параметры раскроя"
        cutting_frame = ttk.Frame(notebook)
        notebook.add(cutting_frame, text="Параметры раскроя")
        
        # Профиль
        profile_frame = ttk.LabelFrame(cutting_frame, text="Профиль", padding="5")
        profile_frame.pack(fill="x", pady=5)
        
        ttk.Label(profile_frame, text="Длина заготовки (мм):").grid(row=0, column=0, padx=5)
        self.profile_length = tk.StringVar(value=str(self.settings.get('profile_length', 6000)))
        ttk.Entry(profile_frame, textvariable=self.profile_length, width=10).grid(row=0, column=1)
        
        ttk.Label(profile_frame, text="Ширина реза (мм):").grid(row=1, column=0, padx=5)
        self.profile_cut = tk.StringVar(value=str(self.settings.get('profile_cut', 10)))
        ttk.Entry(profile_frame, textvariable=self.profile_cut, width=10).grid(row=1, column=1)
        
        # Листовые материалы
        sheet_frame = ttk.LabelFrame(cutting_frame, text="Листовые материалы", padding="5")
        sheet_frame.pack(fill="x", pady=5)
        
        ttk.Label(sheet_frame, text="Размер листа (мм):").grid(row=0, column=0, padx=5)
        self.sheet_size = tk.StringVar(value=self.settings.get('sheet_size', '1250x2500'))
        ttk.Entry(sheet_frame, textvariable=self.sheet_size, width=15).grid(row=0, column=1)
        
        ttk.Label(sheet_frame, text="Ширина реза (мм):").grid(row=1, column=0, padx=5)
        self.sheet_cut = tk.StringVar(value=str(self.settings.get('sheet_cut', 2)))
        ttk.Entry(sheet_frame, textvariable=self.sheet_cut, width=10).grid(row=1, column=1)
        
        # Кнопки
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Сохранить", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.cancel).pack(side=tk.LEFT, padx=5)
    
    def save(self):
        """Сохраняет настройки"""
        self.result = {
            'rename_files': self.rename_var.get(),
            'skip_balance': self.nolog_var.get(),
            'profile_length': int(self.profile_length.get()),
            'profile_cut': int(self.profile_cut.get()),
            'sheet_size': self.sheet_size.get(),
            'sheet_cut': int(self.sheet_cut.get())
        }
        self.dialog.destroy()
    
    def cancel(self):
        """Отменяет изменения"""
        self.result = None
        self.dialog.destroy()
    
    def get_result(self):
        """Возвращает результат"""
        return self.result


class AboutDialog:
    """
    Диалог "О программе"
    """
    
    @staticmethod
    def show(parent):
        dialog = tk.Toplevel(parent)
        dialog.title("О программе")
        dialog.geometry("400x250")
        dialog.transient(parent)
        dialog.grab_set()
        
        # Центрируем
        dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 125
        dialog.geometry(f"+{x}+{y}")
        
        # Содержание
        ttk.Label(dialog, text="DXF/Laser Punch Task Processor", 
                 font=('Arial', 14, 'bold')).pack(pady=20)
        
        ttk.Label(dialog, text="Версия: 2.0").pack()
        ttk.Label(dialog, text="Author: Aleksandr Podgaynyy").pack()
        ttk.Label(dialog, text="Email: aleksandr@podgaynyy.ru").pack()
        ttk.Label(dialog, text="").pack()
        
        frame = ttk.Frame(dialog)
        frame.pack(pady=20)
        ttk.Button(frame, text="OK", command=dialog.destroy).pack()