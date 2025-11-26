# Практические примеры Django Components

## Пример 1: Компонент Button

### Python класс

```python
# components/button.py
from django_components import Component

class Button(Component):
    template_name = "components/button.html"
    css_dependencies = ["components/button.css"]
    
    def get_context_data(self, text="Click me", variant="primary", size="md", disabled=False):
        return {
            "text": text,
            "variant": variant,
            "size": size,
            "disabled": disabled,
        }
```

### HTML шаблон

```html
<!-- templates/components/button.html -->
<button 
    class="btn btn-{{ variant }} btn-{{ size }}"
    {% if disabled %}disabled{% endif %}
>
    {{ text }}
</button>
```

### CSS стили

```css
/* static/components/button.css */
.btn {
    display: inline-block;
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    text-decoration: none;
    transition: all 0.2s ease;
}

.btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* Variants */
.btn-primary {
    background-color: #007bff;
    color: white;
}

.btn-primary:hover:not(:disabled) {
    background-color: #0056b3;
}

.btn-secondary {
    background-color: #6c757d;
    color: white;
}

.btn-secondary:hover:not(:disabled) {
    background-color: #545b62;
}

.btn-danger {
    background-color: #dc3545;
    color: white;
}

.btn-danger:hover:not(:disabled) {
    background-color: #c82333;
}

/* Sizes */
.btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
}

.btn-md {
    padding: 0.5rem 1rem;
    font-size: 1rem;
}

.btn-lg {
    padding: 0.75rem 1.5rem;
    font-size: 1.25rem;
}
```

### Использование

```html
{% load component_tags %}

{% component "button" text="Primary Button" variant="primary" %}
{% component "button" text="Secondary Button" variant="secondary" %}
{% component "button" text="Danger Button" variant="danger" size="lg" %}
{% component "button" text="Disabled Button" variant="primary" disabled=True %}
```

## Пример 2: Компонент Card со слотами

### Python класс

```python
# components/card.py
from django_components import Component, Slot

class Card(Component):
    template_name = "components/card.html"
    css_dependencies = ["components/card.css"]
    
    class Slots:
        header: Slot
        body: Slot
        footer: Slot
    
    def get_context_data(self, title="", css_class=""):
        return {
            "title": title,
            "css_class": css_class,
        }
```

### HTML шаблон

```html
<!-- templates/components/card.html -->
<div class="card {{ css_class }}">
    {% if slots.header %}
    <div class="card-header">
        {{ slots.header }}
    </div>
    {% endif %}
    
    <div class="card-body">
        {% if title %}
        <h5 class="card-title">{{ title }}</h5>
        {% endif %}
        {{ slots.body }}
    </div>
    
    {% if slots.footer %}
    <div class="card-footer">
        {{ slots.footer }}
    </div>
    {% endif %}
</div>
```

### CSS стили

```css
/* static/components/card.css */
.card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    background-color: white;
    margin-bottom: 1rem;
}

.card-header {
    background-color: #f8f9fa;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid #e0e0e0;
    border-radius: 8px 8px 0 0;
}

.card-body {
    padding: 1.25rem;
}

.card-title {
    margin: 0 0 0.5rem 0;
    font-size: 1.25rem;
    font-weight: 600;
}

.card-footer {
    background-color: #f8f9fa;
    padding: 1rem 1.25rem;
    border-top: 1px solid #e0e0e0;
    border-radius: 0 0 8px 8px;
}
```

### Использование со слотами

```html
{% load component_tags %}

{% component "card" title="Product Card" %}
    {% fill "header" %}
        <div class="d-flex justify-content-between align-items-center">
            <span class="badge bg-primary">New</span>
            <span class="text-muted">$99.99</span>
        </div>
    {% endfill %}
    
    {% fill "body" %}
        <p>This is an amazing product description that explains all the features and benefits.</p>
        <ul>
            <li>Feature 1</li>
            <li>Feature 2</li>
            <li>Feature 3</li>
        </ul>
    {% endfill %}
    
    {% fill "footer" %}
        <div class="d-flex gap-2">
            <button class="btn btn-primary">Buy Now</button>
            <button class="btn btn-outline-secondary">Learn More</button>
        </div>
    {% endfill %}
{% endcomponent %}
```

