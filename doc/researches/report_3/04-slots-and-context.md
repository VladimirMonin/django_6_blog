# Slots и передача контекста

## Что такое Slots

Slots (слоты) - это механизм для передачи контента в компоненты, аналогичный slots в Vue.js или children в React.

## Базовые слоты

### Компонент со слотами

```python
from django_components import Component, register

@register("card")
class Card(Component):
    template = """
        <div class="card">
            <div class="card-header">
                {% slot "header" %}
                    Default Header
                {% endslot %}
            </div>
            <div class="card-body">
                {% slot "body" %}
                    Default Body
                {% endslot %}
            </div>
            <div class="card-footer">
                {% slot "footer" %}
                    Default Footer
                {% endslot %}
            </div>
        </div>
    """
```

### Заполнение слотов

```django
{% component "card" %}
    {% fill "header" %}
        <h2>Custom Header</h2>
    {% endfill %}
    
    {% fill "body" %}
        <p>This is custom body content.</p>
    {% endfill %}
    
    {% fill "footer" %}
        <button>Custom Button</button>
    {% endfill %}
{% endcomponent %}
```

## Слоты с данными

### Передача данных в слоты

```python
class Table(Component):
    template = """
        <table>
            <thead>
                <tr>
                    {% for header in headers %}
                        <th>
                            {% slot "header-{{ header.key }}" value=header.title %}
                                {{ header.title }}
                            {% endslot %}
                        </th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                    <tr>
                        {% for header in headers %}
                            <td>
                                {% slot "cell-{{ header.key }}" value=item[header.key] %}
                                    {{ item[header.key] }}
                                {% endslot %}
                            </td>
                        {% endfor %}
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    """
```

### Использование с данными

```django
{% component "table" headers=headers items=items %}
    {% fill "header-name" data="data" %}
        <b>{{ data.value }}</b>
    {% endfill %}
    
    {% fill "cell-age" data="data" %}
        <span style="color: {{ data.value > 30 ? 'red' : 'green' }}">
            {{ data.value }}
        </span>
    {% endfill %}
{% endcomponent %}
```

## Программная работа со слотами

### Slots в Python

```python
from django_components import Component, Slot

class Table(Component):
    def on_render_before(self, context, template):
        # Доступ к слотам
        header_slot = self.slots["header"]
        footer_slot = self.slots["footer"]
        
        # Рендеринг слота с данными
        header_content = header_slot({"user": "John"})
```

### Создание слотов программно

```python
def footer_slot(ctx):
    if ctx.data["disabled"]:
        return ctx.fallback
    
    item = ctx.data["item"]
    if ctx.data["type"] == "table":
        return f"<tr><td>{item}</td></tr>"
    else:
        return f"<li>{item}</li>"

# Использование
Table.render(
    slots={
        "prepend": "Ice cream selection:",
        "append": Slot("© 2025"),
        "row": footer_slot,
        "column_title": Slot(lambda ctx: f"<th>{ctx.data['name']}</th>"),
    },
)
```

## Provide/Inject паттерн

### Передача контекста через дерево компонентов

```django
{# Provide данных для дерева компонентов #}
<body>
    {% provide "theme" variant="light" mode="system" %}
        {% component "header" / %}
        {% component "sidebar" / %}
        {% component "main" / %}
    {% endprovide %}
</body>
```

### Получение данных в компонентах

```python
from django_components import Component, register

@register("header")
class Header(Component):
    template = """
        <header class="theme-{{ theme }}">
            Header content
        </header>
    """

    def get_template_data(self, args, kwargs, slots, context):
        # Получение предоставленных данных
        theme_data = self.inject("theme")
        return {
            "theme": theme_data.variant,
        }
```

## Динамические слоты

### Динамическое заполнение слотов

```python
class MyTable(Component):
    template = """
        <div>
          {% component "child" %}
            {% for slot_name, slot in component_vars.slots.items %}
              {% fill name=slot_name body=slot / %}
            {% endfor %}
          {% endcomponent %}
        </div>
    """
```

### Слоты с динамическими именами

```django
{% component "table" headers=headers items=items %}
    {% fill "header-{{ active_header_name }}" data="data" %}
        <b>{{ data.value }}</b>
    {% endfill %}
{% endcomponent %}
```

## Spread оператор для props

### Передача словаря как props

```python
post_data = {
    "title": "How to...",
    "date": "2015-06-19",
    "author": "John Wick",
}
```

```django
{% component "calendar" ...post_data / %}

{# Комбинация с другими props #}
{% component "calendar" ...post_data id=post.id ...extra / %}
```

## Контекст в слотах

### Доступ к контексту Django

```python
class Table(Component):
    template = """
        {% with "abc" as my_var %}
            {% slot "name" %}
                Hello!
            {% endslot %}
        {% endwith %}
    """

def slot_func(ctx):
    # Доступ к переменной контекста 'my_var'
    return f"Hello, {ctx.context['my_var']}!"
```

## Best Practices для слотов

### Организация слотов

1. **Используйте осмысленные имена** слотов
2. **Предоставляйте значения по умолчанию**
3. **Документируйте ожидаемые данные** для слотов
4. **Используйте типизацию** для сложных слотов

### Производительность

1. **Избегайте глубокой вложенности** слотов
2. **Минимизируйте передачу данных** между слотами
3. **Используйте кэширование** для статических слотов

---

**Следующий раздел**: [Стилизация и JavaScript](./05-styling-and-javascript.md)