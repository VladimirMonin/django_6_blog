# Фаза 3.5: Модель PostMedia

## Цель

Создать модель `PostMedia` для хранения медиа-файлов (изображения, видео, аудио) с привязкой к постам и поддержкой оригинальных имён файлов.

## Контекст

**Текущее состояние:** В [blog/models.py](../../../blog/models.py) есть модели Post, Category, Tag. Нет способа загружать и хранить медиа-файлы, привязанные к постам.

**Проблема:** Django умеет хранить файлы через FileField, но нам нужна логика:

- Post-Centric Storage — файлы изолированы по постам в `media/posts/{slug}/`
- Сохранение оригинального имени файла для матчинга при импорте из Obsidian
- Авто-определение типа медиа (image/video/audio/document)
- Защита от случайного удаления — файлы помечаются "сиротами" при удалении поста (on_delete=SET_NULL)

**Технологии:** FileField (не ImageField, чтобы поддерживать видео/аудио), функция `upload_to` для динамических путей, `mimetypes` для определения типа файла.

**Философия:** PostMedia — обёртка вокруг физического файла. Это не просто путь, а объект с метаданными, который знает к какому посту он относится, как назывался изначально, и какого он типа.

**Важно:** `upload_to` должен быть функцией, а не строкой, чтобы формировать путь `posts/{slug}/` динамически. Функция принимает `(instance, filename)` и возвращает путь.

## Задачи

### Создание функции upload_to

- [ ] Перед классом PostMedia создать функцию `post_media_upload_path(instance, filename)`:
- [ ] Получить slug поста: `slug = instance.post.slug if instance.post else 'orphan'`
- [ ] Вернуть путь: `return f'posts/{slug}/{filename}'`
- [ ] Это обеспечит структуру `media/posts/my-post-slug/image.png`

### Создание модели PostMedia

- [ ] Импортировать `mimetypes` в начале файла: `import mimetypes`
- [ ] Создать класс `PostMedia` **ДО** изменения поля cover в Post
- [ ] Добавить поле `post` — ForeignKey('Post'), on_delete=models.SET_NULL, null=True, blank=True, related_name='media_files', verbose_name="Пост"
- [ ] Добавить поле `file` — FileField, upload_to=post_media_upload_path, verbose_name="Файл"
- [ ] Добавить поле `original_filename` — CharField, max_length=255, verbose_name="Оригинальное имя файла"
- [ ] Добавить поле `file_slug` — SlugField, max_length=255, blank=True, verbose_name="Slug файла"
- [ ] Добавить поле `media_type` — CharField, max_length=20, blank=True, verbose_name="Тип медиа"
- [ ] Добавить поле `created_at` — DateTimeField, auto_now_add=True

### Добавление choices для media_type

- [ ] Создать choices:

```python
IMAGE = 'image'
VIDEO = 'video'
AUDIO = 'audio'
DOCUMENT = 'document'

MEDIA_TYPE_CHOICES = [
    (IMAGE, 'Изображение'),
    (VIDEO, 'Видео'),
    (AUDIO, 'Аудио'),
    (DOCUMENT, 'Документ'),
]
```

- [ ] Обновить поле media_type: добавить `choices=MEDIA_TYPE_CHOICES`

### Реализация метода save()

- [ ] Переопределить метод `save()` в PostMedia:
- [ ] Если `original_filename` пустое, заполнить из `self.file.name`
- [ ] Если `file_slug` пустое, сгенерировать из `original_filename` через slugify
- [ ] Определить `media_type` автоматически:
  - Использовать `mimetypes.guess_type(self.file.name)[0]`
  - Если mime начинается с 'image/' → media_type = IMAGE
  - Если mime начинается с 'video/' → media_type = VIDEO
  - Если mime начинается с 'audio/' → media_type = AUDIO
  - Иначе → media_type = DOCUMENT
- [ ] Вызвать `super().save(*args, **kwargs)`

### Настройка Meta и методов

- [ ] Добавить `class Meta`:
- [ ] `ordering = ['-created_at']`
- [ ] `verbose_name = "Медиа-файл"`
- [ ] `verbose_name_plural = "Медиа-файлы"`
- [ ] `unique_together = [['post', 'original_filename']]` — защита от дублей в одном посте
- [ ] Реализовать `__str__(self)`: `return f"{self.original_filename} ({self.get_media_type_display()})"`

### Создание миграции

- [ ] Запустить `python manage.py makemigrations blog`
- [ ] Проверить миграцию — должна создаться таблица `blog_postmedia`
- [ ] Применить миграцию: `python manage.py migrate`
- [ ] Проверить через Django shell: `from blog.models import PostMedia` → `PostMedia.objects.count()` должен вернуть 0

### Добавление поля cover в Post

- [ ] Вернуться к модели Post
- [ ] Добавить поле `cover` — ForeignKey('PostMedia'), on_delete=models.SET_NULL, null=True, blank=True, related_name='cover_for_post', verbose_name="Обложка"
- [ ] Создать новую миграцию: `python manage.py makemigrations blog`
- [ ] Применить: `python manage.py migrate`

### Тестирование

- [ ] Через Django shell создать тестовый PostMedia
- [ ] Проверить что `upload_to` работает — файл сохраняется в `media/posts/{slug}/`
- [ ] Проверить авто-определение media_type для PNG, MP4, MP3 файлов
- [ ] Проверить что `original_filename` сохраняется корректно
- [ ] Проверить unique_together — попытаться создать два файла с одинаковым именем в одном посте (должна быть ошибка)

## Коммит

**Формат:** `phase 3.5 feat: Создана модель PostMedia для хранения медиа-файлов`

**Описание:**

```
phase 3.5 feat: Создана модель PostMedia для хранения медиа-файлов

- Создана модель PostMedia с полями post, file, original_filename, file_slug, media_type
- Реализована функция upload_to для динамических путей posts/{slug}/
- Авто-определение media_type через mimetypes
- Добавлено поле cover в Post как FK на PostMedia
- Установлен unique_together для защиты от дублей
- Создана и применена миграция
```
