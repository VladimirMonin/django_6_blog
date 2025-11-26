# Практические примеры HTMX + Django

## Пример 1: Click to Load (Загрузка по клику)

### Template
```html
<!-- main_template.html -->
<div class="container">
    <h2>Список элементов</h2>
    <div id="items-list">
        {% for item in initial_items %}
            <div class="item">{{ item.name }}</div>
        {% endfor %}
    </div>
    
    <button hx-get="{% url 'load_more' %}" 
            hx-target="#items-list" 
            hx-swap="beforeend"
            hx-indicator="#loading">
        Загрузить еще
    </button>
    
    <div id="loading" class="htmx-indicator">
        Загрузка...
    </div>
</div>
```

### View
```python
# views.py
from django.shortcuts import render
from django.core.paginator import Paginator

def item_list(request):
    items = Item.objects.all()[:5]  # Первые 5 элементов
    return render(request, 'items/list.html', {'initial_items': items})

def load_more(request):
    page = int(request.GET.get('page', 2))
    items = Item.objects.all()
    paginator = Paginator(items, 5)
    page_obj = paginator.get_page(page)
    
    return render(request, 'items/partial_list.html', {
        'items': page_obj,
        'next_page': page + 1 if page_obj.has_next() else None
    })
```

### Partial Template
```html
<!-- items/partial_list.html -->
{% for item in items %}
    <div class="item">
        <h3>{{ item.name }}</h3>
        <p>{{ item.description }}</p>
    </div>
{% endfor %}

{% if next_page %}
    <button hx-get="{% url 'load_more' %}?page={{ next_page }}" 
            hx-target="#items-list" 
            hx-swap="beforeend"
            hx-indicator="#loading">
        Загрузить еще
    </button>
{% endif %}
```

## Пример 2: Search as you type (Поиск в реальном времени)

### Template
```html
<!-- search.html -->
<div class="search-container">
    <input type="text" 
           name="q" 
           placeholder="Поиск товаров..."
           hx-get="{% url 'search' %}"
           hx-trigger="keyup changed delay:500ms"
           hx-target="#search-results"
           hx-indicator="#search-loading">
    
    <div id="search-loading" class="htmx-indicator">
        Поиск...
    </div>
    
    <div id="search-results">
        <!-- Результаты появятся здесь -->
    </div>
</div>
```

### View
```python
# views.py
from django.db.models import Q

def search(request):
    query = request.GET.get('q', '').strip()
    
    if not query:
        return render(request, 'search/empty.html')
    
    results = Item.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    )[:10]
    
    return render(request, 'search/results.html', {
        'results': results,
        'query': query
    })
```

### Partial Templates
```html
<!-- search/results.html -->
{% if results %}
    <div class="search-results">
        <h4>Найдено {{ results|length }} результатов по запросу "{{ query }}"</h4>
        {% for item in results %}
            <div class="search-item">
                <h5>{{ item.name }}</h5>
                <p>{{ item.description|truncatewords:20 }}</p>
            </div>
        {% endfor %}
    </div>
{% else %}
    <div class="no-results">
        <p>По запросу "{{ query }}" ничего не найдено</p>
    </div>
{% endif %}

<!-- search/empty.html -->
<div class="search-empty">
    <p>Введите поисковый запрос</p>
</div>
```

## Пример 3: Inline Editing (Редактирование на месте)

### Template
```html
<!-- item_detail.html -->
<div class="item-detail">
    <div id="item-{{ item.id }}">
        <h2>{{ item.name }}</h2>
        <p>{{ item.description }}</p>
        <button hx-get="{% url 'edit_item' item.id %}"
                hx-target="#item-{{ item.id }}">
            Редактировать
        </button>
    </div>
</div>
```

### View
```python
# views.py
from django.shortcuts import get_object_or_404

def item_detail(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    return render(request, 'items/detail.html', {'item': item})

def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return render(request, 'items/display.html', {'item': item})
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'items/edit_form.html', {
        'form': form, 
        'item': item
    })
```

