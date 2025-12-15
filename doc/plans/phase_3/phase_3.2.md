# Фаза 3.2: Модель Category

## Цель

Создать модель `Category` для иерархической организации контента блога с поддержкой дефолтных обложек.

## Контекст

**Текущее состояние:** В [blog/models.py](../../../blog/models.py) существует только модель `Post` без связей с категориями. Все посты существуют в одном "плоском" списке без группировки.

**Проблема:** Невозможно организовать контент тематически (Python, Django, Frontend, DevOps). В будущем это критично для LMS — курс должен быть привязан к категории "Образование", а статья — к "Туториалы".

**Технологии:** Django ORM, `SlugField` для SEO-дружественных URL, `FileField` для обложек, `prepopulated_fields` в админке для авто-генерации slug.

**Философия:** Категория — это не просто метка, а полноценная сущность с собственной страницей, описанием и обложкой. Категория может иметь дефолтную обложку, которая используется для постов без собственной обложки.

**Важно:** В Django 6 поведение слагов не изменилось — `SlugField` с `unique=True` по-прежнему требует ручной обработки коллизий или переопределения `save()` для авто-инкремента.

## Задачи

### Создание модели Category

- [ ] Открыть [blog/models.py](../../../blog/models.py)
- [ ] Добавить импорт `from django.db import models` (уже есть)
- [ ] Создать класс `Category` **ДО** класса `Post` (чтобы можно было сразу добавить FK в Post)
- [ ] Добавить поле `name` — CharField, max_length=100, unique=True, verbose_name="Название"
- [ ] Добавить поле `slug` — SlugField, max_length=100, unique=True, verbose_name="URL-slug"
- [ ] Добавить поле `description` — TextField, blank=True, verbose_name="Описание"
- [ ] Добавить поле `default_cover` — FileField, upload_to='categories/', blank=True, null=True, verbose_name="Обложка по умолчанию"
- [ ] Добавить поле `created_at` — DateTimeField, auto_now_add=True

### Настройка Meta и методов

- [ ] Добавить `class Meta` с ordering по имени: `ordering = ['name']`
- [ ] Добавить `verbose_name = "Категория"` и `verbose_name_plural = "Категории"`
- [ ] Реализовать метод `__str__(self)` возвращающий `self.name`
- [ ] Реализовать метод `get_absolute_url(self)` с reverse на `'category_detail'` и kwargs `{'slug': self.slug}`

### Создание миграции

- [ ] Запустить `python manage.py makemigrations blog` в терминале
- [ ] Проверить созданный файл миграции в `blog/migrations/`
- [ ] Убедиться что миграция содержит создание модели Category со всеми полями
- [ ] Применить миграцию: `python manage.py migrate`
- [ ] Проверить через Django shell что модель создана: `python manage.py shell` → `from blog.models import Category` → `Category.objects.count()` должен вернуть 0

### Тестовые данные (опционально на этом этапе)

- [ ] Создать 3-5 категорий вручную через Django shell или админку (если уже настроен CategoryAdmin)
- [ ] Примеры категорий: "Python", "Django", "Frontend", "DevOps", "Общее"
- [ ] Slug генерировать транслитерацией: "Python" → "python", "Django" → "django"

## Коммит

**Формат:** `phase 3.2 feat: Добавлена модель Category для организации контента`

**Описание:**

```
phase 3.2 feat: Добавлена модель Category для организации контента

- Создана модель Category с полями name, slug, description, default_cover
- Реализованы методы __str__ и get_absolute_url
- Создана и применена миграция для Category
- Поле upload_to='categories/' для хранения обложек категорий
```
