"""
Логирование сообщений в GUI и консоль
"""

from datetime import datetime
from typing import Optional


class Logger:
    """
    Класс для логирования сообщений
    """
    
    def __init__(self, log_widget=None):
        """
        Args:
            log_widget: Виджет tkinter для вывода логов
        """
        self.log_widget = log_widget
        self.logs = []  # Хранит все сообщения
        
    def set_widget(self, log_widget):
        """Устанавливает виджет для вывода логов"""
        self.log_widget = log_widget
    
    def log(self, message: str, level: str = "INFO"):
        """
        Выводит сообщение в лог
        
        Args:
            message: Текст сообщения
            level: Уровень (INFO, SUCCESS, WARNING, ERROR, DEBUG)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        
        # Сохраняем в список
        self.logs.append(formatted)
        
        # Выводим в виджет, если он есть
        if self.log_widget:
            tag = level
            self.log_widget.insert("end", formatted + "\n", tag)
            self.log_widget.see("end")
        
        # Выводим в консоль
        print(formatted)
    
    def info(self, message: str):
        self.log(message, "INFO")
    
    def success(self, message: str):
        self.log(message, "SUCCESS")
    
    def warning(self, message: str):
        self.log(message, "WARNING")
    
    def error(self, message: str):
        self.log(message, "ERROR")
    
    def debug(self, message: str):
        self.log(message, "DEBUG")
    
    def get_logs(self) -> list:
        """Возвращает все сохраненные логи"""
        return self.logs
    
    def clear(self):
        """Очищает логи"""
        self.logs = []
        if self.log_widget:
            self.log_widget.delete("1.0", "end")