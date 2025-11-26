# Примеры конфигурации и команды для Django 6 + Poetry 2

## Полные примеры файлов конфигурации

### Пример 1: Базовый pyproject.toml для Django 6 Beta

```toml
[tool.poetry]
name = "django6-project"
version = "0.1.0"
description = "Django 6 project with Poetry"
authors = ["Developer <dev@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.9"
django = { version = "^6.0.0b1", allow-prereleases = true }
asgiref = "^3.7"
sqlparse = "^0.4"

[tool.poetry.group.dev.dependencies]
black = "^23.0"
flake8 = "^6.0"
pytest = "^7.0"
pytest-django = "^4.5"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### Пример 2: Расширенная конфигурация с дополнительными зависимостями

```toml
[tool.poetry]
name = "django6-advanced"
version = "0.1.0"
description = "Advanced Django 6 project with Poetry"
authors = ["Developer <dev@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.10"
django = { version = "@beta", allow-prereleases = true }
asgiref = "^3.7"
sqlparse = "^0.4"
psycopg2-binary = "^2.9"
whitenoise = "^6.5"
gunicorn = "^21.0"

[tool.poetry.group.dev.dependencies]
black = "^23.0"
flake8 = "^6.0"
pytest = "^7.0"
pytest-django = "^4.5"
pytest-cov = "^4.0"
django-debug-toolbar = "^4.0"

[tool.poetry.group.docs.dependencies]
sphinx = "^7.0"
sphinx-rtd-theme = "^1.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## Пошаговые сценарии установки

### Сценарий 1: Создание проекта с нуля

```bash
# 1. Установка Poetry (если не установлен)
pip install poetry

# 2. Создание нового проекта
poetry new my-django-app
cd my-django-app

# 3. Настройка локального виртуального окружения
poetry config virtualenvs.in-project true

# 4. Добавление Django 6 beta
poetry add django@beta --allow-prereleases

# 5. Добавление дополнительных зависимостей
poetry add asgiref sqlparse

# 6. Создание Django проекта
poetry run django-admin startproject myproject .

# 7. Проверка установки
poetry run python manage.py migrate
poetry run python manage.py runserver
```

### Сценарий 2: Добавление Django 6 в существующий проект

```bash
# 1. Перейти в существующий проект
cd existing-poetry-project

# 2. Удалить старую версию Django (если есть)
poetry remove django

# 3. Добавить Django 6 beta
poetry add django@beta --allow-prereleases

# 4. Обновить зависимости
poetry update

# 5. Проверить версию
poetry run python -c "import django; print(django.get_version())"
```

## Команды управления виртуальными окружениями

### Настройка виртуального окружения

```bash
# Создание виртуального окружения в папке проекта
poetry config virtualenvs.in-project true

# Создание виртуального окружения в системной папке
poetry config virtualenvs.in-project false

# Показать текущую конфигурацию
poetry config --list

# Показать путь к виртуальному окружению
poetry env info --path
```

### Управление виртуальными окружениями

```bash
# Список всех виртуальных окружений
poetry env list

# Активация виртуального окружения
poetry shell

# Деактивация виртуального окружения
exit

# Удаление виртуального окружения
poetry env remove python
```

## Команды для работы с зависимостями

### Добавление зависимостей

```bash
# Добавление обычной зависимости
poetry add requests

# Добавление зависимости с pre-release версией
poetry add package@beta --allow-prereleases

# Добавление зависимости в группу dev
poetry add --group dev pytest

# Добавление зависимости с конкретной версией
poetry add "django>=6.0.0b1,<7.0.0" --allow-prereleases
```

### Обновление зависимостей

```bash
# Обновить все зависимости до последних версий
poetry update

# Обновить конкретную зависимость
poetry update django

# Обновить lock файл без обновления зависимостей
poetry lock --no-update
```

### Просмотр информации о зависимостях

```bash
# Показать все установленные пакеты
poetry show

# Показать дерево зависимостей
poetry show --tree

# Показать устаревшие пакеты
poetry show --outdated

# Показать последние доступные версии
poetry show --latest
```

## Команды Django через Poetry

### Базовые команды управления проектом

```bash
# Создание проекта Django
poetry run django-admin startproject myproject .

# Создание приложения
poetry run python manage.py startapp myapp

# Запуск миграций
poetry run python manage.py makemigrations
poetry run python manage.py migrate

# Запуск сервера разработки
poetry run python manage.py runserver

# Создание суперпользователя
poetry run python manage.py createsuperuser

# Сборка статических файлов
poetry run python manage.py collectstatic
```

### Команды для разработки

```bash
# Запуск тестов
poetry run pytest

# Проверка кода с flake8
poetry run flake8

# Форматирование кода с black
poetry run black .

# Запуск shell Django
poetry run python manage.py shell
```

## Скрипты для автоматизации

### Добавление скриптов в pyproject.toml

```toml
[tool.poetry.scripts]
start = "python manage.py runserver"
test = "pytest"
lint = "flake8"
format = "black ."

[tool.poetry.group.dev.scripts]
coverage = "pytest --cov=."
docs = "sphinx-build docs build/docs"
```

### Использование скриптов

```bash
# Запуск сервера через скрипт
poetry run start

# Запуск тестов
poetry run test

# Проверка кода
poetry run lint

# Форматирование кода
poetry run format
```

## Полезные команды для отладки

### Проверка окружения

```bash
# Проверить версию Python
poetry run python --version

# Проверить версию Django
poetry run python -m django --version

# Проверить путь к виртуальному окружению
poetry env info

# Проверить активное виртуальное окружение
poetry env list
```

### Отладка зависимостей

```bash
# Показать конфликтующие зависимости
poetry show --why package-name

# Проверить совместимость зависимостей
poetry check

# Экспорт зависимостей в requirements.txt
poetry export -f requirements.txt --output requirements.txt
```

## Советы по производительности

### Ускорение установки зависимостей

```bash
# Использование кэша Poetry
poetry install --no-cache

# Пропуск установки зависимостей разработки
poetry install --no-dev

# Установка только основных зависимостей
poetry install --only main
```

### Оптимизация виртуальных окружений

```bash
# Использование существующего виртуального окружения
poetry env use /path/to/python

# Очистка кэша Poetry
poetry cache clear . --all
```