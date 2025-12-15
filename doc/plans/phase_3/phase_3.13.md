# Фаза 3.13: Модель UserPostRating

## Цель

Создать модель `UserPostRating` для хранения пользовательских оценок постов с защитой от дублирования и подготовкой к денормализации рейтинга.

## Контекст

**Текущее состояние:** В [blog/models.py](../../../blog/models.py) модель Post имеет поле `rating` типа FloatField, но нет источника данных для этого поля. Нет способа пользователям ставить оценки.

**Проблема:** Как хранить индивидуальные оценки пользователей (User A поставил 5, User B поставил 4) и вычислять средний рейтинг для поста? Нужна связующая модель User ↔ Post с полем rating.

**Решение:** Модель UserPostRating с ForeignKey на User и Post, полем rating (1-5), ограничением unique_together для защиты от повторных оценок одним пользователем.

**Технологии:** Django ORM ForeignKey, IntegerField с валидаторами, Meta options unique_together.

**Философия:** "One Vote Per User". Пользователь может изменить свою оценку, но не может проголосовать дважды. Денормализация рейтинга (Phase 3.14) происходит через сигналы.

**Важно:** Поле rating должно быть IntegerField (не FloatField) с валидаторами MinValueValidator(1) и MaxValueValidator(5). В Django 6 валидаторы работают так же как в Django 5.

## Задачи

### Создание модели UserPostRating

- [ ] Открыть [blog/models.py](../../../blog/models.py)
- [ ] Импортировать валидаторы в начале файла:

```python
from django.core.validators import MinValueValidator, MaxValueValidator
```

- [ ] Создать класс `UserPostRating` **после** всех других моделей (в конце файла)
- [ ] Добавить поле `user` — ForeignKey(User), on_delete=models.CASCADE, related_name='post_ratings', verbose_name="Пользователь"
- [ ] Добавить поле `post` — ForeignKey('Post'), on_delete=models.CASCADE, related_name='ratings', verbose_name="Пост"
- [ ] Добавить поле `rating` — IntegerField, validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Оценка"
- [ ] Добавить поле `created_at` — DateTimeField, auto_now_add=True, verbose_name="Дата оценки"
- [ ] Добавить поле `updated_at` — DateTimeField, auto_now=True, verbose_name="Дата изменения"

### Настройка Meta

- [ ] Добавить `class Meta`:
- [ ] `unique_together = [['user', 'post']]` — один пользователь = одна оценка для поста
- [ ] `ordering = ['-created_at']`
- [ ] `verbose_name = "Оценка поста"`
- [ ] `verbose_name_plural = "Оценки постов"`
- [ ] `indexes = [models.Index(fields=['post', '-rating'])]` — оптимизация для сортировки по рейтингу

### Реализация методов

- [ ] Реализовать `__str__(self)`:

```python
def __str__(self):
    return f"{self.user.username}: {self.rating}/5 для '{self.post.title}'"
```

- [ ] Реализовать метод `clean(self)` для дополнительной валидации:

```python
from django.core.exceptions import ValidationError

def clean(self):
    if self.rating < 1 or self.rating > 5:
        raise ValidationError({'rating': 'Оценка должна быть от 1 до 5'})
```

### Создание миграции

- [ ] Запустить `python manage.py makemigrations blog`
- [ ] Проверить миграцию — должна создаться таблица `blog_userpostrating`
- [ ] Проверить что создан unique constraint на (user, post)
- [ ] Проверить что создан index на (post, -rating)
- [ ] Применить миграцию: `python manage.py migrate`

### Тестирование модели

- [ ] Через Django shell создать тестовые оценки:

```python
from django.contrib.auth.models import User
from blog.models import Post, UserPostRating

user1 = User.objects.first()
post = Post.objects.first()

# Создать оценку
rating1 = UserPostRating.objects.create(user=user1, post=post, rating=5)
print(rating1)

# Попытаться создать вторую оценку тем же пользователем — должна быть ошибка
rating2 = UserPostRating.objects.create(user=user1, post=post, rating=4)
# IntegrityError: UNIQUE constraint failed
```

- [ ] Проверить обновление оценки:

```python
rating1.rating = 4
rating1.save()
# Должно работать — updated_at обновится
```

- [ ] Проверить валидацию:

```python
rating_invalid = UserPostRating(user=user1, post=post, rating=10)
rating_invalid.full_clean()  # ValidationError
```

### Добавление в админку (опционально)

- [ ] В [blog/admin.py](../../../blog/admin.py) создать `UserPostRatingAdmin`:
- [ ] `list_display = ['user', 'post', 'rating', 'created_at', 'updated_at']`
- [ ] `list_filter = ['rating', 'created_at']`
- [ ] `search_fields = ['user__username', 'post__title']`
- [ ] `readonly_fields = ['created_at', 'updated_at']`
- [ ] Зарегистрировать: `@admin.register(UserPostRating)`

### Проверка обратных связей

- [ ] Проверить что `user.post_ratings.all()` работает
- [ ] Проверить что `post.ratings.all()` работает
- [ ] Проверить аннотацию среднего рейтинга:

```python
from django.db.models import Avg

post = Post.objects.annotate(avg_rating=Avg('ratings__rating')).first()
print(post.avg_rating)
```

## Коммит

**Формат:** `phase 3.13 feat: Создана модель UserPostRating для пользовательских оценок`

**Описание:**

```
phase 3.13 feat: Создана модель UserPostRating для пользовательских оценок

- Создана модель UserPostRating с полями user, post, rating (1-5)
- Добавлены валидаторы MinValueValidator и MaxValueValidator
- Настроен unique_together для защиты от дублей
- Добавлен index для оптимизации сортировки по рейтингу
- Реализованы методы __str__ и clean
- Создана и применена миграция
```
