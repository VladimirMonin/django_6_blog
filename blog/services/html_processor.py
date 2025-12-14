# blog/services/html_processor.py
"""Базовый класс для HTML-процессоров.

Определяет интерфейс для всех процессоров, обрабатывающих HTML элементы
с помощью Beautiful Soup 4.
"""

from abc import ABC, abstractmethod
from bs4 import BeautifulSoup


class HTMLProcessor(ABC):
    """Базовый абстрактный класс для обработчиков HTML элементов.

    Все процессоры должны наследовать этот класс и реализовывать методы:
    - process(soup) - основная логика обработки
    - get_name() - имя процессора для логирования

    Архитектура:
        1. Каждый процессор отвечает за свой тип элементов (таблицы, изображения, цитаты)
        2. Процессоры работают in-place (модифицируют soup напрямую)
        3. Процессоры не должны зависеть друг от друга
        4. Порядок регистрации процессоров важен (если есть зависимости)

    Философия:
        Backend (процессоры) добавляет статические Bootstrap классы.
        Frontend (JS) добавляет интерактивность (кнопки, плееры, фуллскрин).

    Example:
        >>> from blog.services.html_processor import HTMLProcessor
        >>> from bs4 import BeautifulSoup
        >>>
        >>> class MyProcessor(HTMLProcessor):
        ...     def process(self, soup: BeautifulSoup) -> None:
        ...         for tag in soup.find_all('div'):
        ...             tag['class'] = tag.get('class', []) + ['my-class']
        ...
        ...     def get_name(self) -> str:
        ...         return "MyProcessor"
    """

    @abstractmethod
    def process(self, soup: BeautifulSoup) -> None:
        """Обрабатывает HTML, модифицируя soup in-place.

        Args:
            soup: Объект BeautifulSoup с HTML документом.

        Returns:
            None. Модификации выполняются in-place.

        Note:
            Метод должен быть идемпотентным (повторный запуск не должен
            ломать результат).
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Возвращает имя процессора для логирования.

        Returns:
            Строка с именем процессора (например, "TableProcessor").

        Note:
            Используется для отладки и логирования порядка выполнения.
        """
        pass
