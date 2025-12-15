# Фаза 3.7: Админка для Category и Tag

## Цель

Создать `CategoryAdmin` и `TagAdmin` для удобного управления таксономией контента, интегрировать в `PostAdmin` через filter_horizontal и autocomplete.

## Контекст

**Текущее состояние:** Модели Category и Tag созданы и имеют миграции. В [blog/admin.py](../../../blog/admin.py) они не зарегистрированы.

**Проблема:** Невозможно создавать категории и теги через админку. В форме Post нет удобного способа выбрать категорию или теги.

**Технологии:** Django Admin ModelAdmin, `prepopulated_fields` для авто-заполнения slug, `filter_horizontal` для красивого выбора M2M, `autocomplete_fields` для быстрого поиска FK.

**Философия:** Справочники должны управляться легко. Категории редактируются редко (администратор создаёт структуру заранее), теги создаются на лету (будет Tom Select в Phase 3.24).

**Важно:** `autocomplete_fields` требует поле `search_fields` в админке связанной модели. Без search_fields автокомплит не работает.

## Задачи

### Создание CategoryAdmin

- [ ] В [blog/admin.py](../../../blog/admin.py) импортировать Category и Tag: `from .models import Post, PostMedia, Category, Tag`
- [ ] Создать класс `CategoryAdmin(ModelAdmin)` с декоратором `@admin.register(Category)`
- [ ] Установить `list_display = ['name', 'slug', 'display_cover', 'created_at']`
- [ ] Установить `prepopulated_fields = {'slug': ('name',)}`
- [ ] Установить `search_fields = ['name', 'slug']` — нужно для autocomplete
- [ ] Установить `ordering = ['name']`

### Реализация display_cover для Category

- [ ] Создать метод `display_cover(self, obj)` в CategoryAdmin:
- [ ] Проверить что `obj.default_cover` существует
- [ ] Вернуть превью: `format_html('<img src="{}" style="max-width: 80px; max-height: 60px;" />', obj.default_cover.url)`
- [ ] Если обложки нет, вернуть "—"
- [ ] Добавить декоратор `@admin.display(description="Обложка")`

### Создание TagAdmin

- [ ] Создать класс `TagAdmin(ModelAdmin)` с декоратором `@admin.register(Tag)`
- [ ] Установить `list_display = ['name', 'slug', 'posts_count', 'created_at']`
- [ ] Установить `prepopulated_fields = {'slug': ('name',)}`
- [ ] Установить `search_fields = ['name', 'slug']` — нужно для Tom Select
- [ ] Установить `ordering = ['name']`

### Реализация posts_count для Tag

- [ ] Создать метод `posts_count(self, obj)` в TagAdmin:
- [ ] Вернуть количество постов: `return obj.posts.count()`
- [ ] Добавить декоратор `@admin.display(description="Количество постов")`
- [ ] Для оптимизации добавить `def get_queryset(self, request)` с annotate:

```python
def get_queryset(self, request):
    qs = super().get_queryset(request)
    return qs.annotate(Count('posts'))
```

### Интеграция в PostAdmin

- [ ] В PostAdmin найти поле category в fieldsets
- [ ] Добавить `autocomplete_fields = ['category']` **после** fieldsets
- [ ] Найти поле tags или добавить в соответствующий fieldset
- [ ] Добавить `filter_horizontal = ['tags']` — красивый виджет выбора M2M
- [ ] Альтернатива filter_horizontal: `raw_id_fields = ['tags']` — компактнее, но менее удобно

### Обновление fieldsets в PostAdmin

- [ ] Добавить fieldset "Таксономия":

```python
("Таксономия", {
    "fields": ("category", "tags")
}),
```

- [ ] Расположить между "Контент" и "Метаданные"

### Тестирование

- [ ] Открыть админку, убедиться что появились разделы Category и Tag
- [ ] Создать 3-5 категорий через CategoryAdmin
- [ ] Проверить что slug генерируется автоматически при вводе name
- [ ] Создать 5-7 тегов через TagAdmin
- [ ] Открыть форму редактирования поста
- [ ] Проверить что поле category имеет autocomplete (лупа для поиска)
- [ ] Проверить что поле tags имеет filter_horizontal (два списка со стрелками)
- [ ] Добавить категорию и теги к посту, сохранить
- [ ] Проверить обратную связь: в CategoryAdmin открыть категорию, убедиться что пост отображается

## Коммит

**Формат:** `phase 3.7 feat: Добавлены CategoryAdmin и TagAdmin с интеграцией в PostAdmin`

**Описание:**

```
phase 3.7 feat: Добавлены CategoryAdmin и TagAdmin с интеграцией в PostAdmin

- Создан CategoryAdmin с prepopulated_fields и display_cover
- Создан TagAdmin с posts_count и аннотацией для оптимизации
- Настроен autocomplete_fields для category в PostAdmin
- Настроен filter_horizontal для tags в PostAdmin
- Добавлены search_fields для поддержки автокомплита
```
