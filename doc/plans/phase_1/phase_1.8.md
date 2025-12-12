# Фаза 1.8: Интеграция HTMX для динамических взаимодействий

## Цель

Внедрить HTMX для создания динамического, отзывчивого пользовательского интерфейса без перезагрузки страниц, сохраняя при этом философию SSR.

## Контекст

HTMX позволяет создавать современные интерактивные веб-приложения, используя HTML-атрибуты вместо написания JavaScript. Это даст нам ощущение SPA при сохранении простоты серверного рендеринга.

**Философия:** Используем HTMX там, где это улучшает UX, а не везде. Базовая навигация остается классической (для SEO и простоты).

**Где применяем HTMX:**

- ✅ Подгрузка постов (infinite scroll или "Загрузить еще")
- ✅ Поиск в реальном времени
- ✅ Фильтрация и сортировка без перезагрузки
- ✅ Лайки, закладки, комментарии (в будущем)
- ❌ Основная навигация (остается обычными ссылками)
- ❌ Первичная загрузка контента

## Задачи

### 1. Установка и базовая настройка

- [ ] Установить django-htmx через Poetry:

  ```bash
  poetry add django-htmx
  ```

- [ ] Добавить в `INSTALLED_APPS` в settings.py
- [ ] Добавить `HtmxMiddleware` в `MIDDLEWARE`
- [ ] Подключить HTMX через CDN в `base.html`:

  ```html
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
  ```

- [ ] Добавить CSRF токен для HTMX запросов в meta теги

### 2. Подготовка view для HTMX

- [ ] Создать вспомогательную функцию в `blog/views.py`:

  ```python
  def is_htmx_request(request):
      return request.htmx
  ```

- [ ] Обновить `post_list()`:
  - Добавить проверку HTMX запроса
  - Возвращать полный шаблон для обычного запроса
  - Возвращать только partial для HTMX запроса
- [ ] Добавить пагинацию к списку постов:
  - По 5 постов на страницу
  - Параметр `?page=N` в URL

### 3. Реализация "Загрузить еще" (Load More)

- [ ] Обновить `post_list.html`:
  - Обернуть список постов в контейнер с `id="post-container"`
  - Использовать partial `post_card` для отрисовки
  - Добавить кнопку "Загрузить еще" с HTMX атрибутами:

    ```html
    <button 
      hx-get="{% url 'blog:post_list' %}?page={{ next_page }}"
      hx-target="#post-container"
      hx-swap="beforeend"
      class="btn btn-dark">
      Загрузить еще
    </button>
    ```

- [ ] Обновить view для возврата только карточек при HTMX запросе
- [ ] Добавить логику скрытия кнопки когда посты закончились

### 4. Реализация поиска в реальном времени

- [ ] Создать форму поиска в `post_list.html`:

  ```html
  <input 
    type="search" 
    name="search"
    hx-get="{% url 'blog:post_list' %}"
    hx-trigger="keyup changed delay:500ms"
    hx-target="#post-container"
    hx-swap="innerHTML"
    placeholder="Поиск...">
  ```

- [ ] Обновить `post_list()` view:
  - Добавить обработку параметра `search`
  - Фильтровать посты по заголовку и контенту
  - Возвращать filtered queryset
- [ ] Добавить индикатор загрузки:

  ```html
  <div class="htmx-indicator">
    <span class="spinner-border spinner-border-sm"></span>
    Поиск...
  </div>
  ```

### 5. Создание partial templates для HTMX

- [ ] Использовать Django 6 partials из фазы 1.6:
  - `{% #post_card %}` для отдельной карточки
  - `{% #post_list %}` для списка карточек
  - `{% #empty_state %}` для пустого результата поиска
- [ ] Создать отдельный partial `_post_card_htmx.html` если нужна дополнительная логика

### 6. Добавление плавных анимаций

- [ ] Обновить `static/css/style.css`:
  - Добавить CSS для HTMX переходов
  - Анимация появления новых постов
  - Плавное скрытие элементов

  ```css
  .htmx-swapping {
    opacity: 0;
    transition: opacity 0.2s ease-out;
  }
  
  .htmx-added {
    animation: fadeIn 0.3s ease-in;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  ```

### 7. История и навигация (опционально)

