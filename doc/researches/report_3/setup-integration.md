# Настройка и интеграция Django Components

## Установка и базовая настройка

### Установка через pip

```bash
# Установка последней версии
pip install django-components

# Установка конкретной версии
pip install django-components==0.130

# Установка с дополнительными зависимостями
pip install django-components[dev]
```

### Настройка в settings.py

```python
# settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Django Components
    'django_components',
    
    # Ваши приложения
    'myapp',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'builtins': [
                'django_components.templatetags.component_tags',
            ],
        },
    },
]

# Настройки для статических файлов
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Для продакшена
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

### Структура проекта

```
myproject/
├── manage.py
├── requirements.txt
├── myproject/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── myapp/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py
│   ├── components/           # Компоненты приложения
│   │   ├── __init__.py
│   │   ├── button.py
│   │   ├── card.py
│   │   └── modal.py
│   └── templates/
│       └── components/       # Шаблоны компонентов
│           ├── button.html
│           ├── card.html
│           └── modal.html
├── templates/                # Глобальные шаблоны
│   ├── base.html
│   └── index.html
└── static/
    └── components/           # Статические файлы компонентов
        ├── button.css
        ├── card.css
        └── modal.js
```

## Регистрация компонентов

### Автоматическая регистрация

Django-components автоматически находит компоненты в папках `components/` ваших приложений.

### Ручная регистрация

```python
# myapp/components/__init__.py
from .button import Button
from .card import Card
from .modal import Modal

# Компоненты будут автоматически доступны
__all__ = ['Button', 'Card', 'Modal']
```

### Настройка каталогов компонентов

```python
# settings.py
COMPONENTS = {
    'autodiscover': True,
    'libraries': [
        'myapp.components',
        'otherapp.components',
    ],
}
```

## Интеграция с Django 6

### Использование новых возможностей шаблонов

Django 6 улучшает работу с частичными шаблонами:

```python
# components/modern_component.py
from django_components import Component

class ModernComponent(Component):
    """Компонент использующий новые возможности Django 6"""
    template_name = "components/modern_component.html"
    
    def get_context_data(self):
        # Используем улучшенный механизм контекста
        return {
            "enhanced_data": self.process_with_django6_features(),
        }
```

### Интеграция с новыми template tags

```html
<!-- Использование с новыми возможностями Django 6 -->
{% load component_tags %}

<main>
    {% component "modern_component" %}
    
    <!-- Новые возможности includes в Django 6 -->
    {% include "partials/sidebar.html" %}
</main>
```

## Интеграция с другими библиотеками

### Интеграция с HTMX

```python
# components/htmx_button.py
from django_components import Component

class HtmxButton(Component):
    template_name = "components/htmx_button.html"
    
    def get_context_data(self, hx_get="", hx_post="", hx_target=""):
        return {
            "hx_get": hx_get,
            "hx_post": hx_post,
            "hx_target": hx_target,
        }
```

```html
<!-- templates/components/htmx_button.html -->
<button 
    class="btn btn-primary"
    {% if hx_get %}hx-get="{{ hx_get }}"{% endif %}
    {% if hx_post %}hx-post="{{ hx_post }}"{% endif %}
    {% if hx_target %}hx-target="{{ hx_target }}"{% endif %}
>
    HTMX Button
</button>
```

### Интеграция с Alpine.js

```python
# components/alpine_component.py
from django_components import Component

class AlpineComponent(Component):
    template_name = "components/alpine_component.html"
    js_dependencies = ["components/alpine_component.js"]
    
    def get_context_data(self, initial_data=""):
        return {
            "initial_data": initial_data,
        }
```

```html
<!-- templates/components/alpine_component.html -->
<div x-data="{ data: '{{ initial_data }}' }">
    <input x-model="data" type="text">
    <p x-text="data"></p>
</div>
```

### Интеграция с Django Forms

```python
# components/form_component.py
from django import forms
from django_components import Component, Slot

class FormComponent(Component):
    template_name = "components/form_component.html"
    
    class Slots:
        fields: Slot
        buttons: Slot
    
    def get_context_data(self, form_instance):
        """
        Принимает экземпляр Django формы
        """
        return {
            "form": form_instance,
        }