### Partial Templates
```html
<!-- items/edit_form.html -->
<form hx-post="{% url 'edit_item' item.id %}"
      hx-target="#item-{{ item.id }}">
    {% csrf_token %}
    
    <div class="form-group">
        {{ form.name.label_tag }}
        {{ form.name }}
        {{ form.name.errors }}
    </div>
    
    <div class="form-group">
        {{ form.description.label_tag }}
        {{ form.description }}
        {{ form.description.errors }}
    </div>
    
    <button type="submit">Сохранить</button>
    <button type="button" 
            hx-get="{% url 'item_detail' item.id %}"
            hx-target="#item-{{ item.id }}">
        Отмена
    </button>
</form>

<!-- items/display.html -->
<h2>{{ item.name }}</h2>
<p>{{ item.description }}</p>
<button hx-get="{% url 'edit_item' item.id %}"
        hx-target="#item-{{ item.id }}">
    Редактировать
</button>
```

## Пример 4: Form Validation (Валидация формы)

### Template
```html
<!-- contact_form.html -->
<form hx-post="{% url 'contact' %}"
      hx-target="#form-result"
      hx-indicator="#form-loading">
    {% csrf_token %}
    
    <div class="form-group">
        <label for="id_name">Имя:</label>
        <input type="text" 
               name="name" 
               id="id_name"
               required
               hx-post="{% url 'validate_field' 'name' %}"
               hx-trigger="keyup changed delay:500ms"
               hx-target="#name-error">
        <div id="name-error"></div>
    </div>
    
    <div class="form-group">
        <label for="id_email">Email:</label>
        <input type="email" 
               name="email" 
               id="id_email"
               required
               hx-post="{% url 'validate_field' 'email' %}"
               hx-trigger="keyup changed delay:500ms"
               hx-target="#email-error">
        <div id="email-error"></div>
    </div>
    
    <div class="form-group">
        <label for="id_message">Сообщение:</label>
        <textarea name="message" id="id_message" required></textarea>
    </div>
    
    <button type="submit">Отправить</button>
    
    <div id="form-loading" class="htmx-indicator">
        Отправка...
    </div>
</form>

<div id="form-result"></div>
```

### Views
```python
# views.py
from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Обработка формы
            return render(request, 'contact/success.html')
        else:
            return render(request, 'contact/form_with_errors.html', {
                'form': form
            })
    else:
        form = ContactForm()
    
    return render(request, 'contact/form.html', {'form': form})

def validate_field(request, field_name):
    form = ContactForm(request.POST)
    
    if form.is_valid():
        return HttpResponse('<span class="text-success">✓</span>')
    else:
        errors = form.errors.get(field_name, [])
        if errors:
            return HttpResponse(f'<span class="text-danger">{errors[0]}</span>')
        return HttpResponse('')
```

## Пример 5: Infinite Scroll (Бесконечный скролл)

### Template
```html
<!-- infinite_scroll.html -->
<div id="posts-container">
    {% for post in posts %}
        <div class="post">
            <h3>{{ post.title }}</h3>
            <p>{{ post.content|truncatewords:50 }}</p>
        </div>
    {% endfor %}
</div>

<!-- Триггер для загрузки следующей страницы -->
<div hx-get="{% url 'load_posts' %}?page=2"
     hx-trigger="revealed"
     hx-swap="beforeend"
     hx-target="#posts-container"
     hx-indicator="#loading-more">
</div>

<div id="loading-more" class="htmx-indicator">
    Загрузка следующих постов...
</div>
```

