# Фаза 3.18: Обновление PostAdmin — расширенные фильтры

## Цель

Добавить фильтры и поиск в `PostAdmin` для удобной навигации по постам: category, tags, status, access_level, author, date_hierarchy.

## Контекст

**Текущее состояние:** В [blog/admin.py](../../../blog/admin.py) PostAdmin имеет только `list_filter = ['is_published', 'created_at']`.

**Проблема:** Невозможно отфильтровать посты по новым полям: категории, тегам, статусу, автору. При большом количестве постов это критично.

**Решение:** Добавить `list_filter` для всех новых полей, настроить `search_fields`, `date_hierarchy` для фильтрации по датам.

## Задачи

### Обновление list_filter

- [ ] Открыть [blog/admin.py](../../../blog/admin.py), найти PostAdmin
- [ ] Заменить `list_filter` на:

```python
list_filter = [
    'status',
    'access_level',
    'category',
    'tags',
    'author',
    'created_at',
    'updated_at',
]
```

### Настройка search_fields

- [ ] Обновить `search_fields`:

```python
search_fields = [
    'title',
    'content',
    'excerpt',
    'author__username',
    'category__name',
    'tags__name',
]
```

### Добавление date_hierarchy

- [ ] Добавить `date_hierarchy = 'created_at'` для фильтрации по году/месяцу/дню

### Обновление list_display

- [ ] Добавить новые поля в `list_display`:

```python
list_display = [
    'title',
    'author',
    'category',
    'status',
    'rating',
    'views_count',
    'display_created_at',
    'display_published'
]
```

### Тестирование

- [ ] Открыть админку, перейти в список постов
- [ ] Проверить фильтры справа — должны отображаться все новые поля
- [ ] Проверить поиск по автору, категории, тегам
- [ ] Проверить date_hierarchy сверху списка

## Коммит

```
phase 3.18 feat: Добавлены расширенные фильтры в PostAdmin

- Обновлён list_filter: status, access_level, category, tags, author
- Обновлён search_fields для поиска по автору, категории, тегам
- Добавлен date_hierarchy для фильтрации по дате
- Обновлён list_display с новыми полями
```
