# Стилизация и JavaScript в компонентах

## CSS в компонентах

### Встроенные стили

```python
from django_components import Component, register

@register("button")
class Button(Component):
    template = """
        <button class="btn">{{ text }}</button>
    """
    
    css = """
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
        }
        .btn:hover {
            background-color: #0056b3;
        }
    """
```

### Отдельные CSS файлы

```python
class Calendar(Component):
    template_file = "calendar.html"
    css_file = "calendar.css"
```

```css
/* calendar.css */
.calendar {
    width: 200px;
    background: pink;
}
.calendar span {
    font-weight: bold;
}
```

## JavaScript в компонентах

### Встроенный JavaScript

```python
class Calendar(Component):
    template = """
        <div class="calendar">
            Today's date is <span>{{ date }}</span>
        </div>
    """
    
    js = """
        (function () {
            document.querySelector(".calendar").onclick = () => {
                alert("Clicked calendar!");
            };
        })();
    """
```

### Отдельные JS файлы

```python
class Button(Component):
    template_file = "button.html"
    js_file = "button.js"
```

```javascript
// button.js
(function () {
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'scale(1)';
            }, 150);
        });
    });
})();
```

## Media зависимости

### Внешние зависимости

```python
class Calendar(Component):
    template_file = "calendar.html"

    class Media:
        js = [
            "path/to/shared.js",
            "path/to/*.js",  # Glob pattern
            "https://unpkg.com/alpinejs@3.14.7/dist/cdn.min.js",
        ]
        css = [
            "path/to/shared.css",
            "path/to/*.css",  # Glob pattern
            "https://unpkg.com/tailwindcss@^2/dist/tailwind.min.css",
        ]
```

## Передача данных в CSS и JS

### Раздельные методы для данных

```python
class ProfileCard(Component):
    class Kwargs:
        user_id: int
        show_details: bool = True

    def get_template_data(self, args, kwargs, slots, context):
        user = User.objects.get(id=kwargs.user_id)
        return {
            "user": user,
            "show_details": kwargs.show_details,
        }

    def get_js_data(self, args, kwargs, slots, context):
        return {
            "user_id": kwargs.user_id,
        }

    def get_css_data(self, args, kwargs, slots, context):
        text_color = "red" if kwargs.show_details else "blue"
        return {
            "text_color": text_color,
        }
```

### Использование данных в CSS

```python
class ThemeComponent(Component):
    css = """
        .theme-component {
            color: {{ text_color }};
            background-color: {{ bg_color }};
        }
    """
    
    def get_css_data(self, args, kwargs, slots, context):
        return {
            "text_color": "#333",
            "bg_color": "#f5f5f5",
        }
```

## HTML атрибуты

### Управление классами и стилями

```python
class Button(Component):
    template = """
        <button {% html_attrs class=class_dict style=style_dict %}>
            {{ text }}
        </button>
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "text": kwargs.get("text", "Click me"),
            "class_dict": {
                "btn": True,
                "btn-primary": kwargs.get("primary", False),
                "btn-disabled": kwargs.get("disabled", False),
            },
            "style_dict": {
                "background-color": "blue" if kwargs.get("primary") else "gray",
                "color": "white",
                "padding": "8px 16px",
            },
        }
```

## Интеграция с frontend фреймворками

### Alpine.js

```python
class Dropdown(Component):
    template = """
        <div x-data="{ open: false }">
            <button @click="open = !open">
                {{ trigger_text }}
            </button>
            <div x-show="open" @click.outside="open = false">
                {% slot "content" %}{% endslot %}
            </div>
        </div>
    """
    
    class Media:
        js = ["https://unpkg.com/alpinejs@3.14.7/dist/cdn.min.js"]
```

### HTMX

```python
class TodoList(Component):
    template = """
        <div hx-get="/todos/" hx-trigger="load">
            Loading todos...
        </div>
    """
    
    class Media:
        js = ["https://unpkg.com/htmx.org@1.9.10"]
```

## Стратегии рендеринга

### Управление зависимостями

```python
# Рендеринг с append стратегией
html = MyComponent.render(deps_strategy="append")

# Рендеринг с ignore стратегией
html = MyComponent.render(deps_strategy="ignore")
```

### Стратегии по умолчанию

- **inline** - CSS и JS встраиваются в HTML
- **append** - зависимости добавляются после компонента
- **ignore** - зависимости игнорируются
- **document** - зависимости подключаются как внешние файлы

## Best Practices

### CSS

1. **Используйте scoped стили** через классы компонентов
2. **Избегайте глобальных селекторов**
3. **Используйте CSS переменные** для темизации
4. **Минимизируйте специфичность** селекторов

### JavaScript

1. **Используйте IIFE** для изоляции кода
2. **Избегайте глобальных переменных**
3. **Используйте event delegation** для динамического контента
4. **Обрабатывайте ошибки** корректно

### Производительность

1. **Минимизируйте размер CSS и JS**
2. **Используйте ленивую загрузку** для тяжелых компонентов
3. **Кэшируйте статические ресурсы**
4. **Оптимизируйте критический путь** рендеринга

---

**Следующий раздел**: [Интеграция с Django 6](./06-django6-integration.md)