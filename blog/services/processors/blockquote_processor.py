# blog/services/processors/blockquote_processor.py
"""Процессор для обработки blockquote и Obsidian Callouts.

Обрабатывает все <blockquote> элементы в HTML:
- Обычные цитаты → базовые Bootstrap классы
- Obsidian Callouts ([!info], [!warning] и т.д.) → Bootstrap alerts
"""

from bs4 import BeautifulSoup

from blog.services.html_processor import HTMLProcessor


class BlockquoteProcessor(HTMLProcessor):
    """Процессор для обработки blockquote и Obsidian Callouts.

    Маппинг Obsidian Callouts на Bootstrap 5 Alert классы:
    - [!info] → alert alert-info (синий)
    - [!warning] → alert alert-warning (желтый)
    - [!success] → alert alert-success (зеленый)
    - [!error] / [!danger] → alert alert-danger (красный)
    - [!tip] → alert alert-primary (основной цвет)
    - [!note] → alert alert-secondary (серый)

    Для обычных цитат (без маркера) добавляются классы:
    - blockquote: базовый Bootstrap класс
    - border-start: левая граница
    - border-warning: цвет границы (желтый)
    - ps-3: padding-left

    Референс из doc/samples/assets/js/main.js:40-67

    Bootstrap 5 Alerts Docs:
        https://getbootstrap.com/docs/5.3/components/alerts/

    Obsidian Callouts Docs:
        https://help.obsidian.md/Editing+and+formatting/Callouts

    Example:
        >>> from bs4 import BeautifulSoup
        >>> from blog.services.processors.blockquote_processor import BlockquoteProcessor
        >>>
        >>> # Obsidian Callout
        >>> html = '<blockquote><p>[!warning]</p><p>Осторожно!</p></blockquote>'
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> processor = BlockquoteProcessor()
        >>> processor.process(soup)
        >>> 'alert alert-warning' in str(soup)
        True
        >>> '[!warning]' not in str(soup)  # Маркер удален
        True
        >>>
        >>> # Обычная цитата
        >>> html2 = '<blockquote><p>Простая цитата</p></blockquote>'
        >>> soup2 = BeautifulSoup(html2, 'html.parser')
        >>> processor.process(soup2)
        >>> 'blockquote border-start' in str(soup2)
        True
    """

    # Маппинг Obsidian типов на Bootstrap 5 Alert классы
    CALLOUT_MAPPING = {
        "[!info]": "alert alert-info",
        "[!warning]": "alert alert-warning",
        "[!success]": "alert alert-success",
        "[!error]": "alert alert-danger",
        "[!danger]": "alert alert-danger",
        "[!tip]": "alert alert-primary",
        "[!note]": "alert alert-secondary",
    }

    def process(self, soup: BeautifulSoup) -> None:
        """Обрабатывает blockquote элементы.

        Алгоритм:
        1. Ищем все <blockquote> в документе
        2. Проверяем первый <p> на наличие Obsidian маркера
        3. Если маркер есть → добавляем alert классы, удаляем маркер
        4. Если маркера нет → добавляем базовые blockquote классы

        Args:
            soup: Объект BeautifulSoup с HTML документом.

        Returns:
            None. Модификации выполняются in-place.

        Note:
            Маркер [!type] удаляется из контента через decompose().
        """
        for blockquote in soup.find_all("blockquote"):
            # Ищем первый параграф
            first_p = blockquote.find("p")

            if first_p:
                text = first_p.get_text().strip()

                # Проверяем, есть ли Obsidian Callout маркер
                if text in self.CALLOUT_MAPPING:
                    # Добавляем Bootstrap Alert классы
                    alert_classes = self.CALLOUT_MAPPING[text].split()
                    existing_classes_raw = blockquote.get("class")
                    existing_classes = (
                        existing_classes_raw
                        if isinstance(existing_classes_raw, list)
                        else []
                    )

                    blockquote["class"] = existing_classes + alert_classes

                    # Удаляем маркер из контента
                    first_p.decompose()

                    # Не добавляем базовые классы, если это Callout
                    continue

            # Если нет маркера, добавляем базовые классы для обычной цитаты
            if "class" not in blockquote.attrs:
                blockquote["class"] = [
                    "blockquote",
                    "border-start",
                    "border-warning",
                    "ps-3",
                ]

    def get_name(self) -> str:
        """Возвращает имя процессора для логирования.

        Returns:
            Строка с названием процессора.
        """
        return "BlockquoteProcessor"
