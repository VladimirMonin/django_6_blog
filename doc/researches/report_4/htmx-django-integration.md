# HTMX в Django 6: Полное руководство по интеграции

## Введение в HTMX

HTMX (Hypermedia as the Engine of Application State) - это библиотека, которая позволяет создавать современные интерактивные веб-приложения без написания большого количества JavaScript. Основная философия HTMX - использование гипермедиа как движка состояния приложения.

### Основные преимущества HTMX

- **Минимальный JavaScript**: Использует HTML-атрибуты для AJAX-запросов
- **Простота интеграции**: Легко интегрируется с существующими Django проектами
- **Частичное обновление**: Обновляет только нужные части страницы
- **Совместимость**: Работает с любым бэкендом, включая Django

## Установка и настройка

### Установка HTMX

HTMX можно подключить через CDN или установить локально:

```html
<!-- CDN вариант -->
<script src="https://unpkg.com/htmx.org@2.0.4"></script>

<!-- Локальная установка -->
<script src="{% static 'js/htmx.min.js' %}"></script>
```

### Установка django-htmx

```bash
pip install django-htmx
```

### Настройка Django

Добавьте в `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'django_htmx',
]

MIDDLEWARE = [
    # ...
    'django_htmx.middleware.HtmxMiddleware',
]
```

## Core концепции HTMX

### Основные атрибуты

- **hx-get**: GET запрос
- **hx-post**: POST запрос  
- **hx-put**: PUT запрос
- **hx-patch**: PATCH запрос
- **hx-delete**: DELETE запрос
- **hx-target**: Целевой элемент для обновления
- **hx-swap**: Способ замены контента
- **hx-trigger**: Триггер события

### Примеры использования

```html
<!-- Загрузка контента по клику -->
<button hx-get="/api/data/" hx-target="#result">
    Загрузить данные
</button>
<div id="result"></div>

<!-- Форма с AJAX отправкой -->
<form hx-post="/submit/" hx-target="#form-result">
    {% csrf_token %}
    <input type="text" name="name">
    <button type="submit">Отправить</button>
</form>
<div id="form-result"></div>
```

## Django-HTMX библиотека

### Middleware

Middleware `django_htmx.middleware.HtmxMiddleware` добавляет объект `request.htmx`:

```python
def my_view(request):
    if request.htmx:
        # HTMX запрос
        return render(request, 'partial.html')
    else:
        # Обычный запрос
        return render(request, 'full_page.html')
```

### Вспомогательные функции

```python
from django_htmx.http import HttpResponseClientRedirect

# Редирект для HTMX
return HttpResponseClientRedirect('/success/')
```

## Практические примеры

### Пример 1: Click to Load

**Template:**
```html
<button hx-get="/load-more/" hx-target="#content" hx-swap="beforeend">
    Загрузить еще
</button>
<div id="content">
    <!-- Контент будет добавляться сюда -->
</div>
```

**View:**
```python
def load_more(request):
    items = Item.objects.all()[:10]
    return render(request, 'partials/items.html', {'items': items})
```

### Пример 2: Search as you type

**Template:**
```html
<input type="text" 
       hx-get="/search/" 
       hx-trigger="keyup changed delay:500ms"
       hx-target="#results"
       name="q"
       placeholder="Поиск...">
<div id="results"></div>
```

**View:**
```python
def search(request):
    query = request.GET.get('q', '')
    if query:
        results = Item.objects.filter(name__icontains=query)
    else:
        results = []
    return render(request, 'partials/search_results.html', {'results': results})
```

### Пример 3: Inline Editing

**Template:**
```html
<div hx-get="/edit/{{ item.id }}/" hx-trigger="click">
    {{ item.name }}
</div>
```

**View:**
```python
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return render(request, 'partials/item_display.html', {'item': item})
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'partials/item_form.html', {'form': form, 'item': item})
```

### Пример 4: Form Validation

**Template:**
```html
<form hx-post="/validate-form/" hx-target="#form-result">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Отправить</button>
</form>
<div id="form-result"></div>
```

**View:**
```python
def validate_form(request):
    if request.method == 'POST':
        form = MyForm(request.POST)
        if form.is_valid():
            # Обработка валидной формы
            return render(request, 'partials/success.html')
        else:
            # Возврат формы с ошибками
            return render(request, 'partials/form_with_errors.html', {'form': form})
```

### Пример 5: Infinite Scroll

**Template:**
```html
<div id="items-container">
    {% for item in items %}
        <div class="item">{{ item.name }}</div>
    {% endfor %}
</div>
<div hx-get="/load-more/?page=2" 
     hx-trigger="revealed" 
     hx-swap="beforeend"
     hx-target="#items-container">
</div>
```

## Формы и валидация

### Django Forms + HTMX