```

```html
<!-- templates/components/form_component.html -->
<form method="post">
    {% csrf_token %}
    
    <div class="form-fields">
        {{ slots.fields }}
    </div>
    
    <div class="form-buttons">
        {{ slots.buttons }}
    </div>
</form>
```

## Расширенные настройки

### Кастомные настройки компонентов

```python
# settings.py
COMPONENTS = {
    'autodiscover': True,
    'libraries': [
        'myapp.components',
    ],
    'template_dirs': [
        'templates/components',
    ],
    'static_dirs': [
        'static/components',
    ],
}
```

### Настройка для разработки

```python
# settings/development.py
DEBUG = True

# Дополнительные настройки для разработки
COMPONENTS = {
    'autodiscover': True,
    'debug': True,  # Включить отладочную информацию
}
```

### Настройка для продакшена

```python
# settings/production.py
DEBUG = False

COMPONENTS = {
    'autodiscover': True,
    'debug': False,
    'cache_timeout': 3600,  # Кэширование компонентов
}
```

## Миграция с других решений

### Миграция с django-template-partials

```python
# Старый код с django-template-partials
from django_template_partials import partial

@partial("my_partial.html")
def my_partial(request, data):
    return {"data": data}

# Новый код с django-components
from django_components import Component

class MyComponent(Component):
    template_name = "components/my_component.html"
    
    def get_context_data(self, data):
        return {"data": data}
```

### Миграция с пользовательских template tags

```python
# Старый код с custom template tags
from django import template

register = template.Library()

@register.inclusion_tag('components/old_component.html')
def old_component(data):
    return {"data": data}

# Новый код с django-components
from django_components import Component

class NewComponent(Component):
    template_name = "components/new_component.html"
    
    def get_context_data(self, data):
        return {"data": data}
```

## Troubleshooting

### Общие проблемы и решения

#### 1. Компоненты не загружаются

**Проблема:** Компоненты не отображаются в шаблонах

**Решение:**
- Проверить настройки в `INSTALLED_APPS`
- Убедиться что `django_components` добавлен
- Проверить правильность `TEMPLATES` конфигурации

```python
# Проверка настроек
INSTALLED_APPS = [
    # ...
    'django_components',  # Должен быть здесь
]

TEMPLATES = [
    {
        'OPTIONS': {
            'builtins': [
                'django_components.templatetags.component_tags',  # Должен быть здесь
            ],
        },
    },
]
```

#### 2. CSS/JS файлы не загружаются

**Проблема:** Стили и скрипты компонентов не применяются

**Решение:**
- Проверить пути к статическим файлам
- Убедиться в правильной настройке `STATICFILES_DIRS`
- Проверить что файлы существуют

```python
# Проверка путей
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Должен указывать на папку со статикой
]
```

#### 3. Slots не работают

**Проблема:** Контент в слотах не отображается

**Решение:**
- Проверить объявление слотов в классе компонента
- Убедиться в правильном использовании `{% fill %}`
- Проверить что слоты объявлены в `class Slots`

```python
# Правильное объявление слотов
class MyComponent(Component):
    class Slots:
        header: Slot
        body: Slot
```

#### 4. Ошибки производительности

**Проблема:** Страницы загружаются медленно

**Решение:**
- Использовать компоненты только для сложных UI элементов
- Избегать глубокого вложения компонентов
- Кэшировать часто используемые компоненты
- Использовать простые шаблоны для статического контента

## Дополнительные ресурсы

### Полезные ссылки

- [Официальная документация django-components](https://github.com/django-components/django-components)
- [Примеры использования на TestDriven.io](https://testdriven.io/blog/django-reusable-components/)
- [Документация Django 6](https://docs.djangoproject.com/en/6.0/)
- [Интеграция с HTMX](https://htmx.org/)

### Сообщество

- [GitHub Issues](https://github.com/django-components/django-components/issues)
- [Django Forum](https://forum.djangoproject.com/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/django-components)

---

**Дата создания**: 26 ноября 2025  
**Версия Django**: 6.0  
**Версия django-components**: 0.130+