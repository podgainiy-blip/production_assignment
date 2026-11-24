"""
Точка входа в приложение
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import main


if __name__ == "__main__":
    main()


# pyinstaller dxf_processor.spec