# Безопасность и Best Practices HTMX + Django

## CSRF защита

### Основной подход

```html
<!-- Добавление CSRF токена в HTMX запросы -->
<meta name="csrf-token" content="{{ csrf_token }}">

<script>
    document.body.addEventListener('htmx:configRequest', function(event) {
        event.detail.headers['X-CSRFToken'] = 
            document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    });
</script>
```

### Альтернативные подходы

```html
<!-- Использование hx-headers -->
<form hx-post="/submit/" 
      hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
    <!-- форма -->
</form>

<!-- Включение CSRF токена в форму -->
<form hx-post="/submit/">
    {% csrf_token %}
    <!-- остальные поля -->
</form>
```

### Настройка Django для HTMX

```python
# settings.py
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_HTTPONLY = False  # Для доступа через JavaScript
```

## XSS защита

### Автоматическое экранирование Django

Django автоматически экранирует все переменные в шаблонах:

```html
<!-- Безопасно - Django экранирует HTML -->
<div>{{ user_input }}</div>

<!-- Опасно - отключает экранирование -->
<div>{{ user_input|safe }}</div>

<!-- Опасно - отключает экранирование -->
<div>{% autoescape off %}{{ user_input }}{% endautoescape %}</div>
```

### Безопасная обработка пользовательского контента

```python
# views.py
from django.utils.html import escape

def safe_view(request):
    user_input = escape(request.POST.get('input', ''))
    return render(request, 'template.html', {'input': user_input})
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.htmx:
            context['is_htmx'] = True
        return context

class ItemListView(HTMXViewMixin, ListView):
    model = Item
    template_name = 'item_list.html'
```

### Структура templates

```
templates/
├── base.html
├── partials/
│   ├── _item_list.html
│   ├── _search_results.html
│   ├── _form.html
│   └── _success.html
├── full_pages/
│   ├── item_list.html
│   └── item_detail.html
└── components/
    ├── search.html
    └── modal.html
```

### Error handling

```python
# views.py
from django.http import HttpResponseBadRequest

def htmx_view(request):
    try:
        if not request.htmx:
            return HttpResponseBadRequest("HTMX request required")
        
        # Логика view
        return render(request, 'partials/success.html')
        
    except Exception as e:
        if request.htmx:
            return render(request, 'partials/error.html', {
                'error': str(e)
            })
        raise
```

### Partial templates должны быть самодостаточными

```html
<!-- partials/item_list.html -->
{% for item in items %}
    <div class="item" id="item-{{ item.id }}">
        <h3>{{ item.name }}</h3>
        <p>{{ item.description }}</p>
        <button hx-get="{% url 'edit_item' item.id %}"
                hx-target="#item-{{ item.id }}">
            Редактировать
        </button>
    </div>
{% endfor %}
```

## Производительность

### Оптимизация responses

```python
# views.py
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 минут кэша
def cached_view(request):
    items = Item.objects.all()[:10]
    return render(request, 'partials/items.html', {'items': items})
```

### Минимизация размера ответов

```python
# views.py
def optimized_view(request):
    """Возвращает минимальный HTML для HTMX"""
    if request.htmx:
        # Только необходимый контент
        return render(request, 'partials/minimal.html')
    # Полная страница для обычных запросов
    return render(request, 'full_page.html')
```

### Ленивая загрузка

```html
<!-- Ленивая загрузка контента -->
<div hx-get="/heavy-content/" 
     hx-trigger="revealed"
     hx-swap="innerHTML">
    Загрузка...
</div>
```

## UX паттерны

### Loading states

```html
<!-- Индикатор загрузки -->
<button hx-post="/submit/" 
        hx-target="#result"
        hx-indicator="#loading">
    Отправить
</button>

<div id="loading" class="htmx-indicator">
    <div class="spinner"></div>
    Загрузка...
</div>

<style>
.htmx-indicator {
    opacity: 0;
    transition: opacity 200ms ease-in;
}
.htmx-request .htmx-indicator {
    opacity: 1;
}
.htmx-request.htmx-indicator {
    opacity: 1;
}
</style>
```

### Error handling в UI

