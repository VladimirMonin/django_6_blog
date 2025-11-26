# Продвинутые техники HTMX + Django

## Out of Band Swaps (OOB)

### Базовый пример OOB

```html
<!-- Форма с обновлением нескольких элементов -->
<form hx-post="/update-profile/">
    {% csrf_token %}
    <input type="text" name="username" value="{{ user.username }}">
    <button type="submit">Обновить</button>
</form>

<!-- Элементы для обновления через OOB -->
<header id="user-header">
    Привет, {{ user.username }}!
</header>

<nav id="user-nav">
    <a href="/profile/">Профиль {{ user.username }}</a>
</nav>
```

### View с OOB

```python
# views.py
def update_profile(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        
        # Обновляем пользователя
        request.user.username = username
        request.user.save()
        
        # Возвращаем несколько обновлений через OOB
        return HttpResponse(f'''
            <div id="user-header" hx-swap-oob="true">
                Привет, {username}!
            </div>
            <div id="user-nav" hx-swap-oob="true">
                <a href="/profile/">Профиль {username}</a>
            </div>
            <div class="success-message">
                Профиль успешно обновлен!
            </div>
        ''')
```

### Динамическое OOB

```html
<!-- Динамическое обновление счетчиков -->
<div class="cart">
    <span id="cart-count">{{ cart.items.count }}</span> товаров
</div>

<button hx-post="/add-to-cart/{{ product.id }}/"
        hx-target="#cart-message"
        hx-swap="innerHTML">
    Добавить в корзину
</button>

<div id="cart-message"></div>
```

```python
# views.py
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = get_cart(request)
    cart.add_item(product)
    
    return HttpResponse(f'''
        <div id="cart-count" hx-swap-oob="true">
            {cart.items.count}
        </div>
        <div id="cart-message">
            Товар "{product.name}" добавлен в корзину!
        </div>
    ''')
```

## Polling и автообновление

### Простой polling

```html
<!-- Обновление статуса каждые 5 секунд -->
<div id="status-display" 
     hx-get="/task-status/{{ task.id }}/"
     hx-trigger="every 5s"
     hx-swap="innerHTML">
    Загрузка статуса...
</div>
```

### Условный polling

```html
<!-- Polling до завершения задачи -->
<div id="task-progress"
     hx-get="/task-progress/{{ task.id }}/"
     hx-trigger="every 2s"
     hx-swap="innerHTML"
     hx-on::after-request="checkTaskComplete(event)">
</div>

<script>
function checkTaskComplete(event) {
    const response = event.detail.xhr.responseText;
    if (response.includes('COMPLETED')) {
        // Останавливаем polling
        event.target.removeAttribute('hx-trigger');
    }
}
</script>
```

### View для polling

```python
# views.py
def task_progress(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    
    context = {
        'task': task,
        'progress': task.get_progress(),
        'status': task.status
    }
    
    return render(request, 'tasks/progress.html', context)
```

## WebSockets с HTMX

### Настройка Django Channels

```python
# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        
        # Отправляем HTML ответ для HTMX
        html_response = f'''
            <div id="messages" hx-swap-oob="beforeend">
                <div class="message">{message}</div>
            </div>
        '''
        
        await self.send(text_data=html_response)
```

### HTMX WebSocket extension

```html
<!-- Подключение WebSocket extension -->
<script src="https://unpkg.com/htmx.org@2.0.4/dist/ext/ws.js"></script>

<!-- Использование WebSocket -->
<div hx-ext="ws" ws-connect="/ws/chat/">
    <div id="messages">
        <!-- Сообщения будут добавляться сюда -->
    </div>
    
    <form ws-send>
        <input type="text" name="message" placeholder="Введите сообщение...">
        <button type="submit">Отправить</button>
    </form>
</div>
```

## Server-Sent Events (SSE)

### Настройка SSE в Django