```python
# views.py
class ContactView(FormView):
    form_class = ContactForm
    template_name = 'contact.html'
    
    def form_valid(self, form):
        if self.request.htmx:
            # HTMX запрос - возвращаем только форму
            return self.render_to_response(
                self.get_context_data(form=form, success=True)
            )
        return super().form_valid(form)
    
    def form_invalid(self, form):
        if self.request.htmx:
            # HTMX запрос - возвращаем форму с ошибками
            return self.render_to_response(
                self.get_context_data(form=form)
            )
        return super().form_invalid(form)
```

### Инлайн валидация

```html
<input type="email" 
       name="email"
       hx-post="/validate-email/"
       hx-trigger="keyup changed delay:500ms"
       hx-target="#email-error">
<div id="email-error"></div>
```

## Продвинутые техники

### Out of Band Swaps (OOB)

```html
<!-- Отправка формы с обновлением нескольких элементов -->
<form hx-post="/update/">
    {% csrf_token %}
    <input type="text" name="name">
    <button type="submit">Обновить</button>
</form>

<!-- Элементы для обновления -->
<div id="header">Старый заголовок</div>
<div id="sidebar">Старая боковая панель</div>
```

**View:**
```python
def update_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        return HttpResponse(f'''
            <div id="header" hx-swap-oob="true">Новый заголовок: {name}</div>
            <div id="sidebar" hx-swap-oob="true">Обновленная боковая панель</div>
            <div>Основной контент</div>
        ''')
```

### Polling и автообновление

```html
<div hx-get="/status/" 
     hx-trigger="every 5s"
     hx-target="this">
    Загрузка статуса...
</div>
```

### WebSockets и SSE

```html
<!-- WebSocket соединение -->
<div hx-ext="ws" ws-connect="/ws/chat/">
    <div id="chat-messages"></div>
    <form ws-send>
        <input type="text" name="message">
        <button type="submit">Отправить</button>
    </form>
</div>
```

## Интеграция с Django 6

### Использование новых features

Django 6 привносит улучшения в шаблоны и производительность, которые хорошо сочетаются с HTMX:

```python
# Использование async views
async def async_data_view(request):
    data = await sync_to_async(Item.objects.all)()
    return render(request, 'partials/data.html', {'data': data})
```

### Django Components + HTMX

```python
# components.py
from django_components import component

@component.register("search_form")
class SearchForm(component.Component):
    template_name = "components/search_form.html"
    
    def get_context_data(self, *args, **kwargs):
        return {"placeholder": "Поиск..."}
```

```html
<!-- Использование компонента с HTMX -->
{% component "search_form" %}
    <input type="text" 
           hx-get="/search/" 
           hx-trigger="keyup changed delay:500ms"
           hx-target="#results">
{% endcomponent %}
```

## Best Practices

### Организация views

```python
# views.py
class HTMXViewMixin:
    """Mixin для обработки HTMX запросов"""
    
    def get_template_names(self):
        if self.request.htmx:
            return [f'partials/{self.template_name}']
        return [self.template_name]

class ItemListView(HTMXViewMixin, ListView):
    model = Item
    template_name = 'item_list.html'
```

### Организация templates

```
templates/
├── base.html
├── partials/
│   ├── _item_list.html
│   ├── _search_results.html
│   ├── _form.html
│   └── _success.html
└── full_pages/
    ├── item_list.html
    └── item_detail.html
```

### Error handling

```python
def htmx_view(request):
    try:
        # Логика view
        return render(request, 'partials/success.html')
    except Exception as e:
        if request.htmx:
            return render(request, 'partials/error.html', {'error': str(e)})
        raise
```

## Безопасность

### CSRF защита

```html
<!-- Добавление CSRF токена в HTMX запросы -->
<meta name="csrf-token" content="{{ csrf_token }}">

<script>
    document.body.addEventListener('htmx:configRequest', function(event) {
        event.detail.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    });
</script>
```

### Альтернативный подход

```html
<form hx-post="/submit/" hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    <!-- форма -->
</form>
```

## Производительность

### Оптимизация responses

```python
def optimized_view(request):
    """Оптимизированный view для HTMX"""
    if request.htmx:
        # Возвращаем минимальный HTML
        return render(request, 'partials/minimal.html')
    # Полная страница
    return render(request, 'full_page.html')
```

### Кэширование

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 минут
def cached_view(request):
    return render(request, 'partials/cached_content.html')
```

## Troubleshooting

### Частые проблемы

1. **CSRF ошибки**: Убедитесь, что CSRF токен передается в HTMX запросах
2. **Неправильный target**: Проверьте ID элементов в hx-target
3. **Ошибки в partial templates**: Убедитесь, что partial templates самодостаточны
4. **Проблемы с событиями**: Используйте hx-trigger для настройки триггеров

### Отладка

```javascript
// Включение отладки HTMX
htmx.logAll();
```

## Источники и ресурсы

- [Официальная документация HTMX](https://htmx.org/docs/)
- [Django-HTMX документация](https://django-htmx.readthedocs.io/)
- [Django-HTMX Patterns](https://github.com/spookylukey/django-htmx-patterns)
- [TestDriven.io Django + HTMX](https://testdriven.io/courses/django-htmx/)

---

*Исследование завершено 26 ноября 2025*