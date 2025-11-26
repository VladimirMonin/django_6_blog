# Руководство по миграции на Template Partials в Django 6

## Обзор миграции

Миграция на Template Partials в Django 6 - это постепенный процесс, который можно выполнять поэтапно. Нет необходимости в срочной миграции, так как традиционный `{% include %}` продолжает работать.

## Этапы миграции

### Этап 1: Подготовка

#### 1.1 Обновление до Django 6

```bash
# Обновите зависимости
pip install -U Django>=6.0

# Проверьте совместимость
python manage.py check
```

#### 1.2 Анализ текущих шаблонов

Создайте скрипт для анализа использования `{% include %}`:

```python
# analyze_includes.py
import os
import re
from pathlib import Path

def find_includes(templates_dir):
    """Находит все использования {% include %} в шаблонах"""
    includes = {}
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith(('.html', '.django')):
                filepath = Path(root) / file
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Поиск всех include тегов
                matches = re.findall(
                    r'\{%\s*include\s+["\']([^"\']+)["\']', 
                    content
                )
                
                if matches:
                    includes[str(filepath)] = matches
    
    return includes

# Использование
if __name__ == "__main__":
    templates_dir = "templates"
    includes = find_includes(templates_dir)
    
    print("Найдены следующие include теги:")
    for template, includes_list in includes.items():
        print(f"\n{template}:")
        for inc in includes_list:
            print(f"  - {inc}")
```

### Этап 2: Приоритизация

#### 2.1 Кандидаты для миграции

**Высокий приоритет:**
- Часто используемые компоненты (кнопки, карточки, алерты)
- Компоненты с простой логикой
- Компоненты, используемые в нескольких местах

**Средний приоритет:**
- Сложные компоненты с условной логикой
- Компоненты с контекстными зависимостями

**Низкий приоритет:**
- Уникальные компоненты, используемые один раз
- Компоненты со сложной бизнес-логикой

### Этап 3: Миграция компонентов

#### 3.1 Простая миграция

**До миграции:**
```django
{# components/button.html #}
<button class="btn {{ class }}">{{ text }}</button>

{# Основной шаблон #}
{% include "components/button.html" with text="Сохранить" class="btn-primary" %}
```

**После миграции:**
```django
{# Основной шаблон с partialdef #}
{% partialdef button %}
    <button class="btn {{ class }}">{{ text }}</button>
{% endpartialdef %}

{# Использование #}
{% partial button with text="Сохранить" class="btn-primary" %}
```

#### 3.2 Миграция с контекстом

**До миграции:**
```django
{# components/user_card.html #}
<div class="user-card">
    <img src="{{ user.avatar_url }}" alt="{{ user.username }}">
    <h3>{{ user.username }}</h3>
    <p>{{ user.bio }}</p>
</div>

{# Основной шаблон #}
{% for user in users %}
    {% include "components/user_card.html" with user=user %}
{% endfor %}
```

**После миграции:**
```django
{# Основной шаблон с partialdef #}
{% partialdef user-card %}
    <div class="user-card">
        <img src="{{ user.avatar_url }}" alt="{{ user.username }}">
        <h3>{{ user.username }}</h3>
        <p>{{ user.bio }}</p>
    </div>
{% endpartialdef %}

{# Использование #}
{% for user in users %}
    {% partial user-card with user=user %}
{% endfor %}
```

### Этап 4: Оптимизация

#### 4.1 Группировка компонентов

Создайте базовый шаблон с общими компонентами:

```django
{# base_components.html #}
{% partialdef button %}
    <button class="btn {{ class }}" {% if disabled %}disabled{% endif %}>
        {{ text }}
    </button>
{% endpartialdef %}

{% partialdef card %}
    <div class="card">
        <h3>{{ title }}</h3>
        <p>{{ content }}</p>
    </div>
{% endpartialdef %}

{% partialdef alert %}
    <div class="alert alert-{{ type }}">
        <strong>{{ title }}</strong> {{ message }}
    </div>
{% endpartialdef %}
```

Используйте в других шаблонах:

```django
{# page.html #}
{% extends "base.html" %}
{% include "base_components.html" %}

{% block content %}
    {% partial alert with type="success" title="Успех!" message="Операция выполнена" %}
    {% partial card with title="Заголовок" content="Содержание" %}
{% endblock %}
```

#### 4.2 Использование синтаксиса с #

Для доступа к частичным шаблонам из других файлов:

```django
{# Включение конкретного partial из другого файла #}
{% include "base_components.html#button" with text="Кнопка" class="btn-primary" %}

{# Или через загрузчик #}
{% get_template "base_components.html#card" %}
```

## Решение проблем

### Проблема 1: Конфликт имен

**Симптом:** Ошибка "Partial 'button' already defined"

**Решение:** Используйте пространства имен:

