# Фаза 3.12: Management command import_post

## Цель

Создать management command `python manage.py import_post <path>` для импорта постов из ZIP-архивов Obsidian через командную строку с опциями категории, тегов, статуса.

## Контекст

**Текущее состояние:** В [blog/services/](../../../blog/services/) есть `archive_handler.py` для работы с ZIP и препроцессор для обработки ссылок. Нет высокоуровневого API для импорта постов.

**Проблема:** Админу нужен простой способ импортировать Obsidian-заметку: `python manage.py import_post article.zip --title "My Article"`. Сейчас это требует написания скриптов в Django shell.

**Решение:** Django management command с argparse для парсинга аргументов, использующий archive_handler и PostMedia для импорта.

**Технологии:** Django management commands (наследование от `BaseCommand`), argparse для опций, Django ORM для создания объектов, `transaction.atomic()` для атомарности операции.

**Философия:** "One Command Import". Загрузил ZIP, указал заголовок, получил готовый пост со всеми медиа и рабочими ссылками.

**Важно:** Management команды создаются в `blog/management/commands/`. Структура: `blog/management/__init__.py`, `blog/management/commands/__init__.py`, `blog/management/commands/import_post.py`.

## Задачи

### Создание структуры management

- [ ] Проверить что существует `blog/management/` (уже есть из Phase 2)
- [ ] Проверить что существует `blog/management/commands/` (уже есть)
- [ ] Убедиться что есть `__init__.py` в обеих папках

### Создание команды import_post.py

- [ ] Создать файл `blog/management/commands/import_post.py`
- [ ] Импортировать необходимые модули:

```python
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.models import User
from pathlib import Path
from blog.models import Post, PostMedia, Category, Tag
from blog.services.archive_handler import extract_zip, find_markdown_file, find_media_files, cleanup_temp
```

### Создание класса Command

- [ ] Создать класс `Command(BaseCommand)`:
- [ ] Добавить `help = 'Импорт поста из ZIP-архива Obsidian'`
- [ ] Реализовать метод `add_arguments(self, parser)`:

```python
def add_arguments(self, parser):
    parser.add_argument('archive_path', type=str, help='Путь к ZIP-архиву')
    parser.add_argument('--title', type=str, help='Заголовок поста (обязательно)')
    parser.add_argument('--category', type=str, help='Slug категории')
    parser.add_argument('--tags', nargs='+', help='Список тегов через пробел')
    parser.add_argument('--status', choices=['draft', 'review', 'published', 'archived'], default='draft')
    parser.add_argument('--access-level', choices=['free', 'member', 'paid'], default='free')
    parser.add_argument('--author', type=str, help='Username автора (default: первый суперпользователь)')
    parser.add_argument('--dry-run', action='store_true', help='Тестовый режим без сохранения')
```

### Реализация handle()

- [ ] Создать метод `handle(self, *args, **options)`:
- [ ] Получить параметры:

```python
archive_path = Path(options['archive_path'])
title = options.get('title')
dry_run = options['dry_run']

if not title:
    raise CommandError('--title обязателен')

if not archive_path.exists():
    raise CommandError(f'Файл не найден: {archive_path}')
```

- [ ] Получить автора:

```python
author_username = options.get('author')
if author_username:
    try:
        author = User.objects.get(username=author_username)
    except User.DoesNotExist:
        raise CommandError(f'Пользователь не найден: {author_username}')
else:
    author = User.objects.filter(is_superuser=True).first()
```

### Обработка архива

- [ ] Распаковать архив:

```python
self.stdout.write('Распаковка архива...')
temp_dir = extract_zip(archive_path)
```

- [ ] Найти Markdown файл:

```python
md_file = find_markdown_file(temp_dir)
if not md_file:
    cleanup_temp(temp_dir)
    raise CommandError('Markdown файл не найден в архиве')

content = md_file.read_text(encoding='utf-8')
self.stdout.write(f'Найден Markdown: {md_file.name} ({len(content)} символов)')
```

