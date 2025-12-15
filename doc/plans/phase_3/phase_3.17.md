# Фаза 3.17: Обработка внешних ссылок в препроцессоре

## Цель

Модифицировать `MarkdownMediaPreprocessor` для корректного различения локальных и внешних ссылок, игнорирования http/https URL, обработки относительных путей.

## Контекст

**Текущее состояние:** В [blog/services/markdown_media_preprocessor.py](../../../blog/services/markdown_media_preprocessor.py) препроцессор обрабатывает все ссылки `![](url)`.

**Проблема:** Если в посте есть `![](https://example.com/image.jpg)`, препроцессор попытается найти `https://example.com/image.jpg` в PostMedia, что неверно. Внешние URL должны игнорироваться.

**Решение:** Добавить проверки типа ссылки перед резолвингом: игнорировать http://, https://, абсолютные пути /, обрабатывать ./ и ../.

**Философия:** "Trust External, Resolve Local". Внешние ссылки — ответственность автора, локальные — резолвим через PostMedia.

## Задачи

### Модификация _resolve_markdown_images

- [ ] Открыть [blog/services/markdown_media_preprocessor.py](../../../blog/services/markdown_media_preprocessor.py)
- [ ] Найти метод `_resolve_markdown_images`
- [ ] Обновить функцию `replace_link` для проверки типа ссылки:

```python
def replace_link(match):
    alt_text = match.group(1)
    filename = match.group(2).strip()
    
    # Игнорировать внешние URL
    if filename.startswith(('http://', 'https://', '//')):
        return match.group(0)
    
    # Игнорировать абсолютные пути
    if filename.startswith('/'):
        return match.group(0)
    
    # Обработать относительные пути ./ и ../
    clean_filename = filename.replace('./', '').replace('../', '')
    
    # Извлечь только имя файла если есть вложенные папки
    clean_filename = clean_filename.split('/')[-1]
    
    # Резолвить через media_map
    resolved_url = self.media_map.get(clean_filename)
    if resolved_url:
        return f'![{alt_text}]({resolved_url})'
    
    # Оставить как есть если не найдено
    return match.group(0)
```

### Добавление метода is_external_url (опционально)

- [ ] Создать вспомогательный метод для чистоты кода:

```python
def _is_external_url(self, url: str) -> bool:
    """Проверяет является ли URL внешней ссылкой."""
    return url.startswith(('http://', 'https://', '//', '/'))
```

- [ ] Использовать в replace_link:

```python
if self._is_external_url(filename):
    return match.group(0)
```

### Обработка URL-кодированных имён

- [ ] Добавить поддержку декодирования URL:

```python
from urllib.parse import unquote

clean_filename = unquote(clean_filename)  # %20 -> пробел
```

### Тестирование различных типов ссылок

- [ ] Создать тестовый Markdown со всеми типами:

```markdown
# Test Links

![External](https://example.com/image.jpg)
![Protocol relative](//cdn.example.com/photo.png)
![Absolute](/static/logo.png)
![Relative](./image.png)
![Parent](../folder/photo.jpg)
![Local](simple.png)
![Nested](attachments/files/document.pdf)
![Encoded](my%20photo.png)
```

- [ ] Пропустить через препроцессор
- [ ] Проверить что внешние URL не изменились
- [ ] Проверить что локальные резолвятся

### Проверка edge cases

- [ ] Пустая ссылка `![]()`
- [ ] Ссылка только с пробелами `![]( )`
- [ ] Ссылка с якорем `![](image.png#anchor)`
- [ ] Ссылка с query params `![](image.png?v=1)`

## Коммит

**Формат:** `phase 3.17 feat: Улучшена обработка внешних ссылок в препроцессоре`

**Описание:**

```
phase 3.17 feat: Улучшена обработка внешних ссылок в препроцессоре

- Игнорирование http://, https://, // URL (внешние ресурсы)
- Игнорирование абсолютных путей начинающихся с /
- Обработка относительных путей ./ и ../
- Извлечение имени файла из вложенных папок
- Поддержка URL-кодированных имён через unquote
```
