# Фаза 3.23: Установка Tom Select и django-tomselect

## Цель

Установить django-tomselect, проверить совместимость с Django 6, настроить базовую конфигурацию, подключить статику.

## Контекст

**Текущее состояние:** В админке используются стандартные виджеты для тегов и категорий.

**Проблема:** Стандартные select неудобны для ManyToMany полей, нет создания тегов "на лету", нет поиска.

**Решение:** Tom Select — современная альтернатива select2, легкая, без jQuery, поддерживает создание опций, поиск, множественный выбор.

## Задачи

### Установка

- [ ] Проверить совместимость с Django 6:
- [ ] Искать в репозитории django-tomselect issues про Django 6
- [ ] Установить через Poetry: `poetry add django-tomselect`

### Настройка settings.py

- [ ] Добавить `'django_tomselect'` в INSTALLED_APPS
- [ ] Добавить конфигурацию (если требуется):

```python
TOMSELECT_CONFIG = {
    'css': 'django_tomselect/css/tom-select.bootstrap5.css',
    'js': 'django_tomselect/js/tom-select.complete.js',
}
```

### Подключение статики

- [ ] Запустить `python manage.py collectstatic --noinput` для сбора статики Tom Select
- [ ] Проверить что файлы появились в STATIC_ROOT

### Тестирование базовой установки

- [ ] Запустить сервер
- [ ] Открыть админку — не должно быть ошибок
- [ ] Проверить что статика Tom Select доступна

## Коммит

```
phase 3.23 feat: Установлен django-tomselect для современных селекторов

- Установлен django-tomselect
- Добавлен в INSTALLED_APPS
- Настроена базовая конфигурация
- Собрана статика Tom Select
```
