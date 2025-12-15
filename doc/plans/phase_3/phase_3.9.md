# Фаза 3.9: Интеграция препроцессора в Post.save()

## Цель

Интегрировать `MarkdownMediaPreprocessor` в метод `save()` модели Post и `convert_markdown_to_html()`, чтобы ссылки автоматически резолвились при каждом сохранении.

## Контекст

**Текущее состояние:** В [blog/models.py](../../../blog/models.py) метод `save()` вызывает `convert_markdown_to_html(self.content)`. В [blog/services/markdown_converter.py](../../../blog/services/markdown_converter.py) функция принимает только строку Markdown.

**Проблема:** Препроцессор нужно вызвать **до** `markdown.markdown()`, но после того как Post сохранён (чтобы был self.pk для доступа к связанным PostMedia). Chicken-and-egg problem: нужен Post для preprocessor, но preprocessor нужен в save().

**Решение:** Изменить сигнатуру `convert_markdown_to_html()` чтобы принимать объект Post (опционально), вызывать препроцессор внутри convert если передан Post, иначе работать как раньше (для обратной совместимости).

**Технологии:** Рефакторинг существующей функции, опциональные параметры Python.

**Философия:** "Backward Compatible Evolution". Не ломаем существующий код — добавляем новую функциональность через опциональный параметр.

**Важно:** Препроцессор должен вызываться **после** первого save() (когда есть pk), но **до** markdown.markdown(). Используем двухэтапный save: первый для получения pk, второй для обновления content_html.

## Задачи

### Модификация convert_markdown_to_html

- [ ] Открыть [blog/services/markdown_converter.py](../../../blog/services/markdown_converter.py)
- [ ] Изменить сигнатуру функции:

```python
def convert_markdown_to_html(markdown_text: str, post=None) -> str:
```

- [ ] Импортировать препроцессор в начале файла:

```python
from blog.services.markdown_media_preprocessor import MarkdownMediaPreprocessor
```

- [ ] Добавить обработку препроцессора **до** `markdown.markdown()`:

```python
if not markdown_text:
    return ""

# Препроцессинг медиа-ссылок (если передан объект Post)
if post is not None and post.pk is not None:
    preprocessor = MarkdownMediaPreprocessor(post)
    markdown_text = preprocessor.process(markdown_text)

# Дальше идёт существующий код с markdown.markdown()
```

### Модификация Post.save()

- [ ] Открыть [blog/models.py](../../../blog/models.py)
- [ ] Найти метод `save()` в классе Post
- [ ] Изменить вызов convert для использования двухэтапного сохранения:

```python
def save(self, *args, **kwargs):
    if not self.slug:
        self.slug = slugify(self.title)
    
    # Авто-генерация excerpt если пустой
    if not self.excerpt and self.content:
        self.excerpt = self.content[:300]
    
    # Первое сохранение для получения pk
    if not self.pk:
        super().save(*args, **kwargs)
    
    # Конвертация Markdown → HTML с препроцессором
    if self.content:
        self.content_html = convert_markdown_to_html(self.content, post=self)
    
    # Финальное сохранение с обновлённым content_html
    super().save(*args, **kwargs)
```

### Обновление импортов в models.py

- [ ] Убедиться что импорт convert остался на месте:

```python
from blog.services import convert_markdown_to_html
```

### Тестирование интеграции

- [ ] Создать новый пост через Django shell или админку
- [ ] Добавить PostMedia к посту с `original_filename = 'test.png'`
- [ ] В content написать: `"# Test\n\n![Image](test.png)"`
- [ ] Сохранить пост
- [ ] Проверить `post.content_html` — должна быть ссылка `/media/posts/{slug}/test.png`
- [ ] Обновить пост (изменить title, пересохранить)
- [ ] Убедиться что ссылки не сломались после повторного save()

### Проверка обратной совместимости

- [ ] Убедиться что вызов `convert_markdown_to_html(text)` без параметра post работает
- [ ] Создать тестовый скрипт:

```python
from blog.services import convert_markdown_to_html
html = convert_markdown_to_html("# Hello\n\n![](image.png)")
# Должен работать без ошибок, image.png останется как есть
```

### Обновление tests (если есть)

- [ ] Если в проекте есть тесты для convert_markdown_to_html, обновить их
- [ ] Добавить тест для препроцессора с Post объектом
- [ ] Добавить тест что без Post препроцессор не вызывается

## Коммит

**Формат:** `phase 3.9 feat: Интегрирован препроцессор в Post.save() и convert_markdown_to_html`

**Описание:**

```
phase 3.9 feat: Интегрирован препроцессор в Post.save() и convert_markdown_to_html

- Изменена сигнатура convert_markdown_to_html для приёма объекта Post
- Реализован двухэтапный save() для обработки препроцессора
- Препроцессор вызывается автоматически при сохранении поста
- Сохранена обратная совместимость для вызовов без Post
- Локальные ссылки на медиа резолвятся автоматически
```