### View
```python
# views.py
from django.core.paginator import Paginator

def post_list(request):
    posts = Post.objects.all()[:10]  # Первые 10 постов
    return render(request, 'posts/list.html', {'posts': posts})

def load_posts(request):
    page = int(request.GET.get('page', 1))
    posts = Post.objects.all()
    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(page)
    
    if page_obj.has_next():
        next_page = page + 1
        # Добавляем следующий триггер
        return render(request, 'posts/partial_list.html', {
            'posts': page_obj,
            'next_page': next_page
        })
    else:
        # Последняя страница
        return render(request, 'posts/partial_list.html', {
            'posts': page_obj,
            'next_page': None
        })
```

### Partial Template
```html
<!-- posts/partial_list.html -->
{% for post in posts %}
    <div class="post">
        <h3>{{ post.title }}</h3>
        <p>{{ post.content|truncatewords:50 }}</p>
    </div>
{% endfor %}

{% if next_page %}
    <div hx-get="{% url 'load_posts' %}?page={{ next_page }}"
         hx-trigger="revealed"
         hx-swap="beforeend"
         hx-target="#posts-container"
         hx-indicator="#loading-more">
    </div>
{% else %}
    <div class="end-of-posts">
        <p>Вы достигли конца списка</p>
    </div>
{% endif %}
```

## Пример 6: Tabs (Вкладки)

### Template
```html
<!-- tabs.html -->
<div class="tabs">
    <div class="tab-headers">
        <button hx-get="{% url 'tab_content' 'info' %}"
                hx-target="#tab-content"
                class="tab-header active">
            Информация
        </button>
        <button hx-get="{% url 'tab_content' 'settings' %}"
                hx-target="#tab-content"
                class="tab-header">
            Настройки
        </button>
        <button hx-get="{% url 'tab_content' 'history' %}"
                hx-target="#tab-content"
                class="tab-header">
            История
        </button>
    </div>
    
    <div id="tab-content" class="tab-content">
        <!-- Контент вкладок будет загружаться сюда -->
    </div>
</div>

<script>
    // Активация вкладок при загрузке
    document.addEventListener('DOMContentLoaded', function() {
        // Загружаем первую вкладку
        htmx.trigger('button.tab-header:first-child', 'click');
    });
    
    // Обновление активного класса
    document.body.addEventListener('htmx:afterSwap', function(event) {
        const target = event.detail.target;
        if (target.id === 'tab-content') {
            // Убираем активный класс со всех вкладок
            document.querySelectorAll('.tab-header').forEach(btn => {
                btn.classList.remove('active');
            });
            // Добавляем активный класс к нажатой вкладке
            event.detail.elt.closest('.tab-header').classList.add('active');
        }
    });
</script>
```

### View
```python
# views.py
def tab_content(request, tab_name):
    templates = {
        'info': 'tabs/info.html',
        'settings': 'tabs/settings.html', 
        'history': 'tabs/history.html'
    }
    
    template_name = templates.get(tab_name, 'tabs/not_found.html')
    
    context = {
        'tab_name': tab_name,
        'data': get_tab_data(tab_name)  # Ваша логика получения данных
    }
    
    return render(request, template_name, context)
```

## Пример 7: Modal (Модальное окно)

### Template
```html
<!-- modal_trigger.html -->
<button hx-get="{% url 'modal_content' %}"
        hx-target="#modal-container"
        hx-swap="innerHTML">
    Открыть модальное окно
</button>

<!-- Контейнер для модального окна -->
<div id="modal-container"></div>
```

### View
```python
# views.py
def modal_content(request):
    return render(request, 'modal/content.html')

def modal_action(request):
    if request.method == 'POST':
        # Обработка действия
        return HttpResponse('<script>window.location.reload()</script>')
    return HttpResponse('')
```

### Modal Template
```html
<!-- modal/content.html -->
<div class="modal-overlay" id="modal-overlay">
    <div class="modal">
        <div class="modal-header">
            <h3>Модальное окно</h3>
            <button onclick="closeModal()">×</button>
        </div>
        
        <div class="modal-body">
            <p>Содержимое модального окна</p>
            
            <form hx-post="{% url 'modal