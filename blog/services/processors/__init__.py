# blog/services/processors/__init__.py
"""Пакет HTML-процессоров для Beautiful Soup обработки.

Экспортирует все доступные процессоры для обработки HTML элементов.

Доступные процессоры:
    - TableProcessor: Добавляет Bootstrap классы к таблицам
    - ImageProcessor: Добавляет .img-fluid, .d-block, .mx-auto к изображениям
    - BlockquoteProcessor: Обрабатывает цитаты и Obsidian Callouts
    - CodeProcessor: Стилизация inline кода

Использование:
    >>> from blog.services.processors import TableProcessor, ImageProcessor
    >>> table_proc = TableProcessor()
    >>> image_proc = ImageProcessor()
"""

from blog.services.processors.blockquote_processor import BlockquoteProcessor
from blog.services.processors.code_processor import CodeProcessor
from blog.services.processors.image_processor import ImageProcessor
from blog.services.processors.table_processor import TableProcessor

__all__ = [
    "TableProcessor",
    "ImageProcessor",
    "BlockquoteProcessor",
    "CodeProcessor",
]
