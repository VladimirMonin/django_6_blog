# Серия 05: Django Components — Модульная Архитектура UI

**Коммит:** `a235121`  
**Дата:** 13 декабря 2025  
**Фаза:** Phase 1.7

## Введение

В предыдущей серии мы познакомились с Django 6 Template Partials — встроенной функцией для переиспользования кусков шаблонов. Но что если нам нужно больше? Что если каждый UI-элемент должен иметь свою логику, стили и поведение, полностью изолированные от остального приложения?

Встречайте **django-components** — стороннюю библиотеку, которая привносит философию компонентной архитектуры из мира React/Vue в Django. Это не замена Template Partials, а эволюция: от простых кусков HTML к полноценным инкапсулированным компонентам.

## Зачем нужны компоненты?

### Проблемы Template Partials

Partials отлично справляются с переиспользованием HTML, но у них есть ограничения:

1. **Нет изоляции стилей** — CSS прописывается в глобальном `style.css`
2. **Нет собственной логики** — вся логика живёт в views или template tags
3. **Нет автоматической загрузки ресурсов** — нужно вручную подключать CSS/JS
4. **Слабая инкапсуляция** — partial зависит от контекста родительского шаблона

### Что даёт django-components?

Компонент в django-components — это **самодостаточная единица UI**, состоящая из трёх файлов:

```
button/
├── button.py        # Python-логика компонента
├── button.html      # HTML-шаблон компонента
└── button.css       # Изолированные стили
```

Каждый компонент:

- ✅ Имеет собственную логику в Python-классе
- ✅ Управляет своими стилями через `Media` класс
- ✅ Автоматически подключает CSS при использовании
- ✅ Может принимать параметры (props) как React-компонент
- ✅ Может вкладываться друг в друга (композиция)

## Установка и настройка

### 1. Установка через Poetry

```bash
poetry add "django-components>=0.143.2" --python=">=3.12,<4.0"
```

**Важный нюанс:** django-components требует Python <4.0, а наш проект изначально был настроен на `>=3.12`. Poetry потребовал явно указать диапазон версий.

### 2. Настройка settings.py

Для работы компонентов нужны **три изменения** в настройках:

#### 2.1. Добавляем приложение

```python
INSTALLED_APPS = [
    # ...
    "django_components",  # ← добавляем
    "blog",
]
```

#### 2.2. Регистрируем template tags глобально

```python
TEMPLATES = [
    {
        # ...
        "OPTIONS": {
            # ...
            "builtins": [
                "django_components.templatetags.component_tags",  # ← добавляем
            ],
        },
    },
]
```

Теперь `{% component %}` доступен во всех шаблонах без `{% load component_tags %}`.

#### 2.3. Настраиваем сборщик статики

```python
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django_components.finders.ComponentsFileSystemFinder",  # ← добавляем
]
```

Это позволяет Django находить CSS/JS файлы компонентов.

## Архитектура компонента

Разберём на примере **Button** — самого базового компонента.

### Структура файлов

```
blog/components/button/
├── button.py        # Класс компонента
├── button.html      # Шаблон
└── button.css       # Стили
```

### Python-класс (button.py)

```python
from django_components import Component, register

@register("button")  # ← имя для использования в шаблонах
class Button(Component):
    template_file = "button/button.html"
    
    def get_template_data(self, args, kwargs, slots, context):
        """Обработка входных параметров (props)"""
        text = kwargs.get("text", "Button")
        url = kwargs.get("url", "#")
        style = kwargs.get("style", "dark")
        icon = kwargs.get("icon")
        active = kwargs.get("active", False)
        
        # Формируем CSS классы
        css_classes = [f"btn btn-{style}"]
        if active:
            css_classes.append("border-warning border-2")
        
        return {
            "text": text,
            "url": url,
            "css_class": " ".join(css_classes),
            "icon": icon,
        }
    
    class Media:
        css = "button/button.css"  # ← автоматическое подключение
```

**Ключевые моменты:**

1. **Декоратор `@register("button")`** — регистрирует компонент под именем "button"
2. **`get_template_data()`** — метод обработки входных данных (аналог React props)
3. **`class Media`** — декларативное подключение CSS/JS
4. **Логика формирования классов** — вся логика инкапсулирована в компоненте

### HTML-шаблон (button.html)

```django
<a href="{{ url }}" class="{{ css_class }}">
    {% if icon %}
        <i class="bi bi-{{ icon }}"></i>
    {% endif %}
    {{ text }}
</a>
```

Шаблон максимально простой — вся логика уже обработана в Python.

### CSS-файл (button.css)

```css
.btn {
    transition: all 0.2s ease;
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.btn.border-warning {
    border-color: #ffc107 !important;
}
```

CSS **изолирован** и подключается только когда компонент используется.

## Использование компонентов

### Простой вызов

```django
{% component "button" text="Читать далее" url="/post/1/" %}
```

