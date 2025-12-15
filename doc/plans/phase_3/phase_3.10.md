# Фаза 3.10: Поддержка Obsidian wikilinks

## Цель

Добавить в `MarkdownMediaPreprocessor` метод конвертации Obsidian wikilinks (`![[file.png]]`) в стандартный Markdown перед обработкой ссылок.

## Контекст

**Текущее состояние:** В [blog/services/markdown_media_preprocessor.py](../../../blog/services/markdown_media_preprocessor.py) препроцессор умеет обрабатывать только стандартный Markdown `![](file.png)`.

**Проблема:** Obsidian использует собственный синтаксис wikilinks для вставки изображений: `![[image.png]]`, `![[image.png|alt text]]`, `![[folder/image.png]]`. Эти ссылки не работают в стандартном Markdown.

**Решение:** Добавить этап конвертации wikilinks → стандартный Markdown **до** резолвинга путей. Таким образом цепочка будет: Obsidian wikilinks → Markdown → Resolved URLs → HTML.

**Технологии:** Регулярные выражения для парсинга wikilinks, обработка разделителя `|` для alt-текста.

**Философия:** "Universal Input Format". Система должна принимать Markdown из любого источника (Obsidian, Notion, ручной ввод) и нормализовать его перед обработкой.

**Важно:** Obsidian поддерживает вложенные папки в wikilinks: `![[attachments/images/photo.png]]`. Нам нужно извлечь только имя файла (`photo.png`) для матчинга с `PostMedia.original_filename`.

## Задачи

### Реализация _convert_wikilinks

- [ ] Открыть [blog/services/markdown_media_preprocessor.py](../../../blog/services/markdown_media_preprocessor.py)
- [ ] Добавить метод `_convert_wikilinks(self, text: str) -> str`:
- [ ] Добавить docstring: "Конвертирует Obsidian wikilinks в стандартный Markdown."
- [ ] Создать regex pattern для wikilinks:

```python
# ![[filename]] или ![[filename|alt text]]
pattern = r'!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]'
```

- [ ] Использовать `re.sub()` с callback:

```python
def replace_wikilink(match):
    filepath = match.group(1).strip()  # Может быть folder/file.png
    alt_text = match.group(2)  # Может быть None
    
    # Извлечь только имя файла (без папок)
    filename = filepath.split('/')[-1]
    
    # Использовать alt-text или имя файла
    alt = alt_text.strip() if alt_text else filename
    
    # Вернуть стандартный Markdown
    return f'![{alt}]({filename})'

return re.sub(pattern, replace_wikilink, text)
```

### Интеграция в process()

- [ ] Найти метод `process(self, markdown_text: str) -> str`
- [ ] Добавить вызов `_convert_wikilinks` **до** `_resolve_markdown_images`:

```python
def process(self, markdown_text: str) -> str:
    # 1. Конвертируем Obsidian wikilinks в стандартный Markdown
    markdown_text = self._convert_wikilinks(markdown_text)
    
    # 2. Резолвим локальные ссылки в URL
    markdown_text = self._resolve_markdown_images(markdown_text)
    
    return markdown_text
```

### Обработка edge cases

- [ ] Добавить поддержку относительных путей Obsidian:
  - `![[./image.png]]` → извлечь `image.png`
  - `![[../image.png]]` → извлечь `image.png`
- [ ] Модифицировать функцию replace_wikilink:

```python
# Удалить ./ и ../
filename = filepath.replace('./', '').replace('../', '').split('/')[-1]
```

### Тестирование wikilinks

- [ ] Создать тестовый Markdown с различными форматами wikilinks:

```markdown
# Test Wikilinks

![[simple.png]]
![[image.png|Beautiful photo]]
![[attachments/photo.jpg]]
![[./local.png]]
![[../parent/file.png|Custom alt]]
```

- [ ] Пропустить через препроцессор
- [ ] Проверить что все конвертированы в стандартный Markdown:

```markdown
![simple.png](simple.png)
![Beautiful photo](image.png)
![photo.jpg](photo.jpg)
![local.png](local.png)
![Custom alt](file.png)
```

### Тестирование резолвинга после wikilinks

- [ ] Создать пост с PostMedia с `original_filename = 'simple.png'`
- [ ] В content добавить: `![[simple.png]]`
- [ ] Сохранить пост
- [ ] Проверить `content_html` — должна быть ссылка `/media/posts/{slug}/simple.png`
- [ ] Проверить что изображение отображается на сайте

### Обработка не найденных файлов

- [ ] Проверить поведение когда файл в wikilink не существует в PostMedia
- [ ] Должна остаться ссылка `![filename](filename)` без резолвинга
- [ ] В HTML это приведёт к битой ссылке (что нормально — будет видно что файл не загружен)

## Коммит

**Формат:** `phase 3.10 feat: Добавлена поддержка Obsidian wikilinks в препроцессор`

**Описание:**

```
phase 3.10 feat: Добавлена поддержка Obsidian wikilinks в препроцессор

- Реализован метод _convert_wikilinks для конвертации ![[file]] в ![](file)
- Поддержка alt-текста через разделитель | в wikilinks
- Обработка вложенных папок Obsidian (извлечение только имени файла)
- Поддержка относительных путей ./ и ../
- Интегрирован в process() перед резолвингом URL
```
