# Практические примеры использования Template Partials в Django 6

## Базовые примеры

### 1. Простая кнопка

```django
{# Определение компонента кнопки #}
{% partialdef button %}
    <button type="button" class="btn {{ class }}" {% if disabled %}disabled{% endif %}>
        {{ text }}
    </button>
{% endpartialdef %}

{# Использование #}
{% partial button with text="Сохранить" class="btn-primary" %}
{% partial button with text="Отмена" class="btn-secondary" %}
{% partial button with text="Удалить" class="btn-danger" disabled=True %}
```

### 2. Карточка с изображением

```django
{% partialdef image-card %}
    <div class="card">
        <img src="{{ image_url }}" class="card-img-top" alt="{{ title }}">
        <div class="card-body">
            <h5 class="card-title">{{ title }}</h5>
            <p class="card-text">{{ description }}</p>
            <div class="card-actions">
                {% partial button with text="Подробнее" class="btn-outline-primary" %}
                {% if show_like %}
                    {% partial button with text="❤️" class="btn-outline-danger" %}
                {% endif %}
            </div>
        </div>
    </div>
{% endpartialdef %}
```

## Продвинутые примеры

### 3. Навигационное меню

```django
{% partialdef navigation %}
    <nav class="navbar navbar-expand-lg {{ navbar_class }}">
        <div class="container">
            <a class="navbar-brand" href="{{ brand_url }}">
                {{ brand_name }}
            </a>
            
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
                    data-bs-target="#navbar-{{ nav_id }}">
                <span class="navbar-toggler-icon"></span>
            </button>
            
            <div class="collapse navbar-collapse" id="navbar-{{ nav_id }}">
                <ul class="navbar-nav me-auto">
                    {% for item in nav_items %}
                        <li class="nav-item">
                            <a class="nav-link {{ item.class }}" href="{{ item.url }}">
                                {{ item.title }}
                            </a>
                        </li>
                    {% endfor %}
                </ul>
                
                {% if user.is_authenticated %}
                    {% partial user-menu %}
                {% else %}
                    {% partial auth-buttons %}
                {% endif %}
            </div>
        </div>
    </nav>
{% endpartialdef %}

{# Вспомогательные компоненты #}
{% partialdef user-menu %}
    <div class="d-flex">
        <span class="navbar-text me-3">Привет, {{ user.username }}!</span>
        {% partial button with text="Выйти" class="btn-outline-secondary" %}
    </div>
{% endpartialdef %}

{% partialdef auth-buttons %}
    <div class="d-flex gap-2">
        {% partial button with text="Войти" class="btn-outline-primary" %}
        {% partial button with text="Регистрация" class="btn-primary" %}
    </div>
{% endpartialdef %}
```

### 4. Форма с валидацией

```django
{% partialdef form-field %}
    <div class="mb-3">
        <label for="{{ field.id }}" class="form-label">{{ field.label }}</label>
        
        {% if field.type == "text" or field.type == "email" %}
            <input type="{{ field.type }}" 
                   class="form-control {{ field.errors|yesno:'is-invalid,' }}" 
                   id="{{ field.id }}" 
                   name="{{ field.name }}" 
                   value="{{ field.value|default:'' }}"
                   {% if field.required %}required{% endif %}>
        
        {% elif field.type == "textarea" %}
            <textarea class="form-control {{ field.errors|yesno:'is-invalid,' }}" 
                      id="{{ field.id }}" 
                      name="{{ field.name }}"
                      rows="{{ field.rows|default:3 }}"
                      {% if field.required %}required{% endif %}>{{ field.value|default:'' }}</textarea>
        
        {% elif field.type == "select" %}
            <select class="form-select {{ field.errors|yesno:'is-invalid,' }}" 
                    id="{{ field.id }}" 
                    name="{{ field.name }}"
                    {% if field.required %}required{% endif %}>
                {% for option in field.options %}
                    <option value="{{ option.value }}" 
                            {% if option.value == field.value %}selected{% endif %}>
                        {{ option.label }}
                    </option>
                {% endfor %}
            </select>
        {% endif %}
        
        {% if field.help_text %}
            <div class="form-text">{{ field.help_text }}</div>
        {% endif %}
        
        {% if field.errors %}
            <div class="invalid-feedback">
                {{ field.errors.0 }}
            </div>
        {% endif %}
    </div>
{% endpartialdef %}

{# Использование формы #}
<form method="post">
    {% csrf_token %}
    
    {% partial form-field with field=form_fields.name %}
    {% partial form-field with field=form_fields.email %}
    {% partial form-field with field=form_fields.message %}
    
    <div class="d-flex gap-2">
        {% partial button with text="Отправить" type="submit" class="btn-primary" %}
        {% partial button with text="Очистить" type="reset" class="btn-secondary" %}
    </div>
</form>
```

