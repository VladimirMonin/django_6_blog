# blog/services.py
"""Сервисы для работы с контентом блога.

Функции:
    convert_markdown_to_html(markdown_text: str) -> str
        Конвертирует Markdown в HTML с поддержкой подсветки кода.
"""

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension


def convert_markdown_to_html(markdown_text: str) -> str:
    """Конвертирует Markdown текст в HTML.

    Использует гибридный подход: генерирует чистый HTML с классами для
    подсветки синтаксиса на фронтенде (Highlight.js), без встроенных
    стилей Pygments.

    Args:
        markdown_text: Текст в формате Markdown.

    Returns:
        HTML строка с сохраненной структурой и классами для code blocks.

    Example:
        >>> markdown_text = "# Hello\\n\\n```python\\nprint('world')\\n```"
        >>> html = convert_markdown_to_html(markdown_text)
        >>> '<h1>Hello</h1>' in html
        True
        >>> 'class="language-python"' in html
        True
    """
    if not markdown_text:
        return ""

    # Настройка расширений Markdown
    extensions = [
        "extra",  # Таблицы, footnotes, abbr, attr_list
        "fenced_code",  # Блоки кода с тройными backticks ```
        "tables",  # Таблицы (входит в extra, но явно указываем)
        "nl2br",  # Переносы строк → <br>
        "codehilite",  # Подсветка кода БЕЗ Pygments (классы для Highlight.js)
        "pymdownx.superfences",  # Улучшенные code blocks (поддержка Mermaid)
        "pymdownx.emoji",  # Эмодзи :smile:
        "pymdownx.tasklist",  # Чекбоксы - [ ] и - [x]
    ]

    # Конфигурация расширений
    extension_configs = {
        "codehilite": {
            "use_pygments": False,  # НЕ генерировать HTML с Pygments
            "guess_lang": True,  # Автоопределение языка
            "lang_prefix": "language-",  # Префикс для классов (Highlight.js формат)
            "css_class": "highlight",  # CSS класс для обертки
        },
        "pymdownx.superfences": {
            "custom_fences": [
                {
                    "name": "mermaid",
                    "class": "mermaid",
                    "format": lambda source, language, css_class, options, md, **kwargs: f'<div class="mermaid">{source}</div>',
                }
            ]
        },
        "pymdownx.emoji": {
            "emoji_index": lambda: None,  # Отключаем индекс (используем простые эмодзи)
            "emoji_generator": lambda *args: args[0],  # Возвращаем текст как есть
        },
    }

    try:
        # Конвертация Markdown → HTML
        html = markdown.markdown(
            markdown_text,
            extensions=extensions,
            extension_configs=extension_configs,
            output_format="html5",
        )
        return html
    except Exception as e:
        # В случае ошибки логируем и возвращаем пустую строку
        # В production лучше использовать logging
        print(f"Ошибка конвертации Markdown: {e}")
        return ""