```html
<!-- Обработка ошибок на клиенте -->
<form hx-post="/submit/" 
      hx-target="#result"
      hx-on::htmx:after-request="handleResponse(event)">
    {% csrf_token %}
    <!-- поля формы -->
</form>

<script>
function handleResponse(event) {
    if (event.detail.xhr.status >= 400) {
        // Показать ошибку
        showError('Произошла ошибка при отправке формы');
    }
}
</script>
```

### Оптимистичные обновления

```html
<!-- Оптимистичное обновление UI -->
<button hx-post="/like/{{ post.id }}/"
        hx-target="this"
        hx-swap="outerHTML"
        onclick="optimisticLike(this)">
    ❤️ {{ post.likes_count }}
</button>

<script>
function optimisticLike(button) {
    const currentCount = parseInt(button.textContent.match(/\d+/)[0]);
    button.innerHTML = `❤️ ${currentCount + 1}`;
}
</script>
```

## Тестирование

### Тестирование HTMX views

```python
# tests.py
from django.test import TestCase
from django.urls import reverse

class HTMXTestCase(TestCase):
    def test_htmx_request(self):
        """Тестирование HTMX запросов"""
        response = self.client.get(
            reverse('htmx_view'),
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/view.html')
    
    def test_non_htmx_request(self):
        """Тестирование обычных запросов"""
        response = self.client.get(reverse('htmx_view'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'full_page.html')
```

### Тестирование CSRF защиты

```python
# tests.py
class CSRFTestCase(TestCase):
    def test_csrf_protection(self):
        """Тестирование CSRF защиты"""
        response = self.client.post(
            reverse('protected_view'),
            {'data': 'test'},
            HTTP_HX_REQUEST='true'
        )
        
        # Должен вернуть 403 без CSRF токена
        self.assertEqual(response.status_code, 403)
```

## Мониторинг и отладка

### Включение отладки HTMX

```javascript
// Включение подробного логирования
htmx.logAll();

// Отслеживание событий HTMX
document.body.addEventListener('htmx:beforeRequest', function(evt) {
    console.log('Before request:', evt.detail);
});

document.body.addEventListener('htmx:afterRequest', function(evt) {
    console.log('After request:', evt.detail);
});
```

### Мониторинг производительности

```python
# middleware.py
import time
from django.utils.deprecation import MiddlewareMixin

class HTMXPerformanceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.htmx:
            request.htmx_start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, 'htmx_start_time'):
            duration = time.time() - request.htmx_start_time
            response['X-HTMX-Response-Time'] = f'{duration:.3f}s'
        return response
```

## Развертывание

### Настройки для production

```python
# settings.py
# Для production отключаем отладку
DEBUG = False

# Настройки безопасности
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Настройки CSRF
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
```

### CDN для HTMX

```html
<!-- Production CDN -->
<script src="https://unpkg.com/htmx.org@2.0.4"></script>

<!-- С fallback на локальную версию -->
<script>
window.htmx || document.write('<script src="/static/js/htmx.min.js"><\/script>')
</script>
```

## Common Pitfalls (Частые ошибки)

### 1. Забыли CSRF токен
```html
<!-- Неправильно -->
<form hx-post="/submit/">
    <!-- нет CSRF токена -->
</form>

<!-- Правильно -->
<form hx-post="/submit/">
    {% csrf_token %}
</form>
```

### 2. Неправильный target
```html
<!-- Неправильно - элемент не существует -->
<button hx-get="/data/" hx-target="#nonexistent">Загрузить</button>

<!-- Правильно - проверьте существование элемента -->
<div id="results"></div>
<button hx-get="/data/" hx-target="#results">Загрузить</button>
```

### 3. Проблемы с partial templates
```html
<!-- Неправильно - зависит от внешнего контекста -->
<div>{{ undefined_variable }}</div>

<!-- Правильно - самодостаточный partial -->
{% if items %}
    {% for item in items %}
        <div>{{ item.name }}</div>
    {% endfor %}
{% else %}
    <div>Нет данных</div>
{% endif %}
```

### 4. Бесконечные циклы
```html
<!-- Опасно - может создать бесконечный цикл -->
<div hx-get="/poll/" hx-trigger="every 1s" hx-target="this"></div>

<!-- Безопасно - ограничение по времени или условию -->
<div hx-get="/poll/" 
     hx-trigger="every 1s" 
     hx-target="this"
     hx-on::after-request="checkStopCondition(event)">
</div>
```