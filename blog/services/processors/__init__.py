# blog/services/processors/__init__.py
"""Пакет HTML-процессоров для Beautiful Soup обработки.

Экспортирует все доступные процессоры для обработки HTML элементов.

Доступные процессоры:
    - TableProcessor: Добавляет Bootstrap классы к таблицам
    - ImageProcessor: (TODO Phase 2.6) Добавляет .img-fluid к изображениям
    - BlockquoteProcessor: (TODO Phase 2.6) Обрабатывает цитаты и Obsidian Callouts
    - CodeProcessor: (TODO Phase 2.6) Стилизация inline кода

Использование:
    >>> from blog.services.processors import TableProcessor
    >>> processor = TableProcessor()
"""

from blog.services.processors.table_processor import TableProcessor

__all__ = [
    "TableProcessor",
    # "ImageProcessor",  # TODO: Phase 2.6
    # "BlockquoteProcessor",  # TODO: Phase 2.6
    # "CodeProcessor",  # TODO: Phase 2.6
]
