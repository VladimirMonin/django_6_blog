# Производительность и Best Practices Django Components

## Производительность

### Важные замечания

Согласно документации django-components, библиотека примерно в **4 раза медленнее** стандартных Django шаблонов. Это связано с дополнительной обработкой компонентов, загрузкой CSS/JS файлов и механизмом слотов.

### Факторы влияющие на производительность

1. **Загрузка компонентов** - каждый компонент требует дополнительной обработки
2. **CSS/JS файлы** - автоматическая загрузка статических файлов
3. **Слоты** - механизм передачи контента требует дополнительных вычислений
4. **Вложенность** - глубоко вложенные компоненты замедляют рендеринг

### Рекомендации по оптимизации

#### 1. Использование компонентов для сложных UI элементов

```python
# ХОРОШО: Использовать для сложных компонентов
class ProductCard(Component):
    """Сложный компонент карточки товара"""
    template_name = "components/product_card.html"
    css_dependencies = ["components/product_card.css"]
    js_dependencies = ["components/product_card.js"]
    
    def get_context_data(self, product):
        return {
            "product": product,
            "formatted_price": self.format_price(product.price),
            "discount": self.calculate_discount(product),
        }

# ПЛОХО: Использовать для простых элементов
class SimpleSpan(Component):
    """Простой span - лучше использовать обычный шаблон"""
    template_name = "components/simple_span.html"
    
    def get_context_data(self, text):
        return {"text": text}
```

#### 2. Избегать чрезмерного вложения компонентов

```python
# ПЛОХО: Глубокое вложение
class DeeplyNestedComponent(Component):
    def get_context_data(self):
        # Каждый уровень вложения добавляет накладные расходы
        return {"data": self.process_data()}

# ХОРОШО: Плоская структура
class FlatComponent(Component):
    def get_context_data(self):
        # Минимальное вложение
        return self.process_all_data()
```

#### 3. Кэширование часто используемых компонентов

```python
from django.core.cache import cache
from django_components import Component

class CachedComponent(Component):
    template_name = "components/cached_component.html"
    
    def get_context_data(self, cache_key="default"):
        cached_data = cache.get(f"component_{cache_key}")
        
        if cached_data is None:
            # Вычисляем данные только если их нет в кэше
            cached_data = self.calculate_expensive_data()
            cache.set(f"component_{cache_key}", cached_data, 300)  # 5 минут
        
        return {"data": cached_data}
```

#### 4. Использование простых компонентов для статического контента

```python
# ХОРОШО: Статический контент в обычных шаблонах
# templates/static_content.html
<div class="static-content">
    <h1>Welcome to our site</h1>
    <p>This content rarely changes</p>
</div>

# ПЛОХО: Статический контент в компонентах
class StaticContent(Component):
    template_name = "components/static_content.html"
```

## Best Practices

### 1. Организация проекта

```
project/
├── apps/
│   ├── core/
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── base.py          # Базовые классы компонентов
│   │       ├── ui/              # UI компоненты
│   │       │   ├── button.py
│   │       │   ├── card.py
│   │       │   └── modal.py
│   │       └── forms/           # Формы
│   │           ├── input.py
│   │           └── select.py
│   └── blog/
│       └── components/          # Компоненты специфичные для приложения
│           ├── post_card.py
│           └── comment_form.py
```

### 2. Именование компонентов

```python
# ХОРОШО: PascalCase для классов
class ProductCard(Component):
    pass

class UserProfileForm(Component):
    pass

# ПЛОХО: snake_case для классов
class product_card(Component):
    pass
```

### 3. Документирование компонентов

```python
class Button(Component):
    """
    Кнопка с различными вариантами стилей.
    
    Args:
        text (str): Текст кнопки
        variant (str): Вариант стиля (primary, secondary, danger)
        size (str): Размер кнопки (sm, md, lg)
        disabled (bool): Отключена ли кнопка
    
    Example:
        {% component "button" text="Submit" variant="primary" %}
    """
    template_name = "components/button.html"
    
    def get_context_data(self, text="Click me", variant="primary", size="md", disabled=False):
        return {
            "text": text,
            "variant": variant,
            "size": size,
            "disabled": disabled,
        }
```

### 4. Валидация входных данных

