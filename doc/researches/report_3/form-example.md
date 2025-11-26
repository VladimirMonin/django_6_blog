# Пример 4: Компонент Form с валидацией

## Python класс

```python
# components/form.py
from typing import Optional
from django_components import Component, Slot, SlotInput

class Form(Component):
    template_name = "components/form.html"
    css_dependencies = ["components/form.css"]
    
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
        return {
            "method": args.method,
            "action": args.action,
            "enctype": kwargs.get("enctype"),
            "css_class": kwargs.get("css_class", ""),
            "fields": slots.fields,
            "buttons": slots.buttons,
        }
```

## HTML шаблон

```html
<!-- templates/components/form.html -->
<form 
    method="{{ method }}" 
    action="{{ action }}"
    {% if enctype %}enctype="{{ enctype }}"{% endif %}
    class="form {{ css_class }}"
>
    {% csrf_token %}
    
    <div class="form-fields">
        {{ fields }}
    </div>
    
    {% if buttons %}
    <div class="form-buttons">
        {{ buttons }}
    </div>
    {% endif %}
</form>
```

## CSS стили

```css
/* static/components/form.css */
.form {
    max-width: 500px;
    margin: 0 auto;
}

.form-fields {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.form-buttons {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
}

.form-group {
    display: flex;
    flex-direction: column;
}

.form-label {
    margin-bottom: 0.5rem;
    font-weight: 600;
}

.form-input {
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
}

.form-input:focus {
    outline: none;
    border-color: #007bff;
    box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}
```

## Использование

```html
{% load component_tags %}

{% component "form" method="POST" action="/submit/" %}
    {% fill "fields" %}
        <div class="form-group">
            <label class="form-label" for="name">Name</label>
            <input type="text" id="name" name="name" class="form-input" required>
        </div>
        
        <div class="form-group">
            <label class="form-label" for="email">Email</label>
            <input type="email" id="email" name="email" class="form-input" required>
        </div>
        
        <div class="form-group">
            <label class="form-label" for="message">Message</label>
            <textarea id="message" name="message" class="form-input" rows="4" required></textarea>
        </div>
    {% endfill %}
    
    {% fill "buttons" %}
        <button type="submit" class="btn btn-primary">Submit</button>
        <button type="reset" class="btn btn-secondary">Reset</button>
    {% endfill %}
{% endcomponent %}
```

## Пример 5: Компонент Table с пагинацией

### Python класс

```python
# components/table.py
from django.core.paginator import Paginator
from django_components import Component, Slot

class Table(Component):
    template_name = "components/table.html"
    css_dependencies = ["components/table.css"]
    
    class Slots:
        headers: Slot
        rows: Slot
    
    def get_context_data(self, items, page_size=10, current_page=1):
        paginator = Paginator(items, page_size)
        page = paginator.get_page(current_page)
        
        return {
            "page": page,
            "paginator": paginator,
        }
```

### HTML шаблон

```html
<!-- templates/components/table.html -->
<div class="table-component">
    <table class="table">
        <thead>
            <tr>
                {{ slots.headers }}
            </tr>
        </thead>
        <tbody>
            {{ slots.rows }}
        </tbody>
    </table>
    
    {% if paginator.num_pages > 1 %}
    <div class="table-pagination">
        <nav>
            <ul class="pagination">
                {% if page.has_previous %}
                <li class="page-item">
                    <a class="page-link" href="?page={{ page.previous_page_number }}">Previous</a>
                </li>
                {% endif %}
                
                {% for num in page.paginator.page_range %}
                <li class="page-item {% if page.number == num %}active{% endif %}">
                    <a class="page-link" href="?page={{ num }}">{{ num }}</a>
                </li>
                {% endfor %}
                
                {% if page.has_next %}
                <li class="page-item">
                    <a class="page-link" href="?page={{ page.next_page_number }}">Next</a>
                </li>
                {% endif %}
            </ul>
        </nav>
    </div>
    {% endif %}
</div>
```

### CSS стили

```css
/* static/components/table.css */
.table-component {
    margin: 1rem 0;
}

.table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
}

.table th,
.table td {
    padding: 0.75rem;
    border: 1px solid #dee2e6;
    text-align: left;
}

.table th {
    background-color: #f8f9fa;
    font-weight: 600;
}

.table-pagination {
    display: flex;
    justify-content: center;
}

.pagination {
    display: flex;
    list-style: none;
    padding: 0;
    margin: 0;
}

.page-item {
    margin: 0 0.25rem;
}

.page-link {
    display: block;
    padding: 0.5rem 0.75rem;
    border: 1px solid #dee2e6;
    text-decoration: none;
    color: #007bff;
    background-color: white;
}

.page-item.active .page-link {
    background-color: #007bff;
    border-color: #007bff;
    color: white;
}

.page-link:hover {
    background-color: #e9ecef;
}
```

### Использование

```html
{% load component_tags %}

{% component "table" items=users page_size=5 current_page=request.GET.page %}
    {% fill "headers" %}
        <th>ID</th>
        <th>Name</th>
        <th>Email</th>
        <th>Actions</th>
    {% endfill %}
    
    {% fill "rows" %}
        {% for user in page.object_list %}
        <tr>
            <td>{{ user.id }}</td>
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>
                <button class="btn btn-sm btn-primary">Edit</button>
                <button class="btn btn-sm btn-danger">Delete</button>
            </td>
        </tr>
        {% endfor %}
    {% endfill %}
{% endcomponent %}
```