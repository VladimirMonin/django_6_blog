# Пример 6: Компонент Alert

## Python класс

```python
# components/alert.py
from django_components import Component, Slot

class Alert(Component):
    template_name = "components/alert.html"
    css_dependencies = ["components/alert.css"]
    js_dependencies = ["components/alert.js"]
    
    class Slots:
        message: Slot
    
    def get_context_data(self, alert_type="info", dismissible=True):
        return {
            "alert_type": alert_type,
            "dismissible": dismissible,
        }
```

## HTML шаблон

```html
<!-- templates/components/alert.html -->
<div class="alert alert-{{ alert_type }} {% if dismissible %}alert-dismissible{% endif %}" 
     role="alert"
     data-alert-id="alert-{{ id }}">
    {{ slots.message }}
    
    {% if dismissible %}
    <button type="button" class="alert-close" aria-label="Close">
        <span>&times;</span>
    </button>
    {% endif %}
</div>
```

## CSS стили

```css
/* static/components/alert.css */
.alert {
    padding: 1rem;
    border: 1px solid transparent;
    border-radius: 4px;
    margin-bottom: 1rem;
    position: relative;
}

.alert-dismissible {
    padding-right: 3rem;
}

.alert-info {
    color: #055160;
    background-color: #cff4fc;
    border-color: #b6effb;
}

.alert-success {
    color: #0f5132;
    background-color: #d1e7dd;
    border-color: #badbcc;
}

.alert-warning {
    color: #664d03;
    background-color: #fff3cd;
    border-color: #ffecb5;
}

.alert-danger {
    color: #842029;
    background-color: #f8d7da;
    border-color: #f5c2c7;
}

.alert-close {
    position: absolute;
    top: 0;
    right: 0;
    padding: 1rem;
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    line-height: 1;
}

.alert-close:hover {
    opacity: 0.7;
}
```

## JavaScript логика

```javascript
// static/components/alert.js
class AlertComponent {
    constructor(element) {
        this.element = element;
        this.closeButton = element.querySelector('.alert-close');
        this.init();
    }
    
    init() {
        if (this.closeButton) {
            this.closeButton.addEventListener('click', () => {
                this.hide();
            });
        }
        
        // Автоматическое скрытие через 5 секунд
        setTimeout(() => {
            if (this.element.parentNode) {
                this.hide();
            }
        }, 5000);
    }
    
    hide() {
        this.element.style.opacity = '0';
        this.element.style.transition = 'opacity 0.3s ease';
        
        setTimeout(() => {
            if (this.element.parentNode) {
                this.element.parentNode.removeChild(this.element);
            }
        }, 300);
    }
}

// Автоматическая инициализация
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.alert').forEach(el => {
        new AlertComponent(el);
    });
});
```

## Использование

```html
{% load component_tags %}

<!-- Различные типы алертов -->
{% component "alert" alert_type="info" %}
    {% fill "message" %}
        <strong>Info!</strong> This is an informational message.
    {% endfill %}
{% endcomponent %}

{% component "alert" alert_type="success" %}
    {% fill "message" %}
        <strong>Success!</strong> Your action was completed successfully.
    {% endfill %}
{% endcomponent %}

{% component "alert" alert_type="warning" %}
    {% fill "message" %}
        <strong>Warning!</strong> Please check your input.
    {% endfill %}
{% endcomponent %}

{% component "alert" alert_type="danger" %}
    {% fill "message" %}
        <strong>Error!</strong> Something went wrong.
    {% endfill %}
{% endcomponent %}

<!-- Alert без возможности закрытия -->
{% component "alert" alert_type="info" dismissible=False %}
    {% fill "message" %}
        This is a persistent message that cannot be dismissed.
    {% endfill %}
{% endcomponent %}
```

# Пример 7: Компонент Navbar

## Python класс

```python
# components/navbar.py
from django_components import Component, Slot

class Navbar(Component):
    template_name = "components/navbar.html"
    css_dependencies = ["components/navbar.css"]
    js_dependencies = ["components/navbar.js"]
    
    class Slots:
        brand: Slot
        menu: Slot
        user_menu: Slot
    
    def get_context_data(self, brand_text="", fixed_top=False):
        return {
            "brand_text": brand_text,
            "fixed_top": fixed_top,
        }
```

## HTML шаблон