## Примеры для блога

### 5. Компонент поста

```django
{% partialdef blog-post %}
    <article class="blog-post">
        <header class="post-header">
            <h2 class="post-title">
                <a href="{{ post.get_absolute_url }}">{{ post.title }}</a>
            </h2>
            
            <div class="post-meta">
                <span class="post-author">
                    {% partial user-avatar with user=post.author size="sm" %}
                    {{ post.author.username }}
                </span>
                <span class="post-date">{{ post.published_at|date:"d.m.Y H:i" }}</span>
                <span class="post-views">👁️ {{ post.views }}</span>
            </div>
        </header>
        
        <div class="post-content">
            {{ post.content|truncatewords:50 }}
        </div>
        
        <footer class="post-footer">
            <div class="post-tags">
                {% for tag in post.tags.all %}
                    {% partial tag-badge with tag=tag %}
                {% endfor %}
            </div>
            
            <div class="post-actions">
                {% partial button with text="Читать далее" class="btn-outline-primary" %}
                {% if user == post.author or user.is_staff %}
                    {% partial button with text="Редактировать" class="btn-outline-secondary" %}
                    {% partial button with text="Удалить" class="btn-outline-danger" %}
                {% endif %}
            </div>
        </footer>
    </article>
{% endpartialdef %}

{# Вспомогательные компоненты #}
{% partialdef user-avatar %}
    <img src="{{ user.profile.avatar.url|default:'/static/images/default-avatar.png' }}" 
         alt="{{ user.username }}" 
         class="avatar avatar-{{ size }}">
{% endpartialdef %}

{% partialdef tag-badge %}
    <span class="badge bg-secondary">
        <a href="{% url 'posts_by_tag' tag.slug %}" class="text-white text-decoration-none">
            {{ tag.name }}
        </a>
    </span>
{% endpartialdef %}
```

### 6. Пагинация

```django
{% partialdef pagination %}
    {% if page_obj.has_other_pages %}
        <nav aria-label="Page navigation">
            <ul class="pagination justify-content-center">
                {% if page_obj.has_previous %}
                    <li class="page-item">
                        <a class="page-link" href="?page={{ page_obj.previous_page_number }}">
                            Назад
                        </a>
                    </li>
                {% else %}
                    <li class="page-item disabled">
                        <span class="page-link">Назад</span>
                    </li>
                {% endif %}
                
                {% for num in page_obj.paginator.page_range %}
                    {% if page_obj.number == num %}
                        <li class="page-item active">
                            <span class="page-link">{{ num }}</span>
                        </li>
                    {% else %}
                        <li class="page-item">
                            <a class="page-link" href="?page={{ num }}">{{ num }}</a>
                        </li>
                    {% endif %}
                {% endfor %}
                
                {% if page_obj.has_next %}
                    <li class="page-item">
                        <a class="page-link" href="?page={{ page_obj.next_page_number }}">
                            Вперед
                        </a>
                    </li>
                {% else %}
                    <li class="page-item disabled">
                        <span class="page-link">Вперед</span>
                    </li>
                {% endif %}
            </ul>
        </nav>
    {% endif %}
{% endpartialdef %}
```

