"""
Пользовательские виджеты для GUI
"""

import tkinter as tk
from tkinter import ttk, scrolledtext


class LogTextWidget(scrolledtext.ScrolledText):
    """
    Виджет для вывода логов с поддержкой цветов
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Настройка цветовых тегов
        self.tag_config("INFO", foreground="#4ec9b0")
        self.tag_config("SUCCESS", foreground="#6a9955")
        self.tag_config("WARNING", foreground="#dcdcaa")
        self.tag_config("ERROR", foreground="#f48771")
        self.tag_config("DEBUG", foreground="#9cdcfe")
    
    def append(self, text: str, tag: str = "INFO"):
        """
        Добавляет текст с указанным тегом
        """
        self.insert("end", text, tag)
        self.see("end")
        self.update_idletasks()
    
    def clear(self):
        """Очищает виджет"""
        self.delete("1.0", "end")


class ReportTextWidget(scrolledtext.ScrolledText):
    """
    Виджет для отображения отчетов
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg='#f5f5f5', fg='#000000', font=('Consolas', 9))
    
    def set_report(self, text: str):
        """
        Устанавливает текст отчета
        """
        self.delete("1.0", "end")
        self.insert("1.0", text)
    
    def clear(self):
        """Очищает виджет"""
        self.delete("1.0", "end")


class ProgressBarWithLabel(ttk.Frame):
    """
    Прогресс-бар с подписью
    """
    
    def __init__(self, parent, text="Прогресс:", **kwargs):
        super().__init__(parent)
        
        self.label = ttk.Label(self, text=text)
        self.label.pack(side="left", padx=(0, 10))
        
        self.progress = ttk.Progressbar(self, **kwargs)
        self.progress.pack(side="left", fill="x", expand=True)
        
        self.percent_label = ttk.Label(self, text="0%", width=5)
        self.percent_label.pack(side="left", padx=(10, 0))
    
    def set_value(self, value: float):
        """
        Устанавливает значение прогресса (0-100)
        """
        self.progress['value'] = value
        self.percent_label.config(text=f"{int(value)}%")
        self.update_idletasks()
    
    def start(self):
        """Запускает анимированный прогресс"""
        self.progress.start()
    
    def stop(self):
        """Останавливает прогресс"""
        self.progress.stop()
    
    def reset(self):
        """Сбрасывает прогресс"""
        self.set_value(0)


class DirectorySelector(ttk.Frame):
    """
    Виджет выбора директории
    """
    
    def __init__(self, parent, label_text="Путь к директории:", 
                 button_text="Обзор...", hint_text="💡 Перетащите папку сюда",
                 path_variable=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.path_variable = path_variable or tk.StringVar()
        
        # Метка
        self.label = ttk.Label(self, text=label_text)
        self.label.grid(row=0, column=0, padx=(0, 10), sticky="w")
        
        # Поле ввода
        self.entry = ttk.Entry(self, textvariable=self.path_variable)
        self.entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        
        # Кнопка
        self.button = ttk.Button(self, text=button_text, command=self.browse)
        self.button.grid(row=0, column=2)
        
        # Подсказка
        self.hint_label = ttk.Label(self, text=hint_text, font=('Arial', 8, 'italic'))
        self.hint_label.grid(row=1, column=1, pady=(5, 0), sticky="w")
        
        self.columnconfigure(1, weight=1)
    
    def browse(self):
        """Открывает диалог выбора папки"""
        from tkinter import filedialog
        directory = filedialog.askdirectory(title="Выберите директорию")
        if directory:
            self.path_variable.set(directory)
    
    def get_path(self) -> str:
        """Возвращает выбранный путь"""
        return self.path_variable.get()
    
    def set_path(self, path: str):
        """Устанавливает путь"""
        self.path_variable.set(path)


class CheckboxGroup(ttk.LabelFrame):
    """
    Группа чекбоксов
    """
    
    def __init__(self, parent, title="Опции", **kwargs):
        super().__init__(parent, text=title, **kwargs)
        
        self.checkboxes = {}
        self.variables = {}
    
    def add_checkbox(self, text: str, variable=None, default: bool = False):
        """
        Добавляет чекбокс в группу
        
        Args:
            text: Текст чекбокса
            variable: Переменная tk.BooleanVar (создается если None)
            default: Значение по умолчанию
            
        Returns:
            Переменная чекбокса
        """
        var = variable or tk.BooleanVar(value=default)
        cb = ttk.Checkbutton(self, text=text, variable=var)
        cb.pack(anchor="w", pady=2)
        
        self.checkboxes[text] = cb
        self.variables[text] = var
        
        return var
    
    def get_value(self, text: str) -> bool:
        """Возвращает значение чекбокса"""
        if text in self.variables:
            return self.variables[text].get()
        return False
    
    def set_value(self, text: str, value: bool):
        """Устанавливает значение чекбокса"""
        if text in self.variables:
            self.variables[text].set(value)
    
    def get_all_values(self) -> dict:
        """Возвращает все значения"""
        return {text: var.get() for text, var in self.variables.items()}