## Пример 3: Компонент Modal с JavaScript

### Python класс

```python
# components/modal.py
from django_components import Component, Slot

class Modal(Component):
    template_name = "components/modal.html"
    css_dependencies = ["components/modal.css"]
    js_dependencies = ["components/modal.js"]
    
    class Slots:
        content: Slot
    
    def get_context_data(self, title="", modal_id=""):
        return {
            "title": title,
            "modal_id": modal_id or f"modal-{id(self)}",
        }
```

### HTML шаблон

```html
<!-- templates/components/modal.html -->
<div class="modal-component" data-modal-id="{{ modal_id }}">
    <div class="modal-backdrop"></div>
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">{{ title }}</h5>
                <button type="button" class="modal-close" aria-label="Close">
                    <span>&times;</span>
                </button>
            </div>
            <div class="modal-body">
                {{ slots.content }}
            </div>
        </div>
    </div>
</div>
```

### CSS стили

```css
/* static/components/modal.css */
.modal-component {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1050;
}

.modal-component.show {
    display: block;
}

.modal-backdrop {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
}

.modal-dialog {
    position: relative;
    width: 500px;
    max-width: 90%;
    margin: 2rem auto;
    z-index: 1051;
}

.modal-content {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e0e0e0;
}

.modal-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
}

.modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-close:hover {
    background-color: #f8f9fa;
    border-radius: 4px;
}

.modal-body {
    padding: 1.5rem;
}
```

### JavaScript логика

```javascript
// static/components/modal.js
class ModalComponent {
    constructor(element) {
        this.element = element;
        this.modalId = element.dataset.modalId;
        this.backdrop = element.querySelector('.modal-backdrop');
        this.closeButton = element.querySelector('.modal-close');
        this.init();
    }
    
    init() {
        // Закрытие по клику на backdrop
        this.backdrop.addEventListener('click', () => {
            this.hide();
        });
        
        // Закрытие по клику на кнопку
        this.closeButton.addEventListener('click', () => {
            this.hide();
        });
        
        // Закрытие по ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible()) {
                this.hide();
            }
        });
    }
    
    show() {
        this.element.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
    
    hide() {
        this.element.classList.remove('show');
        document.body.style.overflow = '';
    }
    
    isVisible() {
        return this.element.classList.contains('show');
    }
}

// Глобальные методы для управления модальными окнами
window.ModalManager = {
    modals: {},
    
    show(modalId) {
        const element = document.querySelector(`[data-modal-id="${modalId}"]`);
        if (element && window.ModalManager.modals[modalId]) {
            window.ModalManager.modals[modalId].show();
        }
    },
    
    hide(modalId) {
        const element = document.querySelector(`[data-modal-id="${modalId}"]`);
        if (element && window.ModalManager.modals[modalId]) {
            window.ModalManager.modals[modalId].hide();
        }
    }
};

// Автоматическая инициализация
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-modal-id]').forEach(el => {
        const modalId = el.dataset.modalId;
        window.ModalManager.modals[modalId] = new ModalComponent(el);
    });
});
```

### Использование

```html
{% load component_tags %}

<!-- Модальное окно -->
{% component "modal" title="Confirmation" modal_id="confirm-modal" %}
    {% fill "content" %}
        <p>Are you sure you want to delete this item?</p>
        <div class="d-flex gap-2">
            <button class="btn btn-danger" onclick="ModalManager.hide('confirm-modal')">
                Delete
            </button>
            <button class="btn btn-secondary" onclick="ModalManager.hide('confirm-modal')">
                Cancel
            </button>
        </div>
    {% endfill %}
{% endcomponent %}

<!-- Кнопка для открытия модального окна -->
<button class="btn btn-primary" onclick="ModalManager.show('confirm-modal')">
    Open Modal
</button>
```

## Пример 4: Компонент Form с валидацией

### Python класс

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

### HTML шаблон

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

### CSS стили

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

### Использование

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
    {% end