# blog/services/markdown_processor.py
"""Главный процессор для обработки HTML через систему процессоров.

Координирует выполнение всех зарегистрированных HTML-процессоров
последовательно.
"""

from typing import Sequence
from bs4 import BeautifulSoup

from blog.services.html_processor import HTMLProcessor


class MarkdownProcessor:
    """Главный процессор для конвертации Markdown → HTML с обработкой.

    Координирует работу всех HTML-процессоров (Beautiful Soup):
    1. Парсит HTML в объект BeautifulSoup
    2. Последовательно применяет все процессоры
    3. Возвращает модифицированный HTML

    Attributes:
        processors: Список зарегистрированных процессоров.

    Example:
        >>> from blog.services.markdown_processor import MarkdownProcessor
        >>> from blog.services.processors import TableProcessor
        >>>
        >>> processors = [TableProcessor()]
        >>> processor = MarkdownProcessor(processors)
        >>> html = '<table><tr><td>Cell</td></tr></table>'
        >>> result = processor.process_html(html)
        >>> 'class="table' in result
        True
    """

    def __init__(self, processors: Sequence[HTMLProcessor]) -> None:
        """Инициализирует процессор с набором обработчиков.

        Args:
            processors: Список процессоров для применения к HTML.

        Note:
            Порядок процессоров важен! Они выполняются последовательно
            в том порядке, в котором переданы.
        """
        self.processors = processors

    def process_html(self, html: str) -> str:
        """Обрабатывает HTML всеми зарегистрированными процессорами.

        Args:
            html: HTML строка для обработки.

        Returns:
            Обработанная HTML строка с добавленными классами и атрибутами.

        Raises:
            Exception: В случае ошибки возвращается оригинальный HTML.

        Note:
            Использует Beautiful Soup parser 'html.parser' (встроенный).
            Процессоры модифицируют soup in-place.
        """
        if not html:
            return ""

        try:
            # Парсим HTML в BeautifulSoup объект
            soup = BeautifulSoup(html, "html.parser")

            # Применяем все процессоры последовательно
            for processor in self.processors:
                try:
                    processor.process(soup)
                except Exception as e:
                    # Логируем ошибку процессора, но продолжаем работу
                    print(f"⚠️ Ошибка в {processor.get_name()}: {e}")
                    continue

            # Возвращаем модифицированный HTML
            return str(soup)

        except Exception as e:
            # В случае критической ошибки возвращаем оригинальный HTML
            print(f"❌ Критическая ошибка MarkdownProcessor: {e}")
            return html
