# Фаза 3.15: Management command regenerate_html

## Цель

Создать management command `python manage.py regenerate_html` для пересоздания `content_html` всех постов с опциями фильтрации по slug, категории, дате.

## Контекст

**Текущее состояние:** В [blog/management/commands/](../../../blog/management/commands/) есть команды create_posts и import_post. Нет способа обновить HTML всех постов при изменении процессоров.

**Проблема:** Если мы добавим новый HTML-процессор (например, для видео-плееров) или изменим стили таблиц, старые посты останутся с устаревшим HTML. Нужно пересоздать `content_html` для всех постов.

**Решение:** Management command который вызывает `Post.save()` для каждого поста, триггеря `convert_markdown_to_html()`. С опциями для выборочной обработки (только draft, только категория "Python").

**Технологии:** Django management commands, QuerySet filtering, bulk operations для оптимизации.

**Философия:** "Regenerate on Demand". Не делаем автоматический пересчёт всех постов при изменении процессора — даём админу контроль когда это делать.

**Важно:** Для больших БД (1000+ постов) используем `iterator()` чтобы не загружать всё в память, и `bulk_update()` для оптимизации записи.

## Задачи

### Создание команды regenerate_html.py

- [ ] Создать файл `blog/management/commands/regenerate_html.py`
- [ ] Импортировать модули:

```python
from django.core.management.base import BaseCommand
from blog.models import Post
from django.db.models import Q
from datetime import datetime
```

### Создание класса Command

- [ ] Создать класс `Command(BaseCommand)`:
- [ ] `help = 'Пересоздать HTML контент для постов'`
- [ ] Реализовать `add_arguments(self, parser)`:

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--slug',
        type=str,
        help='Обновить конкретный пост по slug'
    )
    parser.add_argument(
        '--category',
        type=str,
        help='Обновить посты конкретной категории (slug)'
    )
    parser.add_argument(
        '--status',
        choices=['draft', 'review', 'published', 'archived'],
        help='Обновить посты с определённым статусом'
    )
    parser.add_argument(
        '--date-from',
        type=str,
        help='Обновить посты созданные после даты (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--date-to',
        type=str,
        help='Обновить посты созданные до даты (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Обновить ВСЕ посты (требует подтверждения)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Пропустить подтверждение для --all'
    )
```

### Реализация handle()

- [ ] Создать метод `handle(self, *args, **options)`:
- [ ] Построить QuerySet на основе опций:

```python
queryset = Post.objects.all()

if options['slug']:
    queryset = queryset.filter(slug=options['slug'])
elif options['category']:
    queryset = queryset.filter(category__slug=options['category'])
elif options['status']:
    queryset = queryset.filter(status=options['status'])
    
if options['date_from']:
    date_from = datetime.strptime(options['date_from'], '%Y-%m-%d').date()
    queryset = queryset.filter(created_at__gte=date_from)
    
if options['date_to']:
    date_to = datetime.strptime(options['date_to'], '%Y-%m-%d').date()
    queryset = queryset.filter(created_at__lte=date_to)
```

- [ ] Проверить что хоть один фильтр указан:

```python
if not any([options['slug'], options['category'], options['status'], 
            options['date_from'], options['date_to'], options['all']]):
    self.stdout.write(self.style.ERROR('Укажите хотя бы один фильтр или --all'))
    return
```

### Подтверждение для --all

- [ ] Если `--all` без `--force`:

```python
if options['all'] and not options['force']:
    count = queryset.count()
    confirm = input(f'Обновить {count} постов? (yes/no): ')
    if confirm.lower() != 'yes':
        self.stdout.write('Отменено')
        return
```

### Обработка постов

- [ ] Использовать iterator для больших QuerySet:

```python
total = queryset.count()
self.stdout.write(f'Обновление {total} постов...')

updated = 0
for post in queryset.iterator(chunk_size=100):
    post.save()  # Триггернет convert_markdown_to_html
    updated += 1
    
    if updated % 10 == 0:
        self.stdout.write(f'Обработано: {updated}/{total}')

self.stdout.write(self.style.SUCCESS(f'Успешно обновлено: {updated} постов'))
```

### Альтернативная реализация с bulk_update

- [ ] Для оптимизации можно использовать `bulk_update`:

```python
posts = list(queryset.iterator(chunk_size=100))
for post in posts:
    # Генерируем HTML но не сохраняем
    from blog.services import convert_markdown_to_html
    post.content_html = convert_markdown_to_html(post.content, post=post)

# Сохраняем одним запросом
Post.objects.bulk_update(posts, ['content_html'], batch_size=100)
```

### Обработка ошибок

- [ ] Обернуть обработку в try-except:

```python
try:
    for post in queryset.iterator():
        try:
            post.save()
            updated += 1
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Ошибка для поста {post.slug}: {e}')
            )
except Exception as e:
    self.stdout.write(self.style.ERROR(f'Критическая ошибка: {e}'))
```

### Тестирование

- [ ] Создать несколько тестовых постов разных статусов и категорий
- [ ] Запустить команду с разными опциями:

```bash
# Один пост
python manage.py regenerate_html --slug my-post

# Все черновики
python manage.py regenerate_html --status draft

# Посты категории Python
python manage.py regenerate_html --category python

# Посты за 2025 год
python manage.py regenerate_html --date-from 2025-01-01 --date-to 2025-12-31

# Все посты (с подтверждением)
python manage.py regenerate_html --all

# Все посты (без подтверждения)
python manage.py regenerate_html --all --force
```

- [ ] Проверить что `content_html` обновился
- [ ] Проверить что посты отображаются корректно на сайте

### Добавление прогресс-бара (опционально)

- [ ] Установить библиотеку tqdm (если не против зависимости):

```python
from tqdm import tqdm

for post in tqdm(queryset.iterator(), total=total, desc="Регенерация HTML"):
    post.save()
```

## Коммит

**Формат:** `phase 3.15 feat: Создана команда regenerate_html для пересоздания контента`

**Описание:**

```
phase 3.15 feat: Создана команда regenerate_html для пересоздания контента

- Создан blog/management/commands/regenerate_html.py
- Поддержка фильтрации по slug, category, status, date
- Подтверждение для обработки всех постов через --all --force
- Использование iterator для оптимизации памяти
- Обработка ошибок для отдельных постов без остановки процесса
```
