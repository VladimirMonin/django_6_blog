# Фаза 3.14: Денормализация рейтинга в Post

## Цель

Добавить Django signal `post_save` для `UserPostRating`, автоматически пересчитывающий средний рейтинг и обновляющий поле `Post.rating` при создании/изменении оценки.

## Контекст

**Текущее состояние:** В [blog/models.py](../../../blog/models.py) есть модели Post с полем rating и UserPostRating. При создании оценки поле Post.rating не обновляется автоматически.

**Проблема:** Каждый раз при выводе списка постов с сортировкой по рейтингу придётся делать агрегацию `Post.objects.annotate(Avg('ratings__rating'))`. Это тяжёлый запрос для большого количества постов и оценок.

**Решение:** Денормализация — хранить вычисленное значение в поле Post.rating. Обновлять его через Django signals при изменении UserPostRating.

**Технологии:** Django signals `post_save` и `post_delete`, ORM aggregate Avg(), `update_fields` для оптимизации.

**Философия:** "Denormalize for Read Performance". Жертвуем немного согласованностью данных (signal может не сработать) ради скорости чтения. В критичных местах можем пересчитать вручную.

**Важно:** Signals должны быть импортированы в `apps.py` через `ready()` или размещены в `signals.py` и импортированы в `__init__.py` приложения.

## Задачи

### Создание файла signals.py

- [ ] Создать файл `blog/signals.py`
- [ ] Добавить docstring:

```python
"""Django signals для автоматического обновления данных.

post_save и post_delete для UserPostRating обновляют Post.rating.
"""
```

- [ ] Импортировать модули:

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg
from blog.models import UserPostRating
```

### Реализация функции update_post_rating

- [ ] Создать функцию `update_post_rating(post)`:
- [ ] Добавить docstring: "Пересчитывает и обновляет средний рейтинг поста."
- [ ] Вычислить средний рейтинг:

```python
def update_post_rating(post):
    """Пересчитывает и обновляет средний рейтинг поста."""
    avg_rating = post.ratings.aggregate(Avg('rating'))['rating__avg']
    
    if avg_rating is not None:
        post.rating = round(avg_rating, 2)  # Округляем до 2 знаков
    else:
        post.rating = 0.0  # Если нет оценок
    
    post.save(update_fields=['rating'])
```

### Создание signal receiver для post_save

- [ ] Создать функцию с декоратором `@receiver`:

```python
@receiver(post_save, sender=UserPostRating)
def rating_saved(sender, instance, created, **kwargs):
    """Обновить рейтинг поста при создании/изменении оценки."""
    update_post_rating(instance.post)
```

### Создание signal receiver для post_delete

- [ ] Создать функцию для удаления оценки:

```python
@receiver(post_delete, sender=UserPostRating)
def rating_deleted(sender, instance, **kwargs):
    """Обновить рейтинг поста при удалении оценки."""
    update_post_rating(instance.post)
```

### Регистрация signals

- [ ] Открыть `blog/apps.py`
- [ ] Найти класс `BlogConfig(AppConfig)`
- [ ] Добавить метод `ready()`:

```python
def ready(self):
    import blog.signals  # Импортировать signals при загрузке приложения
```

### Тестирование signals

- [ ] Перезапустить сервер Django (чтобы signals загрузились)
- [ ] Через Django shell создать оценки:

```python
from django.contrib.auth.models import User
from blog.models import Post, UserPostRating

post = Post.objects.first()
user1 = User.objects.get(username='admin')
user2 = User.objects.get(username='user')  # Создать если нет

# До оценок
print(f"Rating before: {post.rating}")

# Создать оценки
UserPostRating.objects.create(user=user1, post=post, rating=5)
post.refresh_from_db()
print(f"After first rating: {post.rating}")  # Должно быть 5.0

UserPostRating.objects.create(user=user2, post=post, rating=3)
post.refresh_from_db()
print(f"After second rating: {post.rating}")  # Должно быть 4.0 ((5+3)/2)
```

- [ ] Проверить изменение оценки:

```python
rating1 = UserPostRating.objects.get(user=user1, post=post)
rating1.rating = 4
rating1.save()
post.refresh_from_db()
print(f"After update: {post.rating}")  # Должно быть 3.5 ((4+3)/2)
```

- [ ] Проверить удаление оценки:

```python
rating1.delete()
post.refresh_from_db()
print(f"After delete: {post.rating}")  # Должно быть 3.0 (только rating2 осталась)
```

### Проверка производительности

- [ ] Создать несколько постов и много оценок (100-200)
- [ ] Измерить время запроса без денормализации:

```python
import time
from django.db.models import Avg

start = time.time()
posts = Post.objects.annotate(avg_rating=Avg('ratings__rating')).all()
list(posts)  # Заставить выполниться
print(f"With annotation: {time.time() - start}s")
```

- [ ] Измерить время с денормализацией:

```python
start = time.time()
posts = Post.objects.all()  # rating уже в поле
list(posts)
print(f"With denormalization: {time.time() - start}s")
```

### Обработка edge cases

- [ ] Проверить что происходит если пост удаляется (оценки должны удалиться через CASCADE)
- [ ] Проверить что signal не вызывается циклично (save() в signal должен использовать update_fields)
- [ ] Проверить что пост без оценок имеет rating = 0.0

## Коммит

**Формат:** `phase 3.14 feat: Добавлена денормализация рейтинга через Django signals`

**Описание:**

```
phase 3.14 feat: Добавлена денормализация рейтинга через Django signals

- Создан blog/signals.py с post_save и post_delete для UserPostRating
- Реализована функция update_post_rating для пересчёта среднего
- Автоматическое обновление Post.rating при создании/изменении/удалении оценок
- Зарегистрированы signals через BlogConfig.ready()
- Оптимизация через update_fields для предотвращения циклов
```
