# Фаза 3.3: Модель Tag и связь с Post

## Цель

Создать модель `Tag` и установить связь ManyToMany с моделью `Post` для гибкой категоризации контента.

## Контекст

**Текущее состояние:** В [blog/models.py](../../../blog/models.py) есть модели `Post` и `Category` (после Phase 3.2). Категория — это жесткая иерархия (один пост = одна категория). Тегов пока нет.

**Проблема:** Категории ограничивают — пост про Django + PostgreSQL нельзя разместить одновременно в "Django" и "Базы данных". Теги решают эту проблему: один пост может иметь множество тегов (django, postgres, orm, tutorial).

**Технологии:** Django ORM ManyToManyField, промежуточная таблица `post_tags` создаётся автоматически через `through=` (не указываем — Django сам создаст).

**Философия:** Теги — это облегчённая таксономия. Категория описывает "что это" (туториал, статья, курс), а теги — "о чем это" (django, python, api, docker). Теги создаются на лету, категории — заранее.

**Важно:** В Django 6 ManyToManyField не требует null=True (это поле не хранится в таблице Post, а в связующей таблице). Ошибка `null=True` на M2M — частая ошибка новичков.

## Задачи

### Создание модели Tag

- [ ] Открыть [blog/models.py](../../../blog/models.py)
- [ ] Добавить класс `Tag` **ДО** класса `Post` (или после Category, до изменения Post)
- [ ] Добавить поле `name` — CharField, max_length=50, unique=True, verbose_name="Название"
- [ ] Добавить поле `slug` — SlugField, max_length=50, unique=True, verbose_name="URL-slug"
- [ ] Добавить поле `created_at` — DateTimeField, auto_now_add=True

### Настройка Meta и методов Tag

- [ ] Добавить `class Meta` с ordering по имени: `ordering = ['name']`
- [ ] Добавить `verbose_name = "Тег"` и `verbose_name_plural = "Теги"`
- [ ] Реализовать метод `__str__(self)` возвращающий `self.name`
- [ ] Реализовать метод `get_absolute_url(self)` с reverse на `'tag_detail'` и kwargs `{'slug': self.slug}`

### Добавление связи tags в Post

- [ ] В модели `Post` добавить поле `tags` — ManyToManyField
- [ ] Параметры: `ManyToManyField('Tag', blank=True, related_name='posts', verbose_name="Теги")`
- [ ] **НЕ добавлять** `null=True` (это ошибка для M2M)
- [ ] `blank=True` позволяет сохранять пост без тегов
- [ ] `related_name='posts'` позволяет делать `tag.posts.all()` для получения всех постов тега

### Создание миграций

- [ ] Запустить `python manage.py makemigrations blog`
- [ ] Должны создаться ДВЕ миграции или одна с двумя операциями:
  - CreateModel Tag
  - AddField tags в Post (или AlterField если модифицируем)
- [ ] Проверить файл миграции — должна быть создана таблица `blog_tag` и связующая таблица `blog_post_tags`
- [ ] Применить миграции: `python manage.py migrate`
- [ ] Проверить через Django shell: `from blog.models import Tag, Post` → `Tag.objects.count()` → должен вернуть 0

### Тестовые данные

- [ ] Создать 5-7 тегов через Django shell или админку
- [ ] Примеры тегов: "python", "django", "orm", "api", "tutorial", "postgres", "docker"
- [ ] Slug генерировать как есть (маленькими буквами, без транслитерации для английских слов)
- [ ] Проверить связь: взять тестовый пост, добавить ему 2-3 тега через `post.tags.add(tag1, tag2)`
- [ ] Проверить обратную связь: `tag.posts.all()` должен вернуть посты с этим тегом

## Коммит

**Формат:** `phase 3.3 feat: Добавлена модель Tag и связь ManyToMany с Post`

**Описание:**

```
phase 3.3 feat: Добавлена модель Tag и связь ManyToMany с Post

- Создана модель Tag с полями name, slug, created_at
- Добавлено поле tags в Post через ManyToManyField
- Реализованы методы __str__ и get_absolute_url для Tag
- Создана и применена миграция для Tag и связующей таблицы
- Настроен related_name='posts' для обратной связи
```
