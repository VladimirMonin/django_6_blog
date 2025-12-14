# 🎨 Серия 15: Три процессора Phase 2.6 — Image, Blockquote, Code

> Реализация ImageProcessor, BlockquoteProcessor и CodeProcessor для полного охвата HTML элементов

---

## 📌 Контекст

После Phase 2.5 у нас есть:
- ✅ Архитектура HTMLProcessor + MarkdownProcessor
- ✅ TableProcessor как референсная реализация
- ⏳ Нужны процессоры для изображений, цитат и inline-кода

**Цель Phase 2.6**: Завершить систему процессоров, покрыв все основные HTML элементы Bootstrap классами.

---

## 🖼️ ImageProcessor: Адаптивные изображения с lazy loading

### Проблема

Markdown генерирует `<img>` без Bootstrap классов:

```html
<!-- ❌ После Markdown конвертации -->
<img src="photo.jpg" alt="Фото">
```

**Что не так**:
- Нет адаптивности → изображение не масштабируется
- Нет центровки → выровнено по левому краю
- Нет lazy loading → все изображения загружаются сразу

### Решение: Bootstrap Image утилиты

**Классы**:
- `.img-fluid` — адаптивность (`max-width: 100%; height: auto`)
- `.d-block` — display block (для центровки)
- `.mx-auto` — горизонтальная центровка (`margin: 0 auto`)

**Lazy loading**:
- Атрибут `loading="lazy"` — браузер загружает изображения при прокрутке

### Реализация

```python
# blog/services/processors/image_processor.py
class ImageProcessor(HTMLProcessor):
    def process(self, soup: BeautifulSoup) -> None:
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
                cls for cls in bootstrap_classes 
                if cls not in existing_classes
            ]

            if new_classes:
                img["class"] = existing_classes + new_classes

            # Добавляем lazy loading если не задан
            if "loading" not in img.attrs:
                img["loading"] = "lazy"

    def get_name(self) -> str:
        return "ImageProcessor"
```

### Результат

```html
<!-- ✅ После ImageProcessor -->
<img 
    src="photo.jpg" 
    alt="Фото" 
    class="img-fluid d-block mx-auto" 
    loading="lazy"
>
```

**Эффект**:
- 📱 Изображение адаптируется под ширину контейнера
- 🎯 Центрировано горизонтально
- ⚡ Загружается при прокрутке (экономия трафика)

---

## 💬 BlockquoteProcessor: Цитаты и Obsidian Callouts

### Проблема

Markdown генерирует простой `<blockquote>`:

```html
<!-- ❌ Обычная цитата -->
<blockquote>
  <p>Текст цитаты</p>
</blockquote>

<!-- ❌ Obsidian Callout (маркер остается) -->
<blockquote>
  <p>[!warning]</p>
  <p>Важное предупреждение</p>
</blockquote>
```

**Что не так**:
- Нет стилей Bootstrap
- Obsidian маркеры `[!warning]` не обрабатываются
- Цитаты выглядят как обычный текст

### Решение: Bootstrap Alerts + базовые стили

**Два сценария**:

1. **Обычная цитата** → базовые Bootstrap классы:
   - `.blockquote` — базовый класс
   - `.border-start` — левая граница
   - `.border-warning` — желтая граница
   - `.ps-3` — padding-left

2. **Obsidian Callout** → Bootstrap Alert классы:
   - `[!info]` → `.alert .alert-info` (синий)
   - `[!warning]` → `.alert .alert-warning` (желтый)
   - `[!success]` → `.alert .alert-success` (зеленый)
   - `[!error]` / `[!danger]` → `.alert .alert-danger` (красный)
   - `[!tip]` → `.alert .alert-primary` (основной цвет)
   - `[!note]` → `.alert .alert-secondary` (серый)

### Реализация

```python
# blog/services/processors/blockquote_processor.py
class BlockquoteProcessor(HTMLProcessor):
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

            # Если нет маркера, добавляем базовые классы
            if "class" not in blockquote.attrs:
                blockquote["class"] = [
                    "blockquote",
                    "border-start",
                    "border-warning",
                    "ps-3",
                ]
```