```python
# views.py
from django.http import StreamingHttpResponse
import json
import time

def sse_updates(request):
    def event_stream():
        while True:
            # Генерируем события
            data = {
                'message': f'Update at {time.strftime("%H:%M:%S")}',
                'count': get_live_count()
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(5)  # Обновление каждые 5 секунд
    
    response = StreamingHttpResponse(
        event_stream(), 
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    return response
```

### HTMX SSE extension

```html
<!-- Подключение SSE extension -->
<script src="https://unpkg.com/htmx.org@2.0.4/dist/ext/sse.js"></script>

<!-- Использование SSE -->
<div hx-ext="sse" sse-connect="/sse/updates/" sse-swap="message">
    <div id="live-updates">
        <!-- Обновления будут появляться здесь -->
    </div>
</div>

<!-- Или с кастомной обработкой -->
<div hx-ext="sse" 
     sse-connect="/sse/updates/"
     hx-on:sse-message="handleUpdate(event)">
</div>

<script>
function handleUpdate(event) {
    const data = JSON.parse(event.detail.data);
    
    // Обновляем UI
    document.getElementById('counter').textContent = data.count;
    
    // Показываем уведомление
    showNotification(data.message);
}
</script>
```

## Оптимистичный UI

### Оптимистичные обновления

```html
<!-- Лайк с оптимистичным обновлением -->
<button class="like-btn" 
        data-likes="{{ post.likes }}"
        data-post-id="{{ post.id }}"
        onclick="optimisticLike(this)"
        hx-post="/like/{{ post.id }}/"
        hx-target="this"
        hx-swap="outerHTML">
    ❤️ {{ post.likes }}
</button>

<script>
function optimisticLike(button) {
    const currentLikes = parseInt(button.getAttribute('data-likes'));
    const newLikes = currentLikes + 1;
    
    // Немедленное обновление UI
    button.innerHTML = `❤️ ${newLikes}`;
    button.setAttribute('data-likes', newLikes);
    
    // Отправка запроса на сервер
    htmx.ajax('POST', `/like/${button.getAttribute('data-post-id')}/`, {
        target: button,
        swap: 'outerHTML'
    });
}
</script>
```

### Откат при ошибке

```html
<!-- Оптимистичное обновление с откатом -->
<button class="follow-btn"
        data-user-id="{{ user.id }}"
        data-following="{{ is_following }}"
        onclick="toggleFollow(this)"
        hx-post="/follow/{{ user.id }}/"
        hx-target="this"
        hx-swap="outerHTML"
        hx-on::htmx:after-request="handleFollowResponse(event)">
    {% if is_following %}Отписаться{% else %}Подписаться{% endif %}
</button>

<script>
let originalState = {};

function toggleFollow(button) {
    // Сохраняем оригинальное состояние
    originalState[button.getAttribute('data-user-id')] = {
        text: button.textContent,
        following: button.getAttribute('data-following')
    };
    
    // Оптимистичное обновление
    const isFollowing = button.getAttribute('data-following') === 'true';
    button.textContent = isFollowing ? 'Подписаться' : 'Отписаться';
    button.setAttribute('data-following', (!isFollowing).toString());
}

function handleFollowResponse(event) {
    if (event.detail.xhr.status >= 400) {
        // Откат при ошибке
        const button = event.detail.elt;
        const userId = button.getAttribute('data-user-id');
        const original = originalState[userId];
        
        if (original) {
            button.textContent = original.text;
            button.setAttribute('data-following', original.following);
        }
        
        showError('Не удалось выполнить действие');
    }
}
</script>
```

## История браузера и навигация

### Push URL

```html
<!-- Обновление URL при навигации -->
<div hx-get="/page/2/" 
     hx-push-url="true"
     hx-target="#content"
     hx-swap="innerHTML">
    Следующая страница
</div>
```

### История с сохранением состояния

