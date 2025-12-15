# Фаза 3.1: MEDIA настройки и URL конфигурация

## Цель

Настроить Django для работы с медиа-файлами: конфигурация `MEDIA_URL`, `MEDIA_ROOT`, добавление URL patterns для dev-режима, создание структуры директорий.

## Контекст

В Phase 2 мы работали только со статикой (`static/`): CSS, JS, изображения дизайна. MEDIA-файлы — это контент, загружаемый пользователями или администраторами через формы (изображения в постах, видео, аудио).

**Текущее состояние:** В [config/settings.py](../../../config/settings.py) настроен только `STATIC_URL`, `MEDIA_URL` и `MEDIA_ROOT` отсутствуют. В [config/urls.py](../../../config/urls.py) нет маршрутов для раздачи медиа-файлов в dev-режиме.

**Проблема:** Django не знает куда сохранять загруженные файлы и как их отдавать браузеру. `FileField` и `ImageField` не будут работать.

**Технологии:** Встроенные Django инструменты — `FileSystemStorage` (для разработки), `django.conf.urls.static.static()` для URL patterns.

**Философия:** "Storage API First". Мы используем абстракцию Django Storage вместо прямых путей к файлам. Это позволит в Phase 4 безболезненно переключиться на S3 без переписывания кода.

## Задачи

### Настройка settings.py

- [ ] Добавить `MEDIA_URL = '/media/'` после `STATIC_URL`
- [ ] Добавить `MEDIA_ROOT = BASE_DIR / 'media'` — абсолютный путь к директории для хранения файлов
- [ ] Добавить комментарий: "# Media files (user uploads)"

### Настройка urls.py для dev-режима

- [ ] Импортировать `settings` и `static` в [config/urls.py](../../../config/urls.py)
- [ ] Добавить условие `if settings.DEBUG:` в конец `urlpatterns`
- [ ] Внутри условия использовать `urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)`
- [ ] Добавить комментарий: "# Раздача медиа-файлов в режиме разработки"

Пример структуры (текстовое описание):

```python
# В конце urlpatterns добавить:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Создание структуры директорий

- [ ] Создать директорию `media/` в корне проекта (на уровне `static/`)
- [ ] Создать поддиректорию `media/posts/` для будущих файлов постов
- [ ] Создать поддиректорию `media/categories/` для обложек категорий
- [ ] Создать файл `.gitkeep` в `media/posts/` и `media/categories/` чтобы Git отслеживал пустые папки
- [ ] Добавить `media/*` (кроме `.gitkeep`) в [.gitignore](../../../.gitignore) чтобы не коммитить пользовательский контент

### Проверка работоспособности

- [ ] Запустить dev-сервер `python manage.py runserver`
- [ ] Открыть <http://127.0.0.1:8000/media/> в браузере — должна отображаться "404 page not found" (ошибка нормальна, т.к. папка пуста)
- [ ] Создать тестовый файл `media/test.txt` с текстом "Hello Media"
- [ ] Открыть <http://127.0.0.1:8000/media/test.txt> — файл должен скачаться или отобразиться в браузере
- [ ] Удалить тестовый файл после проверки

## Коммит

**Формат:** `phase 3.1 feat: Настроены MEDIA настройки для загрузки файлов`

**Описание:**

```
phase 3.1 feat: Настроены MEDIA настройки для загрузки файлов

- Добавлены MEDIA_URL и MEDIA_ROOT в settings.py
- Настроены URL patterns для раздачи медиа в dev-режиме
- Создана структура директорий media/posts/ и media/categories/
- Обновлён .gitignore для исключения пользовательских файлов
```
