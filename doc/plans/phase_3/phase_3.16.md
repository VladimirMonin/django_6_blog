# Фаза 3.16: Unfold action "Пересоздать HTML"

## Цель

Добавить кастомный action в `PostAdmin` для пересоздания HTML выбранных постов через UI админки без использования терминала.

## Контекст

**Текущее состояние:** В [blog/admin.py](../../../blog/admin.py) есть actions `publish_posts` и `unpublish_posts`. Есть management команда `regenerate_html` но она требует терминал.

**Проблема:** Админ должен иметь возможность обновить HTML постов через админку — выбрать несколько постов, нажать action "Пересоздать HTML". Это удобнее чем идти в терминал.

**Решение:** Django admin action — метод в PostAdmin с декоратором `@admin.action`, который вызывает `save()` для выбранных постов.

**Технологии:** Django admin actions, messages framework для уведомлений.

**Философия:** "UI First". Админ не должен знать про management команды для рутинных операций. Всё что можно сделать через UI — делается через UI.

**Важно:** Admin actions получают QuerySet выбранных объектов. Не нужно делать `all()` — работаем с переданным QuerySet.

## Задачи

### Создание action regenerate_html_action

- [ ] Открыть [blog/admin.py](../../../blog/admin.py)
- [ ] Найти класс `PostAdmin`
- [ ] Добавить метод с декоратором `@admin.action`:

```python
@admin.action(description="Пересоздать HTML для выбранных постов")
def regenerate_html_action(self, request, queryset):
    """Пересоздаёт content_html для выбранных постов."""
    updated = 0
    errors = 0
    
    for post in queryset:
        try:
            post.save()  # Триггернет convert_markdown_to_html
            updated += 1
        except Exception as e:
            errors += 1
            self.message_user(
                request,
                f'Ошибка для поста "{post.title}": {e}',
                level='warning'
            )
    
    if updated > 0:
        self.message_user(
            request,
            f'Успешно обновлено {updated} пост(ов)',
            level='success'
        )
    
    if errors > 0:
        self.message_user(
            request,
            f'Ошибок: {errors}',
            level='error'
        )
```

### Регистрация action

- [ ] Найти атрибут `actions` в PostAdmin
- [ ] Добавить новый action в список:

```python
actions = [
    'publish_posts',
    'unpublish_posts',
    'regenerate_html_action'
]
```

### Оптимизация для больших выборок

- [ ] Добавить проверку на количество постов:

```python
@admin.action(description="Пересоздать HTML для выбранных постов")
def regenerate_html_action(self, request, queryset):
    count = queryset.count()
    
    if count > 100:
        self.message_user(
            request,
            f'Слишком много постов ({count}). Используйте management команду regenerate_html для больших выборок.',
            level='warning'
        )
        return
    
    # ... остальной код
```

### Добавление прогресс-информации

- [ ] Для длительных операций можно показывать промежуточный прогресс:

```python
for i, post in enumerate(queryset, 1):
    try:
        post.save()
        updated += 1
        
        # Каждые 10 постов показываем прогресс
        if i % 10 == 0:
            self.message_user(
                request,
                f'Обработано {i}/{count} постов...',
                level='info'
            )
    except Exception as e:
        errors += 1
```

### Тестирование action

- [ ] Открыть админку Django
- [ ] Перейти в список постов
- [ ] Выбрать 2-3 поста через checkbox
- [ ] В выпадающем списке actions выбрать "Пересоздать HTML для выбранных постов"
- [ ] Нажать "Выполнить"
- [ ] Проверить что появилось сообщение об успехе
- [ ] Проверить что `content_html` обновился (можно через preview в админке)

### Тестирование с ошибкой

- [ ] Создать пост с невалидным Markdown (если возможно вызвать ошибку в конвертере)
- [ ] Выбрать этот пост и нормальный пост
- [ ] Запустить action
- [ ] Проверить что показаны и успешные и ошибочные посты
- [ ] Проверить что нормальный пост обновился несмотря на ошибку в другом

### Тестирование больших выборок

- [ ] Создать 100+ тестовых постов (через management команду create_posts)
- [ ] Выбрать "все посты" в админке
- [ ] Запустить action
- [ ] Должно показаться предупреждение о большом количестве
- [ ] Проверить что action не выполнился

## Коммит

**Формат:** `phase 3.16 feat: Добавлен admin action для пересоздания HTML в PostAdmin`

**Описание:**

```
phase 3.16 feat: Добавлен admin action для пересоздания HTML в PostAdmin

- Создан action regenerate_html_action в PostAdmin
- Обработка ошибок для отдельных постов
- Сообщения об успехе/ошибках через messages framework
- Защита от обработки слишком больших выборок (>100 постов)
- Возможность обновить HTML выбранных постов через UI админки
```