### С иконкой

```django
{% component "button" text="Назад" url="/" icon="bi-arrow-left" %}
```

### С активным состоянием

```django
{% component "button" 
    text="Главная" 
    url="post_list" 
    icon="bi-house-door" 
    active=is_post_list 
%}
```

### Передача динамических значений

```django
{% component "button" 
    text="Вернуться к постам" 
    url="post_list" 
    icon="bi-arrow-left" 
%}
```

## Композиция компонентов

Один из мощных паттернов — **компоненты могут использовать другие компоненты**.

### PostCard использует Button

**post_card.html:**

```django
<div class="col">
    <div class="card h-100 shadow-sm post-card">
        <div class="card-body">
            <h2 class="card-title h4 mb-3">
                <a href="{% url 'post_detail' post.pk %}" class="text-decoration-none">
                    {{ post.title }}
                </a>
            </h2>
            <p class="text-muted mb-3">
                <i class="bi bi-calendar3"></i> {{ post.created_at|date:"d.m.Y H:i" }}
            </p>
            <p class="card-text">
                {{ post.content|truncatewords:50 }}
            </p>
            {% component "button" 
                text="Читать далее" 
                url=post.get_absolute_url 
                icon="arrow-right" 
            %}
        </div>
    </div>
</div>
```

**PostCard** инкапсулирует:

- Структуру карточки
- Логику отображения даты
- Кнопку "Читать далее" (через Button компонент)

## Наши компоненты

### Button — универсальная кнопка

**Параметры:**

- `text` — текст кнопки
- `url` — ссылка (можно передать name из urls.py)
- `style` — стиль (dark/warning/outline-dark)
- `icon` — иконка Bootstrap Icons
- `active` — активное состояние (желтая обводка)
- `size` — размер (sm/md/lg)

**Использование:**

```django
{% component "button" text="Главная" url="post_list" icon="bi-house-door" active=True %}
```

### PostCard — карточка поста

**Параметры:**

- `post` — объект модели Post

**Использование:**

```django
{% for post in posts %}
    {% component "post_card" post=post %}
{% endfor %}
```

**Внутренняя структура:**

- Заголовок с ссылкой
- Дата создания
- Превью контента (50 слов)
- Кнопка "Читать далее" (Button)

### Alert — уведомления

**Параметры:**

- `message` — текст сообщения
- `type` — тип (success/danger/warning/info)
- `dismissible` — возможность закрытия

**Использование:**

```django
{% component "alert" message="Постов пока нет." type="warning" %}
```

**Особенности:**

- Автоматический выбор иконки по типу
- Анимация появления (slideIn)
- Поддержка dismissible кнопки

## Автоматическая загрузка стилей

### Как это работает?

В `base.html` добавлен специальный тег:

```django
{% component_css_dependencies %}
```

Этот тег **автоматически** вставляет `<link>` теги для всех используемых компонентов на странице.

**Пример:** Если на странице используются Button и PostCard, будет вставлено:

```html
<link rel="stylesheet" href="/static/button/button.css">
<link rel="stylesheet" href="/static/post_card/post_card.css">
```

**Преимущества:**

- ✅ Загружаются только нужные стили
- ✅ Нет дублирования
- ✅ Не нужно вручную подключать CSS

## Переход от Partials к Components

### До (Template Partials) — post_list.html

```django
{% partialdef post_card %}
    <div class="col">
        <div class="card h-100 shadow-sm">
            <!-- 40 строк HTML -->
        </div>
    </div>
{% endpartialdef %}

{% if posts %}
    {% for post in posts %}
        {% partial post_card %}
    {% endfor %}
{% endif %}
```

**Проблемы:**

- Стили в глобальном CSS
- Логика в views
- 60+ строк в одном файле

### После (Django Components) — post_list.html

```django
{% if posts %}
    <div class="row row-cols-1 g-4">
        {% for post in posts %}
            {% component "post_card" post=post %}
        {% endfor %}
    </div>
{% else %}
    {% component "alert" message="Постов пока нет." type="warning" %}
{% endif %}
```

**Улучшения:**

- ✅ 20 строк вместо 60
- ✅ Стили изолированы в post_card.css
- ✅ Логика в post_card.py
- ✅ Переиспользуется где угодно

## Интеграция с Django

### Передача URL по имени

```django
{% component "button" url="post_list" %}
```

Внутри компонента можно использовать `{% url %}`:

```django
<a href="{% url url %}">...</a>
```

### Передача объектов модели

```django
{% component "post_card" post=post %}
```

В компоненте доступны все методы и атрибуты:

```django
{{ post.title }}
{{ post.get_absolute_url }}
{{ post.created_at|date:"d.m.Y" }}
```

### Передача флагов из views

**views.py:**

```python
def post_list(request):
    posts = Post.objects.filter(is_published=True)
    return render(request, 'blog/post_list.html', {
        'posts': posts,
        'is_post_list': True,  # ← флаг для навигации
        'is_about': False,
    })
```