### Результат

```html
<!-- ✅ Обычная цитата -->
<blockquote class="blockquote border-start border-warning ps-3">
  <p>Текст цитаты</p>
</blockquote>

<!-- ✅ Obsidian Callout (маркер удален!) -->
<blockquote class="alert alert-warning">
  <p>Важное предупреждение</p>
</blockquote>
```

**Эффект**:
- 🎨 Цитаты стилизованы с желтой левой границей
- 🚨 Callouts превращаются в Bootstrap Alerts
- 🧹 Маркеры `[!type]` удаляются из контента

---

## 💻 CodeProcessor: Inline-код с визуальным выделением

### Проблема

Markdown генерирует `<code>` без стилей:

```html
<!-- ❌ Inline-код -->
<p>Используйте функцию <code>convert_markdown_to_html()</code> для конвертации.</p>

<!-- ✅ Code block (НЕ трогаем!) -->
<pre><code class="language-python">def hello():</code></pre>
```

**Что не так**:
- Inline `<code>` не выделен визуально
- Сливается с текстом

**Что НЕ делаем**:
- **Code blocks** (`<pre><code>`) обрабатывает Highlight.js на фронтенде

### Решение: Bootstrap утилиты для inline-кода

**Классы**:
- `.text-danger` — красный цвет текста
- `.bg-light` — светлый фон
- `.px-1` — padding по горизонтали (0.25rem)

### Реализация

```python
# blog/services/processors/code_processor.py
class CodeProcessor(HTMLProcessor):
    def process(self, soup: BeautifulSoup) -> None:
        for code in soup.find_all("code"):
            # Пропускаем code blocks (внутри <pre>)
            if code.parent and code.parent.name == "pre":
                continue

            # Обрабатываем только inline-код
            existing_classes_raw = code.get("class")
            existing_classes = (
                existing_classes_raw
                if isinstance(existing_classes_raw, list)
                else []
            )

            # Bootstrap классы для inline-кода
            bootstrap_classes = ["text-danger", "bg-light", "px-1"]

            # Добавляем только те классы, которых еще нет
            new_classes = [
                cls for cls in bootstrap_classes 
                if cls not in existing_classes
            ]

            if new_classes:
                code["class"] = existing_classes + new_classes
```

### Результат

```html
<!-- ✅ Inline-код выделен -->
<p>Используйте функцию <code class="text-danger bg-light px-1">convert_markdown_to_html()</code> для конвертации.</p>

<!-- ✅ Code block остался без изменений -->
<pre><code class="language-python">def hello():</code></pre>
```

**Эффект**:
- 🔴 Inline-код выделен красным цветом
- 🎨 Светлый фон для контраста
- 📦 Code blocks остаются для Highlight.js

---

## 🔗 Интеграция: Обновление пайплайна

### Обновление `__init__.py`

```python
# blog/services/processors/__init__.py
from blog.services.processors.blockquote_processor import BlockquoteProcessor
from blog.services.processors.code_processor import CodeProcessor
from blog.services.processors.image_processor import ImageProcessor
from blog.services.processors.table_processor import TableProcessor

__all__ = [
    "TableProcessor",
    "ImageProcessor",
    "BlockquoteProcessor",
    "CodeProcessor",
]
```

### Обновление `markdown_converter.py`

```python
# blog/services/markdown_converter.py
from blog.services.processors import (
    BlockquoteProcessor,
    CodeProcessor,
    ImageProcessor,
    TableProcessor,
)

def convert_markdown_to_html(markdown_text: str) -> str:
    # ... Markdown → HTML ...
    
    # Этап 2: Обработка HTML процессорами
    processors = [
        TableProcessor(),       # Таблицы → Bootstrap классы
        ImageProcessor(),       # Изображения → .img-fluid, lazy loading
        BlockquoteProcessor(),  # Цитаты + Obsidian Callouts
        CodeProcessor(),        # Inline-код → .text-danger, .bg-light
    ]
    
    processor = MarkdownProcessor(processors)
    html = processor.process_html(html)
    
    return html
```

