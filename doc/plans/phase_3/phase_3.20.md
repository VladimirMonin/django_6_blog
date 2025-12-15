# Фаза 3.20: Отображение cover и excerpt в списке постов

## Цель

Добавить методы `display_cover()` и `display_excerpt()` в PostAdmin для отображения превью обложки и аннотации в list_display.

## Контекст

**Текущее состояние:** В [blog/admin.py](../../../blog/admin.py) list_display показывает только текстовые поля.

**Проблема:** Невозможно визуально оценить пост в списке — нет обложки, не видно аннотации. Нужны кастомные методы для rich display.

## Задачи

### display_cover

- [ ] Добавить метод в PostAdmin:

```python
@admin.display(description="Обложка")
def display_cover(self, obj):
    if obj.cover and obj.cover.file:
        return format_html(
            '<img src="{}" style="max-width: 80px; max-height: 60px;" />',
            obj.cover.file.url
        )
    return "—"
```

- [ ] Добавить в list_display: `'display_cover'`

### display_excerpt

- [ ] Добавить метод:

```python
@admin.display(description="Аннотация")
def display_excerpt(self, obj):
    if obj.excerpt:
        return obj.excerpt[:100] + '...' if len(obj.excerpt) > 100 else obj.excerpt
    return "—"
```

- [ ] Добавить в list_display: `'display_excerpt'`

### Тестирование

- [ ] Проверить что обложка отображается как thumbnail
- [ ] Проверить что excerpt обрезается до 100 символов
- [ ] Проверить отображение для постов без обложки/excerpt

## Коммит

```
phase 3.20 feat: Добавлено отображение cover и excerpt в list_display

- Реализован display_cover для превью обложки в списке
- Реализован display_excerpt для краткого описания
- Обновлён list_display с новыми методами
```
