# blog/services/processors/code_processor.py
"""Процессор для стилизации inline-кода.

Обрабатывает <code> элементы, которые НЕ находятся внутри <pre>.
Code blocks (<pre><code>) обрабатываются Highlight.js на фронтенде.
"""

from bs4 import BeautifulSoup

from blog.services.html_processor import HTMLProcessor


class CodeProcessor(HTMLProcessor):
    """Процессор для добавления Bootstrap классов к inline-коду.

    Обрабатывает только <code> элементы вне <pre> блоков.
    Добавляет Bootstrap utility классы для визуального выделения:
    - text-danger: красный цвет текста
    - bg-light: светлый фон
    - px-1: padding по горизонтали (0.25rem)

    Code blocks (<pre><code>) не трогаем — они обрабатываются Highlight.js.

    Bootstrap 5 Text Color Docs:
        https://getbootstrap.com/docs/5.3/utilities/colors/

    Bootstrap 5 Background Docs:
        https://getbootstrap.com/docs/5.3/utilities/background/

    Example:
        >>> from bs4 import BeautifulSoup
        >>> from blog.services.processors.code_processor import CodeProcessor
        >>>
        >>> # Inline-код (должен обработаться)
        >>> html = '<p>Используйте <code>convert_markdown_to_html()</code> функцию.</p>'
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> processor = CodeProcessor()
        >>> processor.process(soup)
        >>> 'class="text-danger bg-light px-1"' in str(soup)
        True
        >>>
        >>> # Code block (НЕ должен обработаться)
        >>> html2 = '<pre><code class="language-python">def hello():</code></pre>'
        >>> soup2 = BeautifulSoup(html2, 'html.parser')
        >>> processor.process(soup2)
        >>> 'text-danger' not in str(soup2)  # Классы НЕ добавлены
        True
    """

    def process(self, soup: BeautifulSoup) -> None:
        """Добавляет Bootstrap классы к inline-коду.

        Алгоритм:
        1. Ищем все <code> элементы
        2. Проверяем родителя: если это <pre>, пропускаем
        3. Если это inline-код, добавляем Bootstrap классы

        Args:
            soup: Объект BeautifulSoup с HTML документом.

        Returns:
            None. Модификации выполняются in-place.

        Note:
            Классы добавляются к существующим (не перезаписываются).
            Code blocks остаются без изменений для Highlight.js.
        """
        for code in soup.find_all("code"):
            # Пропускаем code blocks (внутри <pre>)
            if code.parent and code.parent.name == "pre":
                continue

            # Обрабатываем только inline-код
            existing_classes_raw = code.get("class")
            existing_classes = (
                existing_classes_raw if isinstance(existing_classes_raw, list) else []
            )

            # Bootstrap классы для inline-кода
            bootstrap_classes = ["text-danger", "bg-light", "px-1"]

            # Добавляем только те классы, которых еще нет
            new_classes = [
                cls for cls in bootstrap_classes if cls not in existing_classes
            ]

            if new_classes:
                code["class"] = existing_classes + new_classes

    def get_name(self) -> str:
        """Возвращает имя процессора для логирования.

        Returns:
            Строка с названием процессора.
        """
        return "CodeProcessor"
