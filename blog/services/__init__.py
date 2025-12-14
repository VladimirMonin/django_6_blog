# blog/services/__init__.py
"""Пакет сервисов для работы с контентом блога.

Основные компоненты:
    - convert_markdown_to_html: Главная функция конвертации Markdown → HTML
    - MarkdownProcessor: Координатор HTML-процессоров
    - HTMLProcessor: Базовый класс для процессоров
    - processors: Пакет со всеми процессорами (Table, Image, Blockquote, Code)

Архитектура:
    Markdown → HTML (markdown lib) → HTML Processing (Beautiful Soup) → Output

Использование:
    >>> from blog.services import convert_markdown_to_html
    >>> html = convert_markdown_to_html("# Hello World")
    >>> '<h1>Hello World</h1>' in html
    True
"""

from blog.services.markdown_converter import convert_markdown_to_html

__all__ = ["convert_markdown_to_html"]