```django
{# В базовом шаблоне #}
{% partialdef base-button %}
    <button class="btn {{ class }}">{{ text }}</button>
{% endpartialdef %}

{# В специализированном шаблоне #}
{% partialdef special-button %}
    <button class="btn btn-special {{ class }}">{{ text }}</button>
{% endpartialdef %}
```

### Проблема 2: Сложная логика в компонентах

**Симптом:** Компонент становится слишком сложным

**Решение:** Разбейте на несколько компонентов:

```django
{# Вместо одного сложного компонента #}
{% partialdef complex-component %}
    {% if condition_a %}
        <!-- Логика A -->
    {% elif condition_b %}
        <!-- Логика B -->
    {% else %}
        <!-- Логика C -->
    {% endif %}
{% endpartialdef %}

{# Разбейте на несколько простых #}
{% partialdef component-a %}{% endpartialdef %}
{% partialdef component-b %}{% endpartialdef %}
{% partialdef component-c %}{% endpartialdef %}
```

### Проблема 3: Производительность

**Симптом:** Шаблоны стали рендериться медленнее

**Решение:** Оптимизируйте использование контекста:

```django
{# Плохо: передача больших объектов #}
{% partial user-card with user=large_user_object %}

{# Хорошо: передача только нужных данных #}
{% partial user-card with 
    username=user.username
    avatar_url=user.profile.avatar_url
    bio=user.profile.bio|truncatewords:20
%}
```

## Best Practices

### 1. Именование компонентов

```django
{# Хорошие имена #}
{% partialdef primary-button %}{% endpartialdef %}
{% partialdef user-profile-card %}{% endpartialdef %}
{% partialdef blog-post-summary %}{% endpartialdef %}

{# Плохие имена #}
{% partialdef btn %}{% endpartialdef %}  # Слишком короткое
{% partialdef component1 %}{% endpartialdef %}  # Не описательное
```

### 2. Документирование компонентов

```django
{% partialdef modal %}
    {# 
    Компонент модального окна
    
    Параметры:
    - title: Заголовок модального окна
    - content: Содержимое модального окна
    - size: Размер (sm, md, lg)
    - show_close: Показывать кнопку закрытия
    #}
    
    <div class="modal modal-{{ size }}">
        <div class="modal-header">
            <h5>{{ title }}</h5>
            {% if show_close %}
                <button class="btn-close"></button>
            {% endif %}
        </div>
        <div class="modal-body">
            {{ content }}
        </div>
    </div>
{% endpartialdef %}
```

### 3. Тестирование компонентов

Создайте тестовые шаблоны для проверки компонентов:

```django
{# tests/component_tests.html #}
{% extends "base.html" %}

{% block content %}
    <h1>Тестирование компонентов</h1>
    
    <h2>Кнопки</h2>
    {% partial button with text="Обычная" class="btn-primary" %}
    {% partial button with text="Отключенная" class="btn-secondary" disabled=True %}
    
    <h2>Карточки</h2>
    {% partial card with title="Простая карточка" content="Содержание" %}
    
    <h2>Алерты</h2>
    {% partial alert with type="success" title="Успех" message="Сообщение" %}
    {% partial alert with type="error" title="Ошибка" message="Сообщение" %}
{% endblock %}
```

## Инструменты для миграции

### Скрипт автоматической миграции

```python
# migrate_includes.py
import os
import re
from pathlib import Path

def migrate_template(filepath):
    """Мигрирует include теги на partial в одном файле"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Поиск include тегов для миграции
    pattern = r'\{%\s*include\s+["\']([^"\']+)["\'](?:\s+with\s+(.+?))?\s*%\}'
    
    def replace_include(match):
        template_name = match.group(1)
        with_clause = match.group(2) or ''
        
        # Извлекаем имя компонента из пути к шаблону
        component_name = Path(template_name).stem.replace('-', '_')
        
        return f'{{% partial {component_name} {with_clause} %}}'
    
    new_content = re.sub(pattern, replace_include, content)
    
    # Записываем обратно
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return new_content != content

# Использование
if __name__ == "__main__":
    templates_dir = "templates"
    migrated_count = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith(('.html', '.django')):
                filepath = Path(root) / file
                if migrate_template(filepath):
                    print(f"Мигрирован: {filepath}")
                    migrated_count += 1
    
    print(f"\nВсего мигрировано файлов: {migrated_count}")
```

## Заключение

Миграция на Template Partials - это постепенный процесс, который приносит значительные преимущества в виде улучшенной производительности, лучшей организации кода и упрощенного управления компонентами.

**Рекомендуемый подход:**
1. Начните с простых, часто используемых компонентов
2. Тестируйте каждый мигрированный компонент
3. Постепенно расширяйте миграцию на более сложные компоненты
4. Сохраняйте обратную совместимость, используя оба подхода

Миграция не требует срочных действий и может выполняться в течение нескольких спринтов разработки.