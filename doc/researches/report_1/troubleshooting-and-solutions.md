# Проблемы и решения при установке Django 6 Beta через Poetry 2

## Общие проблемы и их решения

### Проблема 1: Poetry не находит beta версии Django

**Симптомы:**
- Команда `poetry add django@beta` завершается ошибкой
- Сообщение "Could not find a matching version of package django"
- Устанавливается стабильная версия вместо beta

**Решение:**
```bash
# Использовать флаг --allow-prereleases
poetry add django@beta --allow-prereleases

# Или указать конкретную beta версию
poetry add "django>=6.0.0b1,<7.0.0" --allow-prereleases

# Убедиться, что в pyproject.toml указано allow-prereleases
```

**Проверка в pyproject.toml:**
```toml
[tool.poetry.dependencies]
django = { version = "^6.0.0b1", allow-prereleases = true }
```

### Проблема 2: Конфликты зависимостей

**Симптомы:**
- Ошибка "SolverProblemError" при установке
- Сообщение о несовместимых версиях зависимостей
- Не удается разрешить зависимости

**Решение:**
```bash
# Очистить lock файл и переустановить
rm poetry.lock
poetry install

# Или использовать команду lock с принудительным обновлением
poetry lock --no-update
poetry install

# Проверить совместимость зависимостей
poetry check
```

### Проблема 3: Ошибки совместимости Python версий

**Симптомы:**
- Ошибка "No matching distribution found for django"
- Сообщение о несовместимой версии Python

**Решение:**
```toml
# Убедиться, что указана совместимая версия Python
[tool.poetry.dependencies]
python = "^3.9"  # Django 6 требует Python 3.9+
```

```bash
# Проверить версию Python в проекте
poetry env info

# Изменить версию Python для проекта
poetry env use python3.9
```

### Проблема 4: Виртуальное окружение не активируется

**Симптомы:**
- Команда `poetry shell` не работает
- Ошибка "No virtualenv has been created for this project"

**Решение:**
```bash
# Создать виртуальное окружение вручную
poetry install

# Или использовать poetry run для выполнения команд
poetry run python manage.py migrate

# Проверить конфигурацию виртуальных окружений
poetry config virtualenvs.in-project true
```

### Проблема 5: Ошибки хэшей при установке

**Симптомы:**
- Ошибка "Invalid hashes" при установке пакетов
- Сообщение о несовпадении контрольных сумм

**Решение:**
```bash
# Очистить кэш Poetry
poetry cache clear . --all

# Переустановить зависимости
rm poetry.lock
poetry install

# Игнорировать проверку хэшей (не рекомендуется для production)
poetry install --no-verify
```

## Проблемы специфичные для Windows

### Проблема 6: Ошибки путей в Windows

**Симптомы:**
- Ошибки с путями, содержащими обратные слеши
- Проблемы с активацией виртуального окружения

**Решение:**
```bash
# Использовать PowerShell вместо CMD
# Убедиться, что пути корректны

# Альтернатива: использовать WSL для разработки
```

### Проблема 7: Блокировка файлов антивирусом

**Симптомы:**
- Ошибки доступа к файлам при установке
- Медленная установка зависимостей

**Решение:**
- Добавить папку проекта в исключения антивируса
- Использовать WSL для обхода проблем с антивирусом

## Проблемы с производительностью

### Проблема 8: Медленная установка зависимостей

**Решение:**
```bash
# Использовать более быстрый индекс пакетов
poetry source add --priority=primary pypi https://pypi.org/simple/

# Отключить проверку хэшей для ускорения (только для разработки)
poetry install --no-verify

# Использовать uv как альтернативный резолвер (если доступен)
poetry config experimental.new-installer false
```

### Проблема 9: Большой размер виртуального окружения

**Решение:**
```bash
# Удалить ненужные пакеты
poetry remove unused-package

# Очистить кэш Poetry
poetry cache clear . --all

# Использовать --no-dev для production установки
poetry install --no-dev
```

## Проблемы с версиями зависимостей

### Проблема 10: Зависимости требуют старую версию Django

**Симптомы:**
- Конфликты с пакетами, которые требуют Django < 6.0
- Ошибки совместимости при установке

**Решение:**
```bash
# Проверить совместимость зависимостей
poetry show --tree

# Найти альтернативные пакеты, совместимые с Django 6
# Обновить конфликтующие зависимости до совместимых версий

# Временно использовать старую версию Django для тестирования
poetry add "django>=5.2,<6.0"
```

### Проблема 11: Pre-release зависимости не обновляются

**Решение:**
```bash
# Принудительное обновление до последней beta версии
poetry update django --allow-prereleases

# Удалить и переустановить зависимость
poetry remove django
poetry add django@beta --allow-prereleases
```

## Проблемы с конфигурацией проекта

### Проблема 12: Неправильная структура проекта

**Решение:**
```bash
# Создать правильную структуру проекта
poetry new myproject
cd myproject

# Или инициализировать Poetry в существующей папке
poetry init
```

### Проблема 13: Конфликты с системными пакетами Python

**Решение:**
```bash
# Убедиться, что используется виртуальное окружение Poetry
poetry env info

# Проверить, какой Python используется
poetry run which python

# Принудительно использовать виртуальное окружение
poetry env use python
```

## Полезные команды для диагностики

### Команды проверки состояния

```bash
# Проверить конфигурацию Poetry
poetry config --list

# Проверить состояние виртуального окружения
poetry env info

# Проверить установленные пакеты
poetry show

# Проверить дерево зависимостей
poetry show --tree

# Проверить наличие обновлений
poetry show --outdated
```

### Команды для отладки

```bash
# Подробный вывод при установке
poetry install -v

# Проверить разрешение зависимостей
poetry lock --no-update -v

# Экспорт зависимостей для проверки
poetry export -f requirements.txt
```

## Профилактические меры

### Рекомендации по настройке проекта

1. **Всегда использовать виртуальные окружения**
2. **Регулярно обновлять зависимости**
3. **Тестировать на разных версиях Python**
4. **Использовать группы зависимостей для разделения окружений**
5. **Сохранять poetry.lock в системе контроля версий**

### Рекомендуемая структура pyproject.toml

```toml
[tool.poetry]
name = "project-name"
version = "0.1.0"
description = ""
authors = ["Name <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.9"
django = { version = "^6.0.0b1", allow-prereleases = true }

[tool.poetry.group.dev.dependencies]
# Зависимости для разработки

[tool.poetry.group.test.dependencies]
# Зависимости для тестирования

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## Дополнительные ресурсы

- [Официальная документация Poetry](https://python-poetry.org/docs/)
- [Django Installation Guide](https://docs.djangoproject.com/en/6.0/topics/install/)
- [Poetry GitHub Issues](https://github.com/python-poetry/poetry/issues)
- [Stack Overflow - Poetry tag](https://stackoverflow.com/questions/tagged/poetry-python)