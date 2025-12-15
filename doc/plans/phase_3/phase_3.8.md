# Фаза 3.8: Сервис MarkdownMediaPreprocessor

## Цель

Создать `MarkdownMediaPreprocessor` для обработки ссылок на медиа-файлы в Markdown **до** конвертации в HTML, резолвя локальные имена в URL через PostMedia.

## Контекст

**Текущее состояние:** В [blog/services/](../../../blog/services/) есть `markdown_converter.py` и `markdown_processor.py` для обработки HTML. Нет препроцессора для Markdown.

**Проблема:** Когда админ пишет `![](image.png)` в Markdown, система не знает что это за файл и где он лежит. При импорте из Obsidian ссылки `![[image.png]]` вообще не работают в стандартном Markdown.

**Решение:** Препроцессор парсит Markdown текст **до** `markdown.markdown()`, находит все ссылки на файлы, ищет соответствующий PostMedia по `original_filename`, заменяет на полный путь `/media/posts/{slug}/{filename}`.

**Технологии:** Регулярные выражения для парсинга Markdown, Django ORM для поиска PostMedia.

**Философия:** "Resolve Before Render". Ссылки должны быть преобразованы в валидные URL до того, как Markdown превратится в HTML. Это позволяет кешировать HTML без повторного резолвинга.

**Важно:** Препроцессор НЕ изменяет базу данных — он возвращает новый текст Markdown с обновлёнными ссылками, который затем передаётся в `markdown.markdown()`.

## Задачи

### Создание файла препроцессора

- [ ] Создать файл `blog/services/markdown_media_preprocessor.py`
- [ ] Добавить docstring модуля:

```python
"""Препроцессор для обработки медиа-ссылок в Markdown.

Обрабатывает локальные ссылки на файлы BEFORE конвертации в HTML.
Резолвит имена файлов через PostMedia.original_filename.
"""
```

- [ ] Импортировать необходимые модули: `import re` и `from typing import Optional`

### Создание класса MarkdownMediaPreprocessor

- [ ] Создать класс `MarkdownMediaPreprocessor`:
- [ ] Добавить конструктор `__init__(self, post)` который принимает объект Post
- [ ] Сохранить post в `self.post = post`
- [ ] Создать кеш media_map: `self.media_map = self._build_media_map()`

### Реализация _build_media_map

- [ ] Создать приватный метод `_build_media_map(self) -> dict`:
- [ ] Если `self.post.pk` не существует, вернуть пустой словарь
- [ ] Получить все PostMedia поста: `media_files = self.post.media_files.all()`
- [ ] Создать словарь `{original_filename: file.url}`:

```python
return {
    media.original_filename: media.file.url
    for media in media_files
}
```

- [ ] Это позволяет O(1) lookup по имени файла

### Реализация process()

- [ ] Создать публичный метод `process(self, markdown_text: str) -> str`:
- [ ] Добавить docstring: "Обрабатывает Markdown текст, резолвя локальные медиа-ссылки."
- [ ] Вызвать `markdown_text = self._resolve_markdown_images(markdown_text)`
- [ ] Вернуть обработанный текст

### Реализация _resolve_markdown_images

- [ ] Создать метод `_resolve_markdown_images(self, text: str) -> str`:
- [ ] Создать regex pattern для поиска `![alt](filename)`:

```python
pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
```

- [ ] Использовать `re.sub()` с callback-функцией для замены:

```python
def replace_link(match):
    alt_text = match.group(1)
    filename = match.group(2)
    
    # Игнорировать внешние ссылки
    if filename.startswith(('http://', 'https://', '/')):
        return match.group(0)  # Не изменяем
    
    # Искать в media_map
    resolved_url = self.media_map.get(filename)
    if resolved_url:
        return f'![{alt_text}]({resolved_url})'
    
    # Если не найдено, оставить как есть (битая ссылка)
    return match.group(0)

return re.sub(pattern, replace_link, text)
```

### Тестирование препроцессора отдельно

- [ ] Создать тестовый скрипт или использовать Django shell:
- [ ] Создать пост с медиа-файлом
- [ ] Markdown текст: `"# Test\n\n![Моё изображение](test.png)"`
- [ ] Создать препроцессор: `preprocessor = MarkdownMediaPreprocessor(post)`
- [ ] Вызвать: `result = preprocessor.process(markdown_text)`
- [ ] Проверить что `test.png` заменён на `/media/posts/{slug}/test.png`

## Коммит

**Формат:** `phase 3.8 feat: Создан MarkdownMediaPreprocessor для резолвинга локальных ссылок`

**Описание:**

```
phase 3.8 feat: Создан MarkdownMediaPreprocessor для резолвинга локальных ссылок

- Создан blog/services/markdown_media_preprocessor.py
- Реализован класс MarkdownMediaPreprocessor с методом process()
- Создан media_map для быстрого lookup PostMedia по имени файла
- Реализован _resolve_markdown_images для замены локальных ссылок
- Игнорируются внешние URL (http://, https://, /)
```
