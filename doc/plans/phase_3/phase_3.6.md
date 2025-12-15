# Фаза 3.6: Админка для PostMedia (TabularInline)

## Цель

Добавить `PostMediaInline` в `PostAdmin` для управления медиа-файлами прямо из формы редактирования поста с preview изображений и копированием Markdown-ссылок.

## Контекст

**Текущее состояние:** В [blog/admin.py](../../../blog/admin.py) есть только `PostAdmin` с базовыми полями. Модель PostMedia создана но не интегрирована в админку.

**Проблема:** Нет способа загрузить файлы к посту через админку. Админ должен видеть все медиа поста, загружать новые, видеть preview изображений и копировать готовые Markdown-ссылки для вставки в контент.

**Технологии:** Django Admin TabularInline для компактного отображения связанных объектов, `readonly_fields` для вычисляемых значений, `format_html` для безопасного рендеринга HTML в админке.

**Философия:** "Copy, Don't Type". Админ не должен вручную писать `![](image.png)` — кнопка "Копировать" даёт готовую ссылку с правильным путём.

**Важно:** TabularInline vs StackedInline — используем Tabular для компактности (список файлов одной строкой), Stacked лучше для сложных форм с множеством полей.

## Задачи

### Создание PostMediaInline

- [ ] В [blog/admin.py](../../../blog/admin.py) импортировать PostMedia: `from .models import Post, PostMedia`
- [ ] Создать класс `PostMediaInline(admin.TabularInline)` **ДО** класса PostAdmin
- [ ] Установить `model = PostMedia`
- [ ] Установить `extra = 1` — показывать 1 пустую форму для загрузки нового файла
- [ ] Установить `fields = ['file', 'preview_image', 'markdown_link', 'original_filename', 'media_type', 'created_at']`
- [ ] Установить `readonly_fields = ['preview_image', 'markdown_link', 'original_filename', 'media_type', 'created_at']`

### Реализация метода preview_image

- [ ] Импортировать `format_html` в начале файла: `from django.utils.html import format_html`
- [ ] Создать метод `preview_image(self, obj)` внутри PostMediaInline:
- [ ] Проверить что `obj.pk` существует (файл сохранён)
- [ ] Проверить что `obj.media_type == 'image'`
- [ ] Вернуть HTML с тегом img: `format_html('<img src="{}" style="max-width: 200px; max-height: 150px;" />', obj.file.url)`
- [ ] Если не изображение, вернуть иконку или текст типа файла
- [ ] Добавить декоратор `@admin.display(description="Превью")`

### Реализация метода markdown_link

- [ ] Создать метод `markdown_link(self, obj)` внутри PostMediaInline:
- [ ] Если `obj.pk` не существует, вернуть "—"
- [ ] Сформировать Markdown-ссылку: `link = f"![{obj.original_filename}]({obj.file.url})"`
- [ ] Вернуть readonly input с ссылкой: `format_html('<input type="text" value="{}" readonly style="width: 100%;" />', link)`
- [ ] Добавить декоратор `@admin.display(description="Markdown ссылка")`

### Интеграция в PostAdmin

- [ ] В классе PostAdmin найти атрибут `fieldsets` или список полей
- [ ] Добавить `inlines = [PostMediaInline]` **после** fieldsets
- [ ] Убедиться что `PostMediaInline` определён **до** PostAdmin в файле

### Регистрация PostMedia в админке (опционально)

- [ ] Создать отдельный `PostMediaAdmin` для просмотра всех медиа-файлов (включая "сирот")
- [ ] Установить `list_display = ['original_filename', 'post', 'media_type', 'created_at']`
- [ ] Установить `list_filter = ['media_type', 'created_at']`
- [ ] Установить `search_fields = ['original_filename', 'post__title']`
- [ ] Зарегистрировать: `@admin.register(PostMedia)` или `admin.site.register(PostMedia, PostMediaAdmin)`

### Тестирование

- [ ] Открыть админку Django, перейти в редактирование любого поста
- [ ] Проверить что внизу формы появился блок "Медиа-файлы" с TabularInline
- [ ] Загрузить тестовое изображение через форму
- [ ] Проверить что preview отображается корректно
- [ ] Проверить что в "Markdown ссылка" появился готовый код с правильным URL
- [ ] Скопировать ссылку, вставить в поле content, сохранить пост
- [ ] Открыть пост на сайте — изображение должно отображаться

## Коммит

**Формат:** `phase 3.6 feat: Добавлен PostMediaInline в админку с preview и Markdown-ссылками`

**Описание:**

```
phase 3.6 feat: Добавлен PostMediaInline в админку с preview и Markdown-ссылками

- Создан PostMediaInline для управления медиа прямо из формы поста
- Реализован метод preview_image для отображения превью изображений
- Реализован метод markdown_link для копирования готовых ссылок
- Настроены readonly_fields для вычисляемых значений
- Интегрирован PostMediaInline в PostAdmin через inlines
```
