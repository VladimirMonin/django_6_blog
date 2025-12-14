# blog/services/processors/table_processor.py
"""Процессор для добавления Bootstrap классов к таблицам.

Обрабатывает все <table> элементы в HTML и добавляет Bootstrap 5 классы
для стилизации.
"""

from bs4 import BeautifulSoup

from blog.services.html_processor import HTMLProcessor


class TableProcessor(HTMLProcessor):
    """Процессор для добавления Bootstrap классов к таблицам.

    Добавляет следующие классы к каждому <table> элементу:
    - table: базовый класс Bootstrap таблиц
    - table-striped: зебра-стилизация (чередующиеся строки)
    - table-hover: подсветка строки при наведении
    - table-bordered: границы для всех ячеек

    Также оборачивает таблицы в контейнер с классом 'table-responsive'
    для горизонтальной прокрутки на мобильных устройствах.

    Референс из doc/samples/assets/js/main.js:
        table: ["table", "table-striped"]

    Bootstrap 5 Table Docs:
        https://getbootstrap.com/docs/5.3/content/tables/

    Example:
        >>> from bs4 import BeautifulSoup
        >>> from blog.services.processors.table_processor import TableProcessor
        >>>
        >>> html = '<table><tr><td>Cell</td></tr></table>'
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> processor = TableProcessor()
        >>> processor.process(soup)
        >>> 'class="table table-striped table-hover table-bordered"' in str(soup)
        True
        >>> 'table-responsive' in str(soup)
        True
    """

    def process(self, soup: BeautifulSoup) -> None:
        """Добавляет Bootstrap классы ко всем таблицам и оборачивает в контейнер.

        Args:
            soup: Объект BeautifulSoup с HTML документом.

        Returns:
            None. Модификации выполняются in-place.

        Note:
            Классы добавляются к существующим (не перезаписываются).
            Если таблица уже имеет класс, новые классы добавляются к списку.
            Таблицы оборачиваются в div.table-responsive для мобильного скролла.
        """
        for table in soup.find_all("table"):
            # Пропускаем таблицы, уже обернутые в table-responsive
            if table.parent and table.parent.name == "div":
                parent_classes = table.parent.get("class", [])
                if "table-responsive" in parent_classes:
                    continue

            # Получаем существующие классы или пустой список
            existing_classes_raw = table.get("class")
            existing_classes = (
                existing_classes_raw if isinstance(existing_classes_raw, list) else []
            )

            # Добавляем Bootstrap классы (если их еще нет)
            bootstrap_classes = ["table", "table-striped", "table-hover", "table-bordered"]

            # Объединяем существующие и новые классы (без дубликатов)
            new_classes = existing_classes + [
                cls for cls in bootstrap_classes if cls not in existing_classes
            ]

            # Устанавливаем обновленные классы
            table["class"] = new_classes

            # Оборачиваем таблицу в div.table-responsive для мобильного скролла
            wrapper = soup.new_tag("div")
            wrapper["class"] = ["table-responsive"]
            table.wrap(wrapper)

    def get_name(self) -> str:
        """Возвращает имя процессора.

        Returns:
            Строка "TableProcessor".
        """
        return "TableProcessor"
