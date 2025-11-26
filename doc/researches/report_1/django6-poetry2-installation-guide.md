# Установка Django 6 Beta через Poetry 2

## Краткая справка

```bash
# Установка Poetry 2
pip install poetry

# Создание нового проекта
poetry new myproject
cd myproject

# Добавление Django 6 beta с разрешением pre-release версий
poetry add django@beta --allow-prereleases

# Альтернативно: указание конкретной beta версии в pyproject.toml
poetry add "django>=6.0.0b1,<7.0.0" --allow-prereleases

# Проверка установки
poetry run python -m django --version
```

## Детальная инструкция

### 1. Установка Poetry 2

Poetry 2 можно установить через pip:

```bash
pip install poetry
```

После установки проверьте версию:
```bash
poetry --version
```

### 2. Создание нового проекта

```bash
# Создание проекта с Poetry
poetry new my-django-project
cd my-django-project
```

### 3. Настройка виртуального окружения

Poetry автоматически создает виртуальное окружение. Для настройки локального окружения в папке проекта:

```bash
# Создание виртуального окружения в папке проекта
poetry config virtualenvs.in-project true
```

### 4. Установка Django 6 Beta

#### Способ 1: Использование флага --allow-prereleases

```bash
# Установка последней beta версии Django
poetry add django@beta --allow-prereleases
```

#### Способ 2: Указание конкретной версии

```bash
# Установка конкретной beta версии
poetry add "django>=6.0.0b1,<7.0.0" --allow-prereleases
```

#### Способ 3: Ручное редактирование pyproject.toml

Добавьте в файл `pyproject.toml`:

```toml
[tool.poetry.dependencies]
python = "^3.9"
django = { version = "^6.0.0b1", allow-prereleases = true }
```

Затем выполните:
```bash
poetry install
```

### 5. Пример полного pyproject.toml

```toml
[tool.poetry]
name = "my-django-project"
version = "0.1.0"
description = ""
authors = ["Your Name <email@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.9"
django = { version = "^6.0.0b1", allow-prereleases = true }

[tool.poetry.group.dev.dependencies]
black = "^23.0"
flake8 = "^6.0"
pytest = "^7.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## Примеры конфигурации

### Конфигурация Poetry для локальных виртуальных окружений

```bash
# Создание виртуального окружения в папке проекта
poetry config virtualenvs.in-project true

# Просмотр текущей конфигурации
poetry config --list
```

### Конфигурация зависимостей с pre-release версиями

```toml
[tool.poetry.dependencies]
python = "^3.9"

# Django 6 beta с разрешением pre-release
# Вариант 1: Использование @beta
# django = { version = "@beta", allow-prereleases = true }

# Вариант 2: Указание диапазона версий
django = { version = ">=6.0.0b1,<7.0.0", allow-prereleases = true }

# Вариант 3: Использование caret с разрешением pre-release
# django = { version = "^6.0.0b1", allow-prereleases = true }
```

## Проверка установки

### Проверка версии Django

```bash
# Через Poetry
poetry run python -m django --version

# Через Python интерпретатор
poetry run python -c "import django; print(django.get_version())"
```

### Проверка зависимостей

```bash
# Показать все установленные пакеты
poetry show

# Показать дерево зависимостей
poetry show --tree

# Проверить наличие обновлений
poetry show --latest
```

### Создание тестового проекта

```bash
# Создание Django проекта
poetry run django-admin startproject myproject .

# Запуск сервера разработки
poetry run python manage.py runserver
```

## Troubleshooting

### Проблема 1: Poetry не находит beta версии

**Решение:** Убедитесь, что используется флаг `--allow-prereleases`:

```bash
# Удалить существующую зависимость
poetry remove django

# Добавить с разрешением pre-release
poetry add django@beta --allow-prereleases
```

### Проблема 2: Конфликты зависимостей

**Решение:** Используйте команду `poetry lock` для разрешения конфликтов:

```bash
# Обновить lock файл
poetry lock --no-update

# Переустановить зависимости
poetry install
```

### Проблема 3: Виртуальное окружение не активируется

**Решение:** Активируйте окружение вручную или используйте `poetry run`:

```bash
# Активация окружения
poetry shell

# Или выполнение команд через poetry run
poetry run python manage.py migrate
```

### Проблема 4: Ошибки совместимости Python версий

**Решение:** Убедитесь, что версия Python соответствует требованиям Django 6:

```toml
[tool.poetry.dependencies]
python = "^3.9"  # Django 6 требует Python 3.9+
```

## Команды управления проектом

### Основные команды Poetry

```bash
# Создание нового проекта
poetry new project-name

# Добавление зависимостей
poetry add package-name

# Установка всех зависимостей
poetry install

# Обновление зависимостей
poetry update

# Удаление зависимостей
poetry remove package-name

# Показать информацию о зависимостях
poetry show

# Активация виртуального окружения
poetry shell
```

### Команды Django через Poetry

```bash
# Создание проекта
poetry run django-admin startproject projectname

# Создание приложения
poetry run python manage.py startapp appname

# Миграции
poetry run python manage.py makemigrations
poetry run python manage.py migrate

# Запуск сервера
poetry run python manage.py runserver

# Создание суперпользователя
poetry run python manage.py createsuperuser
```

## Источники

### Официальная документация

- **Poetry Documentation**: https://python-poetry.org/docs/
- **Django Documentation**: https://docs.djangoproject.com/
- **Poetry Dependency Specification**: https://python-poetry.org/docs/dependency-specification/

### Контекстные источники

- Poetry Website Repository: `/python-poetry/website`
- Django Repository: `/django/django`

### Веб-источники

- Stack Overflow: Python Poetry: Cannot find beta versions of a package
- Poetry GitHub Issues: Pre-release version handling
- Django Installation Documentation

---

**Дата исследования**: 26 ноября 2025  
**Статус**: Полное исследование завершено  
**Следующие шаги**: Тестирование установки в реальном проекте