- [ ] Добавить `hx-push-url="true"` для обновления URL при поиске:

  ```html
  <input 
    hx-get="..."
    hx-push-url="true">
  ```

- [ ] Проверить работу кнопок "Назад/Вперед" браузера
- [ ] Убедиться что поисковые запросы сохраняются в истории

### 8. Тестирование и отладка

- [ ] Проверить работу с отключенным JavaScript (graceful degradation)
- [ ] Тестировать на разных браузерах
- [ ] Проверить производительность (должна улучшиться)
- [ ] Убедиться что CSRF токены работают корректно
- [ ] Проверить работу индикаторов загрузки

### 9. Документация HTMX паттернов

- [ ] Создать `blog/templates/blog/README_HTMX.md`:
  - Список всех HTMX endpoints
  - Паттерны использования
  - Примеры кода
  - Troubleshooting

## Технические детали

### Обновленный view с поддержкой HTMX

```python
from django.core.paginator import Paginator
from django.shortcuts import render

def post_list(request):
    posts = Post.objects.filter(is_published=True)
    
    # Поиск
    search = request.GET.get('search', '')
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search)
        )
    
    # Пагинация
    paginator = Paginator(posts, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # HTMX запрос - возвращаем только partial
    if request.htmx:
        return render(request, 'blog/_post_list_partial.html', {
            'posts': page_obj,
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        })
    
    # Обычный запрос - полная страница
    return render(request, 'blog/post_list.html', {
        'posts': page_obj,
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
    })
```

### Шаблон с HTMX атрибутами

```django
{% load component_tags %}

{# Форма поиска #}
<div class="mb-4">
  <input 
    type="search" 
    name="search"
    class="form-control"
    hx-get="{% url 'blog:post_list' %}"
    hx-trigger="keyup changed delay:500ms"
    hx-target="#post-container"
    hx-swap="innerHTML"
    hx-indicator="#search-indicator"
    placeholder="Поиск по постам...">
  <span id="search-indicator" class="htmx-indicator">
    <small class="text-muted">Поиск...</small>
  </span>
</div>

{# Контейнер для постов #}
<div id="post-container">
  {% for post in posts %}
    {% component "post_card" post=post %}
  {% empty %}
    <p class="text-center text-muted">Постов не найдено</p>
  {% endfor %}
</div>

{# Кнопка "Загрузить еще" #}
{% if next_page %}
  <div class="text-center mt-4">
    <button 
      hx-get="{% url 'blog:post_list' %}?page={{ next_page }}"
      hx-target="#post-container"
      hx-swap="beforeend"
      class="btn btn-dark">
      Загрузить еще
    </button>
  </div>
{% endif %}
```

### CSRF для HTMX

В `base.html`:

```html
<head>
  <!-- ... -->
  <meta name="csrf-token" content="{{ csrf_token }}">
  <script>
    document.body.addEventListener('htmx:configRequest', (event) => {
      event.detail.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').content;
    });
  </script>
</head>
```

## Результат

✅ HTMX установлен и настроен  
✅ Реализована подгрузка постов "Загрузить еще"  
✅ Работает поиск в реальном времени  
✅ Добавлены плавные анимации переходов  
✅ CSRF защита настроена корректно  
✅ История браузера работает (опционально)  
✅ Приложение работает с отключенным JS (graceful degradation)  
✅ UX улучшен без потери простоты кода

## Производительность и UX

**Улучшения:**

- Нет полной перезагрузки страницы
- Меньше трафика (загружаем только данные)
- Мгновенная обратная связь при поиске
- Плавные анимации
- Лучший UX на мобильных устройствах

**Компромиссы:**

- Небольшое увеличение сложности view
- Требуется поддержка двух режимов (HTMX и обычный)
- Нужно больше тестировать

## Связанная документация

- [HTMX Django Integration](../../researches/report_4/htmx-django-integration.md)
- [Practical Examples](../../researches/report_4/practical-examples.md)
- [Security Best Practices](../../researches/report_4/security-best-practices.md)
- [Django 6 Template Partials](../../researches/report_2/django6-templates-innovations.md)
- [Style Guide](style_guide_html.md)

## Следующий шаг

Фаза 2: Расширенные возможности блога (комментарии, теги, поиск, админка)