- [ ] Найти медиа-файлы:

```python
media_files = find_media_files(temp_dir)
self.stdout.write(f'Найдено медиа-файлов: {len(media_files)}')
```

### Создание поста

- [ ] Использовать `transaction.atomic()` для атомарности:

```python
with transaction.atomic():
    # Создать пост
    post = Post(
        title=title,
        content=content,
        status=options['status'],
        access_level=options['access_level'],
        author=author
    )
    
    if dry_run:
        self.stdout.write(self.style.WARNING('DRY RUN: Пост НЕ создан'))
    else:
        post.save()
        self.stdout.write(self.style.SUCCESS(f'Пост создан: {post.slug}'))
```

- [ ] Добавить категорию:

```python
if options.get('category'):
    try:
        category = Category.objects.get(slug=options['category'])
        post.category = category
        post.save(update_fields=['category'])
    except Category.DoesNotExist:
        self.stdout.write(self.style.WARNING(f'Категория не найдена: {options["category"]}'))
```

- [ ] Добавить теги:

```python
if options.get('tags'):
    for tag_name in options['tags']:
        tag, created = Tag.objects.get_or_create(name=tag_name, defaults={'slug': tag_name.lower()})
        post.tags.add(tag)
        if created:
            self.stdout.write(f'Создан тег: {tag_name}')
```

### Загрузка медиа-файлов

- [ ] В том же transaction:

```python
for file_path, mime_type in media_files:
    with open(file_path, 'rb') as f:
        media = PostMedia(
            post=post,
            original_filename=file_path.name
        )
        media.file.save(file_path.name, f, save=True)
        self.stdout.write(f'Загружен: {file_path.name}')
```

- [ ] После загрузки медиа, пересохранить пост чтобы препроцессор обновил ссылки:

```python
post.save()  # Триггернет препроцессор
```

### Очистка

- [ ] После transaction добавить:

```python
cleanup_temp(temp_dir)
self.stdout.write(self.style.SUCCESS(f'Импорт завершён! Пост: /post/{post.pk}/'))
```

### Обработка ошибок

- [ ] Обернуть всё в try-except:

```python
try:
    # ... весь код импорта
except Exception as e:
    cleanup_temp(temp_dir)
    raise CommandError(f'Ошибка импорта: {e}')
```

### Тестирование

- [ ] Подготовить тестовый ZIP из Obsidian с:
  - Файл `article.md` с текстом и ссылками `![](image.png)`
  - Папка `attachments/` с `image.png`
- [ ] Запустить команду:

```bash
python manage.py import_post test.zip --title "Test Article" --status published
```

- [ ] Проверить что пост создан, медиа загружены, ссылки работают
- [ ] Тестировать опции:

```bash
python manage.py import_post test.zip --title "Test" --category python --tags django orm --author admin
```

- [ ] Тестировать dry-run:

```bash
python manage.py import_post test.zip --title "Test" --dry-run
```

### Тестирование edge cases

- [ ] ZIP без Markdown — должна быть ошибка
- [ ] ZIP без медиа — пост создаётся, медиа пусто
- [ ] Битый ZIP — должна быть ошибка
- [ ] Несуществующая категория — warning, пост без категории
- [ ] Несуществующий автор — ошибка

## Коммит

**Формат:** `phase 3.12 feat: Создана management команда import_post для импорта из ZIP`

**Описание:**

```
phase 3.12 feat: Создана management команда import_post для импорта из ZIP

- Создан blog/management/commands/import_post.py
- Поддержка опций: title, category, tags, status, access-level, author
- Добавлен dry-run режим для тестирования без сохранения
- Автоматическая загрузка всех медиа-файлов из архива
- Атомарность операции через transaction.atomic()
- Автоматическое обновление ссылок через препроцессор
```
