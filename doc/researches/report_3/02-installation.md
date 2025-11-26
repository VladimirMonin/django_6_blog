# Установка и настройка django-components

## Установка пакета

```bash
pip install django-components
```

## Настройка Django проекта

### Добавление в INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'django_components',
]
```

### Конфигурация компонентов

```python
# settings.py
from django_components import ComponentsSettings
from pathlib import Path

COMPONENTS = ComponentsSettings(
    # Глобальные директории компонентов
    dirs=[
        Path(BASE_DIR) / "components",
    ],
    # Директории компонентов на уровне приложений
    app_dirs=[
        "components",
    ],
)
```

### Настройка URL

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    ...,
    path("", include("django_components.urls")),
]
```

## Структура проекта

### Рекомендуемая организация

```
project/
├── components/           # Глобальные компоненты
│   ├── button/
│   │   ├── __init__.py
│   │   ├── button.py
│   │   ├── button.html
│   │   ├── button.css
│   │   └── button.js
│   └── card/
│       ├── __init__.py
│       ├── card.py
│       ├── card.html
│       ├── card.css
│       └── card.js
├── myapp/
│   ├── components/      # Компоненты приложения
│   │   ├── __init__.py
│   │   └── forms.py
│   ├── models.py
│   └── views.py
└── templates/
    └── base.html
```

## Подключение в шаблонах

### Базовый шаблон

```django
<!doctype html>
<html>
  <head>
    <title>{% block title %}My Site{% endblock %}</title>
    {% component_css_dependencies %}
  </head>
  <body>
    {% block content %}{% endblock %}
    {% component_js_dependencies %}
  </body>
</html>
```

### Использование компонентов

```django
{% load component_tags %}

{% component "button" text="Click me" / %}
```

## Дополнительные расширения

### Установка расширений

```bash
# Для расширенной валидации типов
pip install djc-ext-pydantic

# Для подсветки синтаксиса в VSCode
pip install pygments-djc
```

### Настройка расширений

```python
# settings.py
COMPONENTS = {
    "extensions": [
        "my_app.extensions.MyExtension",
    ],
}
```

## Проверка установки

### Создание тестового компонента

```python
# components/hello/hello.py
from django_components import Component, register

@register("hello")
class Hello(Component):
    template = """
        <div class="hello">
            Hello, {{ name }}!
        </div>
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "name": kwargs.get("name", "World"),
        }
```

### Использование в шаблоне

```django
{% component "hello" name="Django" / %}
```

## Типичные проблемы при установке

### Проблема: Компоненты не загружаются

**Решение**: Проверьте настройки `COMPONENTS` и убедитесь, что директории существуют.

### Проблема: CSS/JS не подключаются

**Решение**: Убедитесь, что в базовом шаблоне есть `{% component_css_dependencies %}` и `{% component_js_dependencies %}`.

### Проблема: Ошибки импорта

**Решение**: Убедитесь, что все компоненты зарегистрированы с помощью `@register` декоратора.

---

**Следующий раздел**: [Создание компонентов](./03-creating-components.md)