```html
<!-- Навигация с сохранением состояния -->
<div class="pagination">
    {% for page in pages %}
        <button hx-get="{% url 'paginated_list' %}?page={{ page }}"
                hx-push-url="true"
                hx-target="#items-list"
                hx-swap="innerHTML"
                {% if page == current_page %}class="active"{% endif %}>
            {{ page }}
        </button>
    {% endfor %}
</div>
```

### Обработка back/forward

```javascript
// Обработка навигации браузера
window.addEventListener('popstate', function(event) {
    // Загружаем контент для текущего URL
    const url = window.location.pathname + window.location.search;
    htmx.ajax('GET', url, {
        target: '#main-content',
        swap: 'innerHTML'
    });
});
```

## Расширения HTMX

### Подключение расширений

```html
<!-- Подключение нескольких расширений -->
<script src="https://unpkg.com/htmx.org@2.0.4/dist/ext/ws.js"></script>
<script src="https://unpkg.com/htmx.org@2.0.4/dist/ext/sse.js"></script>
<script src="https://unpkg.com/htmx.org@2.0.4/dist/ext/debug.js"></script>

<!-- Использование расширений -->
<div hx-ext="ws,sse,debug">
    <!-- Контент с расширениями -->
</div>
```

### Кастомные расширения

```javascript
// custom-extension.js
htmx.defineExtension('my-extension', {
    onEvent: function(name, evt) {
        if (name === 'htmx:beforeRequest') {
            // Кастомная логика перед запросом
            console.log('Custom extension: before request', evt.detail);
        }
    }
});
```

```html
<!-- Использование кастомного расширения -->
<script src="/static/js/custom-extension.js"></script>

<div hx-ext="my-extension">
    <button hx-post="/action/">Действие</button>
</div>
```

## Интеграция с Django 6 features

### Async views

```python
# views.py
from asgiref.sync import sync_to_async
from django.shortcuts import render

async def async_htmx_view(request):
    if request.htmx:
        # Асинхронные операции
        items = await sync_to_async(list)(Item.objects.all()[:10])
        return render(request, 'partials/async_items.html', {
            'items': items
        })
    
    return render(request, 'full_page.html')
```

### Template improvements

```html
<!-- Использование новых возможностей шаблонов Django 6 -->
{% with items|slice:":5" as first_five %}
    <div hx-get="{% url 'load_more' %}" 
         hx-trigger="revealed"
         hx-target="this"
         hx-swap="afterend">
        
        {% for item in first_five %}
            <div class="item">{{ item.name }}</div>
        {% endfor %}
    </div>
{% endwith %}
```

### Performance optimizations

```python
# views.py
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

@vary_on_headers('HX-Request')
@cache_page(60 * 5)  # 5 минут кэша
def cached_htmx_view(request):
    if request.htmx:
        return render(request, 'partials/cached_content.html')
    return render(request, 'full_page.html')
```

## Мониторинг и аналитика

### Трекинг HTMX событий

```javascript
// Отслеживание HTMX событий для аналитики
document.body.addEventListener('htmx:afterRequest', function(event) {
    const detail = event.detail;
    
    // Отправка в аналитику
    if (typeof gtag !== 'undefined') {
        gtag('event', 'htmx_request', {
            'url': detail.pathInfo.requestPath,
            'method': detail.pathInfo.requestMethod,
            'status': detail.xhr.status
        });
    }
});
```

### Performance monitoring

```python
# middleware.py
import time
from django.utils.deprecation import MiddlewareMixin

class HTMXPerformanceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.htmx:
            request._htmx_start_time = time.time()
    
    def process_response(self, request, response):
        if hasattr(request, '_htmx_start_time'):
            duration = time.time() - request._htmx_start_time
            
            # Логирование производительности
            print(f'HTMX request took {duration:.3f}s: {request.path}')
            
            # Добавление в заголовки для мониторинга
            response['X-HTMX-Duration'] = f'{duration:.3f}'
        
        return response
```