# Создание компонентов

## Структура компонента

Компонент в django-components состоит из нескольких частей:

- **Python класс** - логика компонента
- **HTML шаблон** - структура компонента
- **CSS стили** - внешний вид
- **JavaScript** - интерактивность

## Базовый компонент

### Простой компонент

```python
from django_components import Component, register

@register("button")
class Button(Component):
    template = """
        <button class="btn btn-{{ variant }}">
            {{ text }}
        </button>
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "text": kwargs.get("text", "Click me"),
            "variant": kwargs.get("variant", "primary"),
        }
```

### Использование

```django
{% component "button" text="Save" variant="success" / %}
```

## Компоненты с файлами

### Отдельные файлы

```python
# components/calendar/calendar.py
from django_components import Component, register

@register("calendar")
class Calendar(Component):
    template_file = "calendar.html"
    css_file = "calendar.css"
    js_file = "calendar.js"

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "date": kwargs.get("date", "2025-01-01"),
        }
```

### Файлы компонента

```html
<!-- calendar.html -->
<div class="calendar">
    Today's date is <span>{{ date }}</span>
</div>
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

```javascript
// calendar.js
(function () {
    document.querySelector(".calendar").onclick = () => {
        alert("Clicked calendar!");
    };
})();
```

## Типизация компонентов

### Валидация входных данных

```python
from typing import Optional
from django.template import Context
from django_components import Component, Slot, SlotInput

class Button(Component):
    class Args:
        size: int
        text: str

    class Kwargs:
        variable: str
        another: int
        maybe_var: Optional[int] = None

    class Slots:
        my_slot: Optional[SlotInput] = None
        another_slot: SlotInput

    def get_template_data(self, args: Args, kwargs: Kwargs, slots: Slots, context: Context):
        args.size  # int
        kwargs.variable  # str
        slots.my_slot  # Slot[MySlotData]
```

## Single File Components

### Все в одном файле

```python
from django_components import Component, register

@register("profile_card")
class ProfileCard(Component):
    template: types.django_html = """
        <div class="profile-card">
            <img src="{{ user.avatar }}" alt="{{ user.name }}">
            <h3>{{ user.name }}</h3>
            <p>{{ user.bio }}</p>
        </div>
    """

    css: types.css = """
        .profile-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 16px;
            max-width: 300px;
        }
        .profile-card img {
            width: 100%;
            border-radius: 50%;
        }
    """

    js: types.js = """
        (function() {
            document.querySelectorAll('.profile-card').forEach(card => {
                card.addEventListener('click', () => {
                    console.log('Profile card clicked');
                });
            });
        })();
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "user": kwargs["user"],
        }
```

## Динамические компоненты

### Компонент с динамическим выбором

```python
from django_components import Component, register

@register("dynamic")
class DynamicComponent(Component):
    def on_render(self, context, template):
        component_name = self.kwargs.get("is")
        # Динамически рендерим другой компонент
        return Component.render_by_name(
            component_name,
            context=context,
            kwargs=self.kwargs._asdict(),
            slots=self.slots,
        )
```

### Использование

```django
{% component "dynamic" is="button" text="Dynamic Button" / %}
```

## Расширенные возможности

### Media зависимости

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

### HTML атрибуты

```python
class Button(Component):
    template = """
        <button {% html_attrs class=class_dict style=style_dict %}>Click me</button>
    """

    def get_template_data(self, args, kwargs, slots, context):
        return {
            "class_dict": {
                "btn": True,
                "btn-primary": kwargs.get("primary", False),
                "btn-disabled": kwargs.get("disabled", False),
            },
            "style_dict": {
                "background-color": "blue" if kwargs.get("primary") else "gray",
                "color": "white",
            },
        }
```

## Best Practices

### Организация компонентов

1. **Группируйте по функциональности** - кнопки, формы, карточки
2. **Используйте отдельные файлы** для сложных компонентов
3. **Single File Components** для простых компонентов
4. **Следуйте соглашениям именования**

### Производительность

1. **Минимизируйте зависимости** между компонентами
2. **Используйте кэширование** для статических компонентов
3. **Оптимизируйте CSS и JS**
4. **Избегайте глубокой вложенности**

---

**Следующий раздел**: [Slots и передача контекста](./04-slots-and-context.md)