```html
<!-- templates/components/navbar.html -->
<nav class="navbar {% if fixed_top %}navbar-fixed-top{% endif %}">
    <div class="navbar-container">
        <!-- Brand -->
        <div class="navbar-brand">
            {% if slots.brand %}
                {{ slots.brand }}
            {% else %}
                <a href="/" class="brand-link">{{ brand_text }}</a>
            {% endif %}
        </div>
        
        <!-- Main Menu -->
        {% if slots.menu %}
        <div class="navbar-menu">
            {{ slots.menu }}
        </div>
        {% endif %}
        
        <!-- User Menu -->
        {% if slots.user_menu %}
        <div class="navbar-user-menu">
            {{ slots.user_menu }}
        </div>
        {% endif %}
        
        <!-- Mobile Toggle -->
        <button class="navbar-toggle" aria-label="Toggle navigation">
            <span></span>
            <span></span>
            <span></span>
        </button>
    </div>
</nav>
```

## CSS стили

```css
/* static/components/navbar.css */
.navbar {
    background-color: #343a40;
    color: white;
    padding: 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navbar-fixed-top {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 1030;
}

.navbar-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

.navbar-brand {
    font-size: 1.25rem;
    font-weight: 600;
}

.brand-link {
    color: white;
    text-decoration: none;
}

.brand-link:hover {
    color: #adb5bd;
}

.navbar-menu {
    display: flex;
    gap: 2rem;
    align-items: center;
}

.navbar-user-menu {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.navbar-toggle {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
    flex-direction: column;
    gap: 0.25rem;
}

.navbar-toggle span {
    display: block;
    width: 25px;
    height: 3px;
    background-color: white;
    transition: all 0.3s ease;
}

/* Mobile styles */
@media (max-width: 768px) {
    .navbar-menu,
    .navbar-user-menu {
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background-color: #343a40;
        flex-direction: column;
        padding: 1rem;
        gap: 1rem;
    }
    
    .navbar-menu.show,
    .navbar-user-menu.show {
        display: flex;
    }
    
    .navbar-toggle {
        display: flex;
    }
    
    .navbar-toggle.active span:nth-child(1) {
        transform: rotate(45deg) translate(5px, 5px);
    }
    
    .navbar-toggle.active span:nth-child(2) {
        opacity: 0;
    }
    
    .navbar-toggle.active span:nth-child(3) {
        transform: rotate(-45deg) translate(7px, -6px);
    }
}
```

## JavaScript логика

```javascript
// static/components/navbar.js
class NavbarComponent {
    constructor(element) {
        this.element = element;
        this.toggleButton = element.querySelector('.navbar-toggle');
        this.menu = element.querySelector('.navbar-menu');
        this.userMenu = element.querySelector('.navbar-user-menu');
        this.init();
    }
    
    init() {
        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', () => {
                this.toggleMobileMenu();
            });
        }
        
        // Закрытие меню при клике вне его
        document.addEventListener('click', (e) => {
            if (!this.element.contains(e.target)) {
                this.closeMobileMenu();
            }
        });
    }
    
    toggleMobileMenu() {
        this.toggleButton.classList.toggle('active');
        
        if (this.menu) {
            this.menu.classList.toggle('show');
        }
        
        if (this.userMenu) {
            this.userMenu.classList.toggle('show');
        }
    }
    
    closeMobileMenu() {
        this.toggleButton.classList.remove('active');
        
        if (this.menu) {
            this.menu.classList.remove('show');
        }
        
        if (this.userMenu) {
            this.userMenu.classList.remove('show');
        }
    }
}

// Автоматическая инициализация
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.navbar').forEach(el => {
        new NavbarComponent(el);
    });
});
```

## Использование

```html
{% load component_tags %}

{% component "navbar" brand_text="MyApp" fixed_top=True %}
    {% fill "brand" %}
        <a href="/" class="brand-link">
            <img src="/static/logo.png" alt="Logo" style="height: 30px; margin-right: 10px;">
            MyApp
        </a>
    {% endfill %}
    
    {% fill "menu" %}
        <a href="/" class="nav-link">Home</a>
        <a href="/about/" class="nav-link">About</a>
        <a href="/services/" class="nav-link">Services</a>
        <a href="/contact/" class="nav-link">Contact</a>
    {% endfill %}
    
    {% fill "user_menu" %}
        {% if user.is_authenticated %}
            <span class="nav-text">Welcome, {{ user.username }}</span>
            <a href="/profile/" class="nav-link">Profile</a>
            <a href="/logout/" class="nav-link">Logout</a>
        {% else %}
            <a href="/login/" class="nav-link">Login</a>
            <a href="/register/" class="nav-link">Register</a>
        {% endif %}
    {% endfill %}
{% endcomponent %}
```