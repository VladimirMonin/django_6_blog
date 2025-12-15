# Фаза 3.4: Расширение модели Post

## Цель

Добавить в модель `Post` поля для полноценного контент-управления и подготовки к LMS: автор, аннотация, обложка, статусы, уровни доступа, метрики.

## Контекст

**Текущее состояние:** В [blog/models.py](../../../blog/models.py) модель `Post` содержит только базовые поля: title, slug, content, content_html, created_at, updated_at, is_published. Нет связей с User, Category, метрик или статусов.

**Проблема:** Модель слишком простая для реального блога. Невозможно:

- Указать автора поста
- Добавить SEO-аннотацию для карточек и мета-тегов
- Установить обложку для соцсетей и preview
- Управлять жизненным циклом (черновик → на модерации → опубликован → архив)
- Ограничить доступ к контенту (бесплатный, для зарегистрированных, платный)
- Отслеживать популярность (просмотры, рейтинг)

**Технологии:** Django ORM ForeignKey для связей, TextField для длинных текстов, choices для статусов, FloatField для рейтинга с default=0.0.

**Философия:** Атомарность и полиморфизм контента. Один Post — универсальная единица, которая может быть статьёй блога (free + published) или уроком курса (paid + published). Добавляем все поля сейчас, чтобы избежать миграций в Phase 6.

**Важно:** Поле `cover` будет ForeignKey на PostMedia (который создадим в Phase 3.5), пока добавим его с `null=True` и создадим отдельную миграцию после PostMedia. Поле `category` — ForeignKey на Category (уже есть).

## Задачи

### Добавление полей в Post

- [ ] Импортировать `User` в начале файла: `from django.contrib.auth.models import User`
- [ ] Добавить поле `author` — ForeignKey(User), on_delete=models.SET_NULL, null=True, blank=True, related_name='posts', verbose_name="Автор"
- [ ] Добавить поле `excerpt` — TextField, blank=True, max_length=300, verbose_name="Аннотация", help_text="Краткое описание для preview и SEO"
- [ ] Добавить поле `category` — ForeignKey('Category'), on_delete=models.SET_NULL, null=True, blank=True, related_name='posts', verbose_name="Категория"
- [ ] Добавить поле `views_count` — PositiveIntegerField, default=0, verbose_name="Количество просмотров"
- [ ] Добавить поле `rating` — FloatField, default=0.0, verbose_name="Средний рейтинг"

### Добавление choices для статусов

- [ ] Создать класс `Status` с выбором статусов **внутри** класса Post (как вложенный класс или перед Post):

```python
DRAFT = 'draft'
REVIEW = 'review'
PUBLISHED = 'published'
ARCHIVED = 'archived'

STATUS_CHOICES = [
    (DRAFT, 'Черновик'),
    (REVIEW, 'На модерации'),
    (PUBLISHED, 'Опубликовано'),
    (ARCHIVED, 'Архив'),
]
```

- [ ] Добавить поле `status` — CharField, max_length=20, choices=STATUS_CHOICES, default=DRAFT, verbose_name="Статус"

### Добавление choices для уровней доступа

- [ ] Создать choices для access_level:

```python
FREE = 'free'
MEMBER = 'member'
PAID = 'paid'

ACCESS_LEVEL_CHOICES = [
    (FREE, 'Бесплатный'),
    (MEMBER, 'Только для зарегистрированных'),
    (PAID, 'Платный/Курс'),
]
```

- [ ] Добавить поле `access_level` — CharField, max_length=20, choices=ACCESS_LEVEL_CHOICES, default=FREE, verbose_name="Уровень доступа"

### Обновление метода save()

- [ ] Модифицировать метод `save()` в Post:
- [ ] Добавить генерацию `excerpt` из первого абзаца `content` если excerpt пустой
- [ ] Ограничить excerpt до 300 символов: `self.excerpt = self.content[:300] + '...'` если больше
- [ ] Удалить HTML-теги из excerpt (базовая очистка через regex или BeautifulSoup)

### Создание миграции

- [ ] Запустить `python manage.py makemigrations blog`
- [ ] Django спросит про default значения для существующих постов — выбрать опцию 1 (указать default в коде)
- [ ] Для author указать default=1 (предполагаем что есть суперпользователь с id=1) или null=True
- [ ] Проверить файл миграции — должны быть операции AddField для всех новых полей
- [ ] Применить миграцию: `python manage.py migrate`

### Обновление **str** и Meta

- [ ] Обновить `ordering` в Meta на `['-created_at', '-rating']` для сортировки по дате и рейтингу
- [ ] Обновить метод `__str__` чтобы включал статус: `return f"{self.title} [{self.get_status_display()}]"`

### Тестирование

- [ ] Проверить через Django shell создание поста с новыми полями
- [ ] Проверить что `is_published` больше не используется — заменён на `status`
- [ ] Обновить существующие тестовые посты: установить status=PUBLISHED, access_level=FREE
- [ ] Проверить что auto-генерация excerpt работает при сохранении пустого поста

## Коммит

**Формат:** `phase 3.4 feat: Расширена модель Post полями для LMS и контент-управления`

**Описание:**

```
phase 3.4 feat: Расширена модель Post полями для LMS и контент-управления

- Добавлены поля: author, excerpt, category, status, access_level
- Добавлены метрики: views_count, rating
- Реализованы choices для Status и AccessLevel
- Обновлён метод save() для авто-генерации excerpt
- Заменён is_published на status с choices
- Создана и применена миграция с дефолтными значениями
```
