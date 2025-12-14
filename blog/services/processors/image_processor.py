# blog/services/processors/image_processor.py
"""Процессор для добавления Bootstrap классов к изображениям.

Обрабатывает все <img> элементы в HTML и добавляет Bootstrap 5 классы
для адаптивности и центровки, а также lazy loading.
"""

from bs4 import BeautifulSoup

from blog.services.html_processor import HTMLProcessor


class ImageProcessor(HTMLProcessor):
    """Процессор для добавления Bootstrap классов к изображениям.

    Добавляет следующие классы к каждому <img> элементу:
    - img-fluid: адаптивность (max-width: 100%; height: auto)
    - d-block: display: block
    - mx-auto: центровка по горизонтали (margin: 0 auto)

    Также добавляет атрибут loading="lazy" для оптимизации загрузки.

    Референс из doc/samples/assets/js/main.js:14:
        img: ["img-fluid", "d-block", "mx-auto"]

    Bootstrap 5 Images Docs:
        https://getbootstrap.com/docs/5.3/content/images/

    Example:
        >>> from bs4 import BeautifulSoup
        >>> from blog.services.processors.image_processor import ImageProcessor
        >>>
        >>> html = '<img src="photo.jpg" alt="Photo">'
        >>> soup = BeautifulSoup(html, 'html.parser')
        >>> processor = ImageProcessor()
        >>> processor.process(soup)
        >>> 'class="img-fluid d-block mx-auto"' in str(soup)
        True
        >>> 'loading="lazy"' in str(soup)
        True
    """

    def process(self, soup: BeautifulSoup) -> None:
        """Добавляет Bootstrap классы ко всем изображениям.

        Args:
            soup: Объект BeautifulSoup с HTML документом.

        Returns:
            None. Модификации выполняются in-place.

        Note:
            Классы добавляются к существующим (не перезаписываются).
            Атрибут loading добавляется только если его нет.
        """
        for img in soup.find_all("img"):
            # Безопасное получение существующих классов
            existing_classes_raw = img.get("class")
            existing_classes = (
                existing_classes_raw
                if isinstance(existing_classes_raw, list)
                else []
            )

            # Bootstrap классы для изображений
            bootstrap_classes = ["img-fluid", "d-block", "mx-auto"]

            # Добавляем только те классы, которых еще нет
            new_classes = [
                cls for cls in bootstrap_classes if cls not in existing_classes
            ]

            if new_classes:
                img["class"] = existing_classes + new_classes

            # Добавляем lazy loading если не задан
            if "loading" not in img.attrs:
                img["loading"] = "lazy"

    def get_name(self) -> str:
        """Возвращает имя процессора для логирования.

        Returns:
            Строка с названием процессора.
        """
        return "ImageProcessor"