---

## 📊 Сравнение: До и После

| Элемент | До Phase 2.6 | После Phase 2.6 |
|---------|--------------|-----------------|
| `<table>` | ✅ `.table .table-striped` | ✅ (Phase 2.5) |
| `<img>` | ❌ Нет классов | ✅ `.img-fluid .d-block .mx-auto loading="lazy"` |
| `<blockquote>` | ❌ Нет стилей | ✅ `.blockquote .border-start` |
| Obsidian Callouts | ❌ Маркеры видны | ✅ `.alert .alert-*`, маркеры удалены |
| Inline `<code>` | ❌ Не выделен | ✅ `.text-danger .bg-light .px-1` |
| Code blocks | ✅ Highlight.js | ✅ (не трогаем) |

---

## 🧪 Тестирование

### Регенерация постов

```bash
python manage.py create_posts --clear
```

**Результат**:
```
🗑️  Удалено 9 существующих постов.
📚 Найдено 9 архитектурных документов
✓ Создан: Серия 01...
✓ Создан: Серия 02...
...
✨ Успешно создано постов: 9
```

### Проверка в браузере

1. **Изображения**:
   - Открыть DevTools → Elements
   - Найти `<img>` → проверить классы `.img-fluid .d-block .mx-auto`
   - Проверить атрибут `loading="lazy"`

2. **Цитаты**:
   - Найти `<blockquote>` → классы `.blockquote .border-start`
   - Найти Callout → класс `.alert .alert-warning` (без маркера)

3. **Inline-код**:
   - Найти `<code>` вне `<pre>` → классы `.text-danger .bg-light .px-1`
   - Code blocks → только `.language-*` от Highlight.js

---

## ⚠️ Важные детали

### 1. Безопасная работа с атрибутом `class`

Beautiful Soup может вернуть `class` как:
- `None` (если нет)
- `str` (если один класс)
- `list[str]` (если несколько)

**Решение**: явная проверка типа

```python
existing_classes_raw = img.get("class")
existing_classes = (
    existing_classes_raw
    if isinstance(existing_classes_raw, list)
    else []
)
```

### 2. Идемпотентность

Процессоры проверяют, есть ли уже нужные классы:

```python
new_classes = [
    cls for cls in bootstrap_classes 
    if cls not in existing_classes
]
```

Повторный запуск → дубликатов нет.

### 3. Пропуск code blocks в CodeProcessor

```python
if code.parent and code.parent.name == "pre":
    continue  # Пропускаем code blocks
```

Highlight.js работает отдельно на фронтенде.

### 4. Удаление маркеров Obsidian

```python
first_p.decompose()  # Удаляет весь <p> с маркером
```

Не `first_p.string = ""` (оставит пустой тег).

---

## 📈 Статистика Phase 2.6

**Файлы**:
- ✅ `image_processor.py` — 89 строк
- ✅ `blockquote_processor.py` — 137 строк
- ✅ `code_processor.py` — 97 строк
- ✅ Обновлен `__init__.py` — экспорт всех процессоров
- ✅ Обновлен `markdown_converter.py` — регистрация в пайплайне

**Итого**:
- 3 новых процессора
- ~320 строк кода
- 4 типа HTML элементов покрыто Bootstrap классами

---

## 🎯 Что дальше?

### Phase 2.7: Frontend интерактивность

**Цель**: Добавить JS для улучшения UX

**Планы**:
1. **Fullscreen images** — клик на изображение → оверлей на весь экран
2. **Copy code buttons** — кнопка "Copy" для code blocks
3. **Media players** — Plyr.io для `<video>` и `<audio>`
4. **Table of Contents** — автоматическое оглавление из заголовков

**Философия**: Backend (Phase 2.5-2.6) добавил статические классы, Frontend (Phase 2.7) добавит интерактивность.

---

## 🔗 Связанные серии

- **← Серия 13**: Архитектура HTML-процессоров
- **← Серия 14**: TableProcessor — референсная реализация
- **→ Серия 16**: (планируется) Документация Phase 2.7

---

**Последнее обновление**: 14 декабря 2025