## Примеры для админ-панели

### 7. Карточка статистики

```django
{% partialdef stats-card %}
    <div class="card stats-card {{ color_class }}">
        <div class="card-body">
            <div class="d-flex align-items-center">
                <div class="stats-icon me-3">
                    {{ icon }}
                </div>
                <div class="stats-content">
                    <h5 class="stats-value">{{ value }}</h5>
                    <p class="stats-label mb-0">{{ label }}</p>
                    {% if change_percent %}
                        <small class="stats-change {{ change_percent|slice:'0:1' == '+'|yesno:'text-success,text-danger' }}">
                            {{ change_percent }} с прошлого месяца
                        </small>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
{% endpartialdef %}

{# Использование в дашборде #}
<div class="row">
    <div class="col-md-3">
        {% partial stats-card with 
            value=stats.total_users 
            label="Всего пользователей" 
            icon="👥" 
            change_percent="+12%" 
            color_class="bg-primary text-white" 
        %}
    </div>
    <div class="col-md-3">
        {% partial stats-card with 
            value=stats.total_posts 
            label="Всего постов" 
            icon="📝" 
            change_percent="+5%" 
            color_class="bg-success text-white" 
        %}
    </div>
    <div class="col-md-3">
        {% partial stats-card with 
            value=stats.total_comments 
            label="Всего комментариев" 
            icon="💬" 
            change_percent="-2%" 
            color_class="bg-warning text-dark" 
        %}
    </div>
    <div class="col-md-3">
        {% partial stats-card with 
            value=stats.active_users 
            label="Активных пользователей" 
            icon="🔥" 
            change_percent="+8%" 
            color_class="bg-info text-white" 
        %}
    </div>
</div>
```

## Примеры с условной логикой

### 8. Условное отображение

```django
{% partialdef conditional-content %}
    <div class="conditional-block">
        {% if condition == 'success' %}
            {% partial alert with 
                type="success" 
                title="Успех!" 
                message=message 
            %}
        {% elif condition == 'warning' %}
            {% partial alert with 
                type="warning" 
                title="Внимание!" 
                message=message 
            %}
        {% elif condition == 'error' %}
            {% partial alert with 
                type="danger" 
                title="Ошибка!" 
                message=message 
            %}
        {% else %}
            <div class="content">
                {{ default_content }}
            </div>
        {% endif %}
    </div>
{% endpartialdef %}

{# Компонент алерта #}
{% partialdef alert %}
    <div class="alert alert-{{ type }} alert-dismissible fade show" role="alert">
        <strong>{{ title }}</strong> {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
{% endpartialdef %}
```

## Советы по использованию

### 1. Организация компонентов

```django
{# base.html - основной шаблон с компонентами #}
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Мой сайт{% endblock %}</title>
</head>
<body>
    {# Определение всех компонентов в одном месте #}
    {% partialdef button %}{% endpartialdef %}
    {% partialdef card %}{% endpartialdef %}
    {% partialdef alert %}{% endpartialdef %}
    {% partialdef modal %}{% endpartialdef %}
    
    {# Основной контент #}
    {% block content %}{% endblock %}
</body>
</html>
```

### 2. Использование с наследованием

```django
{# child_template.html #}
{% extends "base.html" %}

{% block content %}
    <h1>Моя страница</h1>
    
    {# Использование компонентов из базового шаблона #}
    {% partial button with text="Действие" class="btn-primary" %}
    {% partial card with title="Карточка" content="Содержание" %}
{% endblock %}
```

### 3. Комбинирование с традиционными include

```django
{# Можно смешивать подходы #}
{% include "shared/header.html" %}

<main>
    {% partial user-profile with user=user %}
    {% partial post-list with posts=posts %}
</main>

{% include "shared/footer.html" %}
```

Эти примеры демонстрируют мощь Template Partials в Django 6 и показывают, как можно создавать переиспользуемые, модульные компоненты для любых нужд проекта.