```python
from typing import Optional
from django_components import Component, Slot, SlotInput

class ValidatedForm(Component):
    template_name = "components/validated_form.html"
    
    class Args:
        method: str
        action: str
    
    class Kwargs:
        enctype: Optional[str] = None
        css_class: Optional[str] = None
    
    class Slots:
        fields: SlotInput
        buttons: Optional[SlotInput] = None
    
    def get_context_data(self, args, kwargs, slots):
        # Валидация метода
        if args.method.upper() not in ['GET', 'POST', 'PUT', 'DELETE']:
            raise ValueError(f"Invalid HTTP method: {args.method}")
        
        return {
            "method": args.method.upper(),
            "action": args.action,
            "enctype": kwargs.get("enctype"),
            "css_class": kwargs.get("css_class", ""),
            "fields": slots.fields,
            "buttons": slots.buttons,
        }
```

### 5. Тестирование компонентов

```python
from django.test import TestCase
from django_components import Component

class TestButtonComponent(TestCase):
    def test_button_default_values(self):
        component = Button()
        context = component.get_context_data()
        
        self.assertEqual(context["text"], "Click me")
        self.assertEqual(context["variant"], "primary")
        self.assertEqual(context["size"], "md")
        self.assertFalse(context["disabled"])
    
    def test_button_custom_values(self):
        component = Button()
        context = component.get_context_data(
            text="Custom Text",
            variant="danger",
            size="lg",
            disabled=True
        )
        
        self.assertEqual(context["text"], "Custom Text")
        self.assertEqual(context["variant"], "danger")
        self.assertEqual(context["size"], "lg")
        self.assertTrue(context["disabled"])
    
    def test_button_rendering(self):
        """Тестирование рендеринга компонента"""
        component = Button()
        context = component.get_context_data(text="Test")
        
        # Проверка что контекст содержит ожидаемые данные
        self.assertIn("text", context)
        self.assertIn("variant", context)
        
        # Можно также тестировать рендеринг HTML
        from django.template import Template, Context
        template = Template('{% load component_tags %}{% component "button" text="Test" %}')
        rendered = template.render(Context({}))
        
        self.assertIn("Test", rendered)
        self.assertIn("btn-primary", rendered)
```

### 6. Интеграция с Django Forms

```python
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
        if not isinstance(form_instance, forms.BaseForm):
            raise TypeError("form_instance must be a Django form")
        
        return {
            "form": form_instance,
        }
```

### 7. Работа с контекстом Django

```python
from django_components import Component

class ContextAwareComponent(Component):
    template_name = "components/context_aware.html"
    
    def get_context_data(self, context):
        """
        Получает доступ к контексту Django
        """
        user = context.get('user')
        request = context.get('request')
        
        return {
            "user": user,
            "is_authenticated": user.is_authenticated if user else False,
            "current_path": request.path if request else "",
        }
```

### 8. Обработка ошибок

```python
from django_components import Component

class ErrorHandlingComponent(Component):
    template_name = "components/error_handling.html"
    
    def get_context_data(self, data_source=None):
        try:
            # Потенциально опасная операция
            processed_data = self.process_data(data_source)
            
            return {
                "data": processed_data,
                "error": None,
            }
        except Exception as e:
            # Возвращаем информацию об ошибке
            return {
                "data": None,
                "error": str(e),
                "error_type": type(e).__name__,
            }
```

### 9. Оптимизация загрузки статических файлов

```python
class OptimizedComponent(Component):
    template_name = "components/optimized.html"
    
    # Загружаем только необходимые файлы
    css_dependencies = [
        "components/optimized.css",
        "components/shared.css",  # Общие стили
    ]
    
    js_dependencies = [
        "components/optimized.js",
    ]
    
    def get_context_data(self):
        # Минимальная логика
        return {"data": self.get_minimal_data()}
```

## Совместимость с Django 6

### Использование новых возможностей

Django 6 вводит улучшенные механизмы для работы с частичными шаблонами:

```python
class ModernComponent(Component):
    """Компонент использующий новые возможности Django 6"""
    template_name = "components/modern_component.html"
    
    def get_context_data(self):
        # Используем новые API Django 6
        return {
            "data": self.process_with_new_apis(),
        }
```

### Миграция с предыдущих версий

```python
# Для миграции с django-template-partials
class MigratedComponent(Component):
    """
    Компонент мигрированный с django-template-partials
    """
    template_name = "components/migrated.html"
    
    # Сохраняем совместимость со старым кодом
    def get_context_data(self, *args, **kwargs):
        # Конвертируем старые параметры в новые
        return self.convert_legacy_context(*args, **kwargs)
```

## Заключение

Django-components - мощный инструмент для создания переиспользуемых компонентов, но требует внимательного подхода к производительности. Следуя best practices, можно создавать эффективные и поддерживаемые компоненты, которые улучшают структуру проекта и ускоряют разработку.