**base.html:**

```django
{% component "button" 
    text="Главная" 
    url="post_list" 
    active=is_post_list  ← передаём флаг
%}
```

## Философия компонентов

### Принципы проектирования

1. **Single Responsibility** — один компонент = одна задача
   - Button — только кнопка
   - Alert — только уведомление
   - PostCard — только карточка поста

2. **Композиция вместо наследования**
   - PostCard использует Button
   - Можно создать CardWithActions, который использует Button + Dropdown

3. **Props down, events up** (готовимся к HTMX)
   - Данные передаются сверху вниз (props)
   - События уходят снизу вверх (скоро добавим с HTMX)

4. **Изоляция**
   - Каждый компонент — независимая единица
   - Можно скопировать папку `button/` в другой проект — заработает

### Когда использовать компоненты?

**✅ Используйте компоненты если:**

- Элемент переиспользуется в разных местах
- Нужна собственная логика (валидация, форматирование)
- Нужны изолированные стили
- Планируете HTMX-интерактивность (следующая серия!)

**❌ НЕ используйте компоненты если:**

- Элемент уникален и встречается в одном месте
- Нет логики (простой `<div>`)
- Достаточно Django template tags или filters

## Подготовка к HTMX

django-components идеально сочетается с HTMX по нескольким причинам:

1. **Компоненты возвращают готовый HTML**
   - HTMX может загружать их через AJAX
   - Не нужен JSON API

2. **Изолированные стили подгружаются автоматически**
   - Даже при динамической загрузке компонента

3. **Компоненты могут быть endpoint'ами**
   - URL → компонент → HTML фрагмент
   - HTMX вставляет HTML на страницу

**Пример (будет в следующей серии):**

```python
# Эндпоинт для HTMX
def load_more_posts(request):
    posts = Post.objects.all()[10:20]
    return render(request, 'blog/post_card_list.html', {'posts': posts})
```

```django
<!-- HTMX загрузит компоненты через AJAX -->
<button hx-get="/posts/load-more/" hx-target="#posts-list" hx-swap="beforeend">
    Загрузить ещё
</button>
```

Но это тема следующей серии! 😉

## Диаграмма архитектуры компонентов

```
┌─────────────────────────────────────────────────────────────┐
│                      BASE TEMPLATE                          │
│  {% component_css_dependencies %}  ← автозагрузка CSS       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     PAGE TEMPLATE                           │
│  {% component "post_card" post=post %}                      │
│  {% component "alert" message="..." type="warning" %}      │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   BUTTON     │    │  POST_CARD   │    │    ALERT     │
│ Component    │    │  Component   │    │  Component   │
├──────────────┤    ├──────────────┤    ├──────────────┤
│ button.py    │    │post_card.py  │    │  alert.py    │
│ button.html  │    │post_card.html│    │  alert.html  │
│ button.css   │    │post_card.css │    │  alert.css   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │  ComponentsFileSystem   │
              │        Finder           │
              │  (собирает все CSS)     │
              └─────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │  Rendered HTML + CSS    │
              └─────────────────────────┘
```

## Сравнение подходов

| Аспект | Template Partials | Django Components |
|--------|-------------------|-------------------|
| **Переиспользование** | ✅ Да | ✅ Да |
| **Изоляция стилей** | ❌ Нет (глобальный CSS) | ✅ Да (свой CSS файл) |
| **Собственная логика** | ❌ Нет (в views) | ✅ Да (в классе) |
| **Автозагрузка ресурсов** | ❌ Вручную | ✅ Автоматически |
| **Композиция** | ❌ Сложно | ✅ Естественно |
| **Готовность к HTMX** | 🟡 Частично | ✅ Идеально |
| **Сложность** | 🟢 Низкая | 🟡 Средняя |
| **Встроенность** | ✅ Django 6+ | ❌ Сторонняя библиотека |

## Статистика изменений

**Коммит `a235121`:**

- 19 файлов изменено
- +476 строк добавлено
- -94 строки удалено
- 9 новых файлов (3 компонента)

**Упрощение шаблонов:**

- `post_list.html`: 60 строк → 20 строк (-66%)
- `post_detail.html`: 64 строки → 40 строк (-37%)
- `base.html`: 86 строк → 72 строки (-16%)

## Что дальше?

В следующей серии мы интегрируем **HTMX** и увидим, как компоненты становятся динамическими:

1. Загрузка компонентов через AJAX
2. Infinite scroll для постов
3. Модальные окна без JavaScript
4. Живой поиск
5. Partial page updates

django-components + HTMX = SPA-подобный UX без написания JavaScript! 🚀

---

**Следующая серия:** Django + HTMX — Интерактивность без JavaScript  
**Предыдущая серия:** [Django 6 Template Partials](04_template_partials.md)  
**Вернуться к оглавлению:** [